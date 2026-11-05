"""Read-only native proof before completing one interrupted group association."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import pwd
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(*args):
    return subprocess.check_output(list(args), text=True, timeout=30).strip()


def verify(data):
    name, address, config = data['name'], data['address'], data['provisioning']
    pin = config['hypervisor_pin']
    require(re.fullmatch(r'[a-z][a-z0-9-]*-v(?:0[1-9]|[1-9][0-9]+)', name)
            and config['vm_name'] == name and config.get('generic_image') is True,
            'Repair requires the exact selected versioned generic profile.')
    require(ipaddress.ip_address(address).version == 4 and ipaddress.ip_address(address).is_private,
            'Repair requires the selected private guest address.')
    require(Path('/etc/machine-id').read_text().strip() == pin['machine_id'], 'Hypervisor identity differs.')
    disk = str(Path(config['vm_dir']) / (name + '.disk.qcow2'))
    source = Path(config['golden_image_path'])
    target = Path(disk)
    source_stat, target_stat = source.lstat(), target.lstat()
    trusted_owners = {0}
    try:
        trusted_owners.add(pwd.getpwnam('qemu').pw_uid)
    except KeyError:
        pass
    require(stat.S_ISREG(source_stat.st_mode) and stat.S_ISREG(target_stat.st_mode)
            and target_stat.st_nlink == 1 and source_stat.st_uid in trusted_owners and target_stat.st_uid in trusted_owners
            and not (target_stat.st_mode & 0o022) and source.resolve() != target.resolve(),
            'Clone is not exclusive protected regular storage.')
    source_digest = hashlib.sha256()
    with source.open('rb') as source_stream:
        for chunk in iter(lambda: source_stream.read(1024 * 1024), b''):
            source_digest.update(chunk)
    source_hash = source_digest.hexdigest()
    identity = run('virsh', '--readonly', '-c', 'qemu:///system', 'domuuid', name)
    require(re.fullmatch(r'[a-f0-9-]{36}', identity), 'Native UUID is missing.')
    interfaces = None
    for inactive in (False, True):
        args = ['virsh', '--readonly', '-c', 'qemu:///system', 'dumpxml', name]
        if inactive:
            args.append('--inactive')
        domain = ET.fromstring(run(*args))
        require(domain.findtext('name') == name and domain.findtext('uuid') == identity, 'Domain identity differs.')
        # Existing provisioning writes provenance to persistent XML after boot.
        # Match the shared lifecycle: always check saved provenance; also check
        # current provenance when libvirt exposes a current description.
        if inactive or domain.find('description') is not None:
            saved = json.loads(domain.findtext('description') or '{}')
            require(saved.get('schema_version') == 1 and saved.get('deployment_type') == 'generic-recovery'
                    and saved.get('vm_name') == name and saved.get('uuid') == identity
                    and saved.get('hypervisor_machine_id') == pin['machine_id']
                    and saved.get('source_image_sha256') == source_hash and saved.get('host_keys')
                    and all(re.fullmatch(r'(?:ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)) [A-Za-z0-9+/]+={0,2}', key)
                            for key in saved['host_keys']), 'Native generic provenance differs.')
        disks = domain.findall("./devices/disk[@device='disk']")
        require(len(disks) == 1 and disks[0].get('type') == 'file'
                and disks[0].find('source').get('file') == disk, 'Domain does not own the selected clone.')
        nics = domain.findall('./devices/interface')
        require(len(nics) == 1 and nics[0].get('type') == 'network'
                and nics[0].find('source').get('network') == config['vm_network'], 'Native network differs.')
        current = nics[0].find('mac').get('address', '').lower()
        require(re.fullmatch(r'(?:[a-f0-9]{2}:){5}[a-f0-9]{2}', current), 'Native MAC is missing.')
        require(interfaces in (None, current), 'Current and saved interfaces differ.')
        interfaces = current
        require(domain.findtext('vcpu') == str(config['vm_vcpus'])
                and domain.find('memory').get('unit') == 'KiB'
                and int(domain.findtext('memory')) == int(config['vm_memory_mb']) * 1024,
                'Native resources differ from the selected profile.')
    info = json.loads(run('qemu-img', 'info', '-U', '--output=json', disk))
    require(info.get('format') == 'qcow2' and 'backing-filename' not in info
            and info['virtual-size'] == int(config['vm_disk_gb']) * 1073741824, 'Native clone backing or capacity differs.')
    network = ET.fromstring(run('virsh', '--readonly', '-c', 'qemu:///system', 'net-dumpxml', config['vm_network']))
    require(network.findtext('name') == config['vm_network'] and network.find('bridge').get('name') in config['isolation_policy']['bridges'],
            'Native network is outside the pinned isolation policy.')
    leases = run('virsh', '--readonly', '-c', 'qemu:///system', 'net-dhcp-leases', config['vm_network'], '--mac', interfaces)
    observed = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?=/)', leases)
    require(observed == [address], 'Current native DHCP address differs or is ambiguous.')
    for other in run('virsh', '--readonly', '-c', 'qemu:///system', 'list', '--all', '--name').splitlines():
        if not other:
            continue
        if other != name:
            for inactive in (False, True):
                args = ['virsh', '--readonly', '-c', 'qemu:///system', 'dumpxml', other]
                if inactive:
                    args.append('--inactive')
                xml = ET.fromstring(run(*args))
                require(all(not node.get('file') or Path(node.get('file')).resolve() != target.resolve()
                            for node in xml.findall('./devices/disk/source'))
                        and all(node.get('address', '').lower() != interfaces for node in xml.findall('./devices/interface/mac')),
                        'Another domain references this clone or MAC.')
    return {'verified': True, 'vm_name': name, 'uuid': identity, 'disk': disk, 'address': address, 'mac': interfaces}


if __name__ == '__main__':
    try:
        print(json.dumps(verify(json.load(sys.stdin))))
    except Exception as error:
        print(json.dumps({'verified': False, 'reason': str(error)}))
        sys.exit(1)
