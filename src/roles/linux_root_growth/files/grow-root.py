#!/usr/bin/env python3
"""Grow an existing direct GPT/XFS root partition, preserving its identity."""
import datetime
import json
import os
import pathlib
import subprocess


def command(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def inspect():
    mount = json.loads(command('findmnt', '-J', '-o', 'SOURCE,FSTYPE', '/').stdout)['filesystems'][0]
    if mount['fstype'] != 'xfs':
        raise ValueError('Only an existing XFS root filesystem is supported')
    source = pathlib.Path(mount['source']).resolve()
    block = json.loads(command('lsblk', '-J', '-o', 'TYPE,PKNAME', str(source)).stdout)['blockdevices'][0]
    if block['type'] != 'part' or not block['pkname']:
        raise ValueError('Root must be a direct partition, not LVM or an encrypted mapping')
    disk = '/dev/' + block['pkname']
    number = int((pathlib.Path('/sys/class/block') / source.name / 'partition').read_text())
    table = json.loads(command('sfdisk', '--json', disk).stdout)['partitiontable']
    if table['label'] != 'gpt':
        raise ValueError('Expected an existing GPT partition table')
    partitions = table['partitions']
    root = next(p for p in partitions if pathlib.Path(p['node']).resolve() == source)
    if root != max(partitions, key=lambda p: p['start'] + p['size']):
        raise ValueError('Root must be the last partition; other partitions are never moved')
    return disk, number, root


def grow():
    os.umask(0o077)
    disk, number, before = inspect()
    total_before = os.statvfs('/').f_blocks * os.statvfs('/').f_frsize
    dry = command('growpart', '--dry-run', disk, str(number), check=False)
    if dry.returncode not in [0, 1] or (dry.returncode == 1 and 'NOCHANGE' not in dry.stdout + dry.stderr):
        raise ValueError('Partition growth dry run failed; no partition changes were made')
    if dry.returncode == 0:
        backup = pathlib.Path('/var/lib/assistant-team/storage-backups')
        backup.mkdir(mode=0o700, parents=True, exist_ok=True)
        if backup.is_symlink():
            raise ValueError('Partition backup directory must not be a symlink')
        backup.chmod(0o700)
        name = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = backup / (name + '.sfdisk')
        with path.open('x') as output:
            output.write(command('sfdisk', '--dump', disk).stdout)
        path.chmod(0o600)
        command('growpart', disk, str(number))
    final_disk, final_number, after = inspect()
    if final_disk != disk or final_number != number or any(after.get(k) != before.get(k) for k in ['start', 'type', 'uuid']):
        raise ValueError('Partition identity validation failed; consult the protected partition-table backup')
    if after['size'] < before['size']:
        raise ValueError('Partition unexpectedly shrank; filesystem growth was not attempted')
    command('xfs_growfs', '/')
    total_after = os.statvfs('/').f_blocks * os.statvfs('/').f_frsize
    if total_after < total_before:
        raise ValueError('Filesystem capacity validation failed')
    return {'changed': after['size'] > before['size'] or total_after > total_before,
            'filesystem_bytes': total_after,
            'available_bytes': os.statvfs('/').f_bavail * os.statvfs('/').f_frsize}


if __name__ == '__main__':
    print(json.dumps(grow()))
