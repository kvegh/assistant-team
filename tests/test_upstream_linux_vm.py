"""Exercise the proposed normal raw-image path without a hypervisor or network."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.errors import AnsibleFilterError
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'src/roles/linux_vm'
spec = importlib.util.spec_from_file_location('upstream_pin', ROOT / 'src/filter_plugins/linux_vm_recovery.py')
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


def pin():
    return {'address': '192.0.2.10', 'user': 'fixture', 'port': 22,
            'machine_id': '1' * 32, 'host_keys': ['ssh-ed25519 AAAA']}


class NormalUpstreamTests(unittest.TestCase):
    def run_play(self, root, tasks, variables, *, check=False, roles=None):
        path = root / 'play.yml'
        path.write_text(yaml.safe_dump([{'name': 'Disposable upstream fixture', 'hosts': 'localhost',
            'connection': 'local', 'gather_facts': False, 'vars': variables, 'tasks': tasks}], sort_keys=False))
        env = dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_HOME=str(root / 'home'),
            ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
            ANSIBLE_FILTER_PLUGINS=str(ROOT / 'src/filter_plugins'),
            ANSIBLE_ROLES_PATH=str(roles or ROOT / 'src/roles'))
        args = [sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(path)]
        if check:
            args.append('--check')
        return subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)

    def inputs(self, root):
        source = root / 'source.qcow2'
        source.write_bytes(b'unchanged synthetic image baseline')
        route = {'vm_name': 'fixture-v07', 'generic_image': True, 'update_packages': False,
            'golden_image_path': str(source), 'source_image_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'vm_dir': str(root / 'vms'), 'vm_domain': 'example.invalid', 'vm_network': 'normal',
            'network_bridge': 'fixture0', 'hypervisor_pin': pin()}
        provision = dict(route, guest_ssh_user='fixture', guest_ssh_password='synthetic-bootstrap-canary',
                         guest_become_password='synthetic-bootstrap-canary')
        variables = {'ansible_host': pin()['address'], 'linux_vm_upstream': route,
            'vm_name': route['vm_name'], 'linux_vm_deployment_name': route['vm_name'],
            '__linux_vm_environment': {'provisioning':deepcopy(provision)},
            'provisioning': provision, 'role_path': str(ROLE)}
        return route, provision, variables

    def preflight(self, *, wrong_machine=False, wrong_hash=False, wrong_bridge=False, empty_route=False, missing_source=False):
        with tempfile.TemporaryDirectory(prefix='normal-image-preflight-') as tmp:
            root = Path(tmp)
            route, provision, variables = self.inputs(root)
            if wrong_hash:
                provision['source_image_sha256'] = route['source_image_sha256'] = '0' * 64
            if empty_route:
                variables['linux_vm_upstream']={}
            if missing_source:
                variables.pop('__linux_vm_environment')
            tasks = deepcopy(yaml.safe_load((ROLE / 'tasks/upstream-preflight.yml').read_text()))
            for task in tasks:
                if task['name'].startswith('Verify the actual'):
                    task['ansible.builtin.command']['argv'] = [sys.executable, '-c', "print('%s')" % ('2' * 32 if wrong_machine else '1' * 32)]
                if task['name'].startswith('Read the selected normal upstream network'):
                    xml = '<network><name>normal</name><bridge name="%s"/></network>' % ('other0' if wrong_bridge else 'fixture0')
                    task['ansible.builtin.command']['argv'] = [sys.executable, '-c', 'print(' + repr(xml) + ')']
            marker = root / 'passed'
            tasks.append({'name': 'First disposable storage boundary', 'ansible.builtin.file': {'path': str(marker), 'state': 'touch'}})
            result = self.run_play(root, tasks, variables)
            expected = not any((wrong_machine, wrong_hash, wrong_bridge, empty_route, missing_source))
            self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)
            self.assertEqual(marker.exists(), expected)
            self.assertEqual(Path(route['golden_image_path']).read_bytes(), b'unchanged synthetic image baseline')
            self.assertNotIn('synthetic-bootstrap-canary', result.stdout + result.stderr)

    def test_normal_preflight_accepts_only_exact_identity_source_hash_and_bridge(self):
        self.preflight()

    def test_empty_normal_mode_flag_cannot_skip_recovery_controls(self):
        self.preflight(empty_route=True)

    def test_missing_encrypted_namespace_cannot_select_normal_mode(self):
        self.preflight(missing_source=True)

    def test_wrong_machine_stops_before_storage(self):
        self.preflight(wrong_machine=True)

    def test_wrong_source_hash_stops_before_storage(self):
        self.preflight(wrong_hash=True)

    def test_wrong_network_bridge_stops_before_storage(self):
        self.preflight(wrong_bridge=True)

    def test_native_input_loads_preserve_encrypted_login_and_reject_updates_or_secret_overrides(self):
        for reject in (None, 'updates', 'credential', 'both_routes'):
            with self.subTest(reject=reject), tempfile.TemporaryDirectory(prefix='normal-image-input-') as tmp:
                root = Path(tmp)
                route, provision, variables = self.inputs(root)
                environment = {'provisioning': dict(provision, vm_name='unused-encrypted-default')}
                secret = VaultSecret(b'synthetic-key')
                ciphertext = root / 'environment_vault.yml'
                ciphertext.write_bytes(VaultLib([('default', secret)]).encrypt(yaml.safe_dump(environment)))
                key = root / 'key'; key.write_text('synthetic-key'); key.chmod(0o600)
                if reject == 'updates':
                    route['update_packages'] = True
                if reject == 'credential':
                    route['guest_ssh_password'] = 'rejected-secret-canary'
                variables = {'secret_config_file': str(ciphertext), 'vm_name': route['vm_name'], 'linux_vm_upstream': route}
                if reject == 'both_routes':
                    variables['linux_vm_recovery'] = {}
                plays = []
                for original in yaml.safe_load((ROOT / 'src/deploy_linux_vm.yml').read_text()):
                    tasks = deepcopy(original['pre_tasks'])
                    for task in tasks:
                        if 'ansible.builtin.include_tasks' in task:
                            item = task['ansible.builtin.include_tasks']
                            item['file'] = str(ROOT / 'src' / item['file'])
                    tasks.append({'name': 'Require exact normal route and protected login after this load', 'no_log': True,
                        'ansible.builtin.assert': {'that': ["provisioning.vm_name == 'fixture-v07'",
                         "provisioning.guest_ssh_password == 'synthetic-bootstrap-canary'",
                         'provisioning.update_packages is boolean and not provisioning.update_packages',
                         'provisioning.source_image_sha256 == linux_vm_upstream.source_image_sha256']}})
                    plays.append({'name': 'Actual normal upstream environment binding', 'hosts': 'localhost',
                        'connection': 'local', 'gather_facts': False, 'vars': variables, 'tasks': tasks})
                play = root / 'loads.yml'; play.write_text(yaml.safe_dump(plays, sort_keys=False))
                result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                    str(play), '--vault-password-file', str(key)], cwd=ROOT, text=True, capture_output=True, timeout=90,
                    env=dict(os.environ, ANSIBLE_HOME=str(root/'home'), ANSIBLE_LOCAL_TEMP=str(root/'local'),
                        ANSIBLE_REMOTE_TEMP=str(root/'remote'), ANSIBLE_ROLES_PATH=str(ROOT/'src/roles'), ANSIBLE_NOCOLOR='1'))
                self.assertEqual(result.returncode == 0, reject is None, result.stdout + result.stderr)
                self.assertNotIn('synthetic-bootstrap-canary', result.stdout + result.stderr)
                self.assertNotIn('rejected-secret-canary', result.stdout + result.stderr)

    def test_normal_publication_never_calls_recovery_release_and_cleans_public_trust(self):
        with tempfile.TemporaryDirectory(prefix='normal-image-publication-') as tmp:
            root = Path(tmp)
            _, _, variables = self.inputs(root)
            roles = root / 'roles'; poison = roles / 'linux_recovery_release/tasks'; poison.mkdir(parents=True)
            (poison/'main.yml').write_text('- name: Recovery role must never run for normal upstream mode\n  ansible.builtin.fail:\n    msg: Forbidden recovery policy call\n')
            trust = root / 'known_hosts'; trust.write_text('synthetic public key only'); trust.chmod(0o600)
            variables.update(deployment_vm_provenance={'vm_name': 'fixture-v07'}, deployment_vm_vcpus=2,
                deployment_vm_memory_mb=4096, deployment_vm_disk_gb=20, ansible_facts={'machine_id': '2'*32},
                deployment_vm_hypervisor_pin=pin(), deployment_vm_trust_file=str(trust))
            tasks = yaml.safe_load((ROOT/'src/tasks/verified_generic_guest.yml').read_text())
            result = self.run_play(root, tasks, variables, roles=roles)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(trust.exists())
            self.assertIn('skipping:', result.stdout)
            self.assertNotIn('TASK [Recovery role must never', result.stdout)

    def test_offline_bootstrap_explicitly_disables_cloud_init_updates_only_for_normal_route(self):
        for normal in (False, True):
            with self.subTest(normal=normal), tempfile.TemporaryDirectory(prefix='normal-image-bootstrap-') as tmp:
                root = Path(tmp)
                _, _, variables = self.inputs(root)
                if not normal:
                    variables.pop('linux_vm_upstream')
                proof = root/'proof.json'
                stub = root/'customize.py'
                stub.write_text("import json,pathlib,sys,yaml\na=sys.argv[1:]\n"
                    "assert '--no-network' in a\n"
                    "assert 'synthetic-bootstrap-canary' not in ' '.join(a)\n"
                    "password=pathlib.Path(a[a.index('--password')+1].split(':',2)[2])\n"
                    "assert password.read_text().strip()=='synthetic-bootstrap-canary'\n"
                    "assert password.stat().st_mode & 511 == 384\n"
                    "cfg=next(x.split(':',1)[0] for x in a if x.endswith(':/etc/cloud/cloud.cfg.d/99-automation-bootstrap.cfg'))\n"
                    "data=yaml.safe_load(pathlib.Path(cfg).read_text())\n"
                    "assert data['datasource_list']==['None']\n"
                    + ("assert data['package_update'] is False and data['package_upgrade'] is False\n" if normal else
                       "assert 'package_update' not in data and 'package_upgrade' not in data\n")
                    + "pathlib.Path("+repr(str(proof))+").write_text(json.dumps({'workspace':str(password.parent)}))\n")
                tasks = deepcopy(yaml.safe_load((ROLE/'tasks/generic-bootstrap.yml').read_text()))
                for task in tasks[1]['block']:
                    if task['name'].startswith('Customize the new generic clone'):
                        task['ansible.builtin.command']['argv'] = [sys.executable,str(stub)] + task['ansible.builtin.command']['argv'][1:]
                variables.update(linux_vm_deployment_name='fixture-v07',linux_vm_deployment_disk=str(root/'clone.qcow2'))
                result = self.run_play(root,tasks,variables)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertFalse(Path(json.loads(proof.read_text())['workspace']).exists())
                self.assertNotIn('synthetic-bootstrap-canary',result.stdout+result.stderr)

    def test_normal_and_recovery_saved_provenance_cannot_be_interchanged(self):
        base={'schema_version':1,'deployment_type':'generic-upstream','vm_name':'fixture-v07','uuid':'fixture-uuid',
              'hypervisor_machine_id':'1'*32,'source_image_sha256':'a'*64,'host_keys':['ssh-ed25519 AAAA']}
        self.assertEqual(identity.saved_keys(base,'fixture-v07','fixture-uuid','1'*32,'a'*64,'generic-upstream'),['ssh-ed25519 AAAA'])
        with self.assertRaises(AnsibleFilterError):
            identity.saved_keys(base,'fixture-v07','fixture-uuid','1'*32,'a'*64)
        with self.assertRaises(AnsibleFilterError):
            identity.saved_keys(dict(base,deployment_type='generic-recovery'),'fixture-v07','fixture-uuid','1'*32,'a'*64,'generic-upstream')

    def test_copied_normal_clone_hash_must_match_before_customization(self):
        source=yaml.safe_load((ROLE/'tasks/main.yml').read_text())
        start=next(i for i,t in enumerate(source) if t['name']=='Hash the newly copied normal upstream clone before customization')
        checks=source[start:start+2]
        for changed in [False,True]:
            with self.subTest(changed=changed),tempfile.TemporaryDirectory(prefix='normal-clone-hash-') as tmp:
                root=Path(tmp)
                route,_,variables=self.inputs(root)
                clone=root/'clone.qcow2';clone.write_bytes(b'wrong-copy' if changed else Path(route['golden_image_path']).read_bytes())
                variables['linux_vm_deployment_disk']=str(clone)
                marker=root/'customization-boundary'
                tasks=checks+[{'name':'Disposable customization boundary','ansible.builtin.file':{'path':str(marker),'state':'touch'}}]
                result=self.run_play(root,tasks,variables)
                self.assertEqual(result.returncode==0,not changed,result.stdout+result.stderr)
                self.assertEqual(marker.exists(),not changed)
                self.assertTrue(clone.exists())

    def test_normal_check_mode_routes_around_recovery_policy_before_any_clone(self):
        with tempfile.TemporaryDirectory(prefix='normal-image-routing-') as tmp:
            root=Path(tmp)
            route,_,variables=self.inputs(root)
            variables.update(linux_vm_deployment_name=route['vm_name'],linux_vm_vcpus=2,
                linux_vm_memory_mb=4096,linux_vm_disk_gb=20,
                linux_vm_deployment_disk=str(root/'never-created.qcow2'))
            preflight=deepcopy(yaml.safe_load((ROLE/'tasks/upstream-preflight.yml').read_text()))
            for task in preflight:
                if task['name'].startswith('Verify the actual'):
                    task['ansible.builtin.command']['argv']=[sys.executable,'-c',"print('1'*32)"]
                if task['name'].startswith('Read the selected normal upstream network'):
                    task['ansible.builtin.command']['argv']=[sys.executable,'-c',"print('<network><name>normal</name><bridge name=\"fixture0\"/></network>')"]
            preflight_path=root/'upstream-preflight.yml';preflight_path.write_text(yaml.safe_dump(preflight,sort_keys=False))
            forbidden=root/'recovery-forbidden.yml'
            forbidden.write_text('- name: Recovery policy must not run in normal mode\n  ansible.builtin.fail:\n    msg: Forbidden recovery policy call\n')
            tasks=deepcopy(yaml.safe_load((ROLE/'tasks/main.yml').read_text()))
            for task in tasks:
                if task['name'].startswith('Verify a declared recovery hypervisor'):
                    task['ansible.builtin.include_tasks']['file']=str(forbidden)
                if task['name'].startswith('Verify a declared normal upstream'):
                    task['ansible.builtin.include_tasks']['file']=str(preflight_path)
                if task['name']=='Inspect existing VM names':
                    task['ansible.builtin.command']['argv']=[sys.executable,'-c',"print('unrelated-fixture')"]
                if task['name']=='Inspect golden image':
                    task['ansible.builtin.command']['argv']=[sys.executable,'-c',"print('{\"virtual-size\":1073741824}')"]
            result=self.run_play(root,tasks,variables,check=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('Require the exact normal upstream network bridge',result.stdout)
            self.assertNotIn('TASK [Recovery policy must not',result.stdout)
            self.assertNotIn('TASK [Clone the golden image',result.stdout)
            self.assertFalse(Path(variables['linux_vm_deployment_disk']).exists())

    def test_existing_no_overwrite_guard_refuses_either_domain_or_disk_conflict(self):
        guard=next(t for t in yaml.safe_load((ROLE/'tasks/main.yml').read_text()) if t['name']=='Refuse to overwrite an existing VM or disk')
        for domain,disk in [(False,False),(True,False),(False,True)]:
            with self.subTest(domain=domain,disk=disk),tempfile.TemporaryDirectory(prefix='normal-image-conflict-') as tmp:
                root=Path(tmp)
                _,_,variables=self.inputs(root)
                variables.update(linux_vm_deployment_name='fixture-v07',__linux_vm_existing_vms={'stdout_lines':['fixture-v07'] if domain else []},__linux_vm_existing_disk={'stat':{'exists':disk}})
                marker=root/'clone-boundary'
                tasks=[guard,{'name':'Disposable clone boundary','ansible.builtin.file':{'path':str(marker),'state':'touch'}}]
                result=self.run_play(root,tasks,variables)
                self.assertEqual(result.returncode==0,not(domain or disk),result.stdout+result.stderr)
                self.assertEqual(marker.exists(),not(domain or disk))


if __name__=='__main__':
    unittest.main()
