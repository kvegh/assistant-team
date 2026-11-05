"""Run actual retirement plays against disposable files and a simulated libvirt."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]


class GenericRetirementFlowTests(unittest.TestCase):
    def fixture(self, root):
        vms, roles = root / 'vms', root / 'roles'
        vms.mkdir(); roles.mkdir()
        selected, other = 'example-v16', 'other-v16'
        clone, other_disk, source = vms / (selected + '.disk.qcow2'), vms / (other + '.disk.qcow2'), root / 'source.qcow2'
        clone.write_bytes(b'disposable clone only')
        other_disk.write_bytes(b'preserved other clone')
        source.write_bytes(b'preserved upstream image')
        state = root / 'state.json'
        state.write_text(json.dumps({'domains': {selected: 'running', other: 'running'}, 'canonical': True, 'app': True}))
        trace = root / 'virsh.jsonl'
        virsh = root / 'virsh'
        virsh.write_text("#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\n"
            "p=Path(os.environ['RETIRE_FLOW_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]\n"
            "with Path(os.environ['RETIRE_FLOW_TRACE']).open('a') as f:f.write(json.dumps(a)+'\\n')\n"
            "name='example-v16'\n"
            "if a==['list','--all','--name']:print('\\n'.join(s['domains']))\n"
            "elif a[0]=='domblklist':\n"
            " print(' Type Device Target Source\\nfile disk vda '+str(Path(os.environ['RETIRE_FLOW_VMS'])/(a[1]+'.disk.qcow2')))\n"
            "elif a==['domstate',name]:print(s['domains'][name])\n"
            "elif a==['shutdown',name]:s['domains'][name]='shut off';p.write_text(json.dumps(s))\n"
            "elif a==['undefine',name,'--nvram']:\n"
            " assert s['domains'][name]=='shut off';del s['domains'][name];p.write_text(json.dumps(s))\n"
            "else:raise SystemExit('Forbidden simulated hypervisor operation')\n")
        virsh.chmod(0o700)
        pin = {'address': '192.0.2.10', 'user': 'fixture', 'port': 2222, 'machine_id': '1' * 32,
               'host_keys': ['ssh-ed25519 AAAA']}
        profile = {'provisioning': {'vm_name': selected, 'vm_dir': str(vms), 'golden_image_path': str(source),
                    'generic_image': True, 'hypervisor_pin': pin}}
        key = root / 'vpf'; key.write_text('synthetic-retirement-key'); key.chmod(0o600)
        vault = VaultLib([('default', VaultSecret(b'synthetic-retirement-key'))])
        profile_path = root / 'retire_vault.yml'; profile_path.write_bytes(vault.encrypt(yaml.safe_dump(profile)))

        def role(name, tasks):
            path = roles / name / 'tasks'
            path.mkdir(parents=True)
            (path / 'main.yml').write_text(yaml.safe_dump(tasks, sort_keys=False))

        read_state = {'name': 'Read fixture application ownership', 'ansible.builtin.slurp': {'src': str(state)},
                      'register': 'fixture_state_raw'}
        decode = {'name': 'Decode fixture application ownership', 'ansible.builtin.set_fact': {
            'fixture_state': '{{ fixture_state_raw.content | b64decode | from_json }}'}}
        role('inventory_vm_guard', [read_state, decode,
            {'name': 'Keep optional absence limited to requested retirement', 'ansible.builtin.assert': {'that': [
                'inventory_vm_guard_operation == "retire"',
                'fixture_state.app or inventory_vm_guard_allow_absent | default(false) | bool']}},
            {'name': 'Return the existing explicit fixture inventory binding', 'ansible.builtin.set_fact': {
                '__inventory_vm_guard_matches': '{{ [{"id":42,"variables":"assistant_vm_name: example-v16"}] if fixture_state.app else [] }}',
                '__inventory_vm_guard_groups': ['assistant_team'], '__inventory_vm_guard_host': {'id': 42},
                '__inventory_vm_guard_controller_host': 'https://controller.example.invalid',
                '__inventory_vm_guard_token': 'synthetic-inventory-token', '__inventory_vm_guard_ca_path': ''}}])
        planner = root / 'plan.py'
        planner.write_text("import json,os\nfrom pathlib import Path\np=Path(os.environ['RETIRE_FLOW_STATE']);s=json.loads(p.read_text())\n"
            "disk=Path(os.environ['RETIRE_FLOW_VMS'])/'example-v16.disk.qcow2';st=disk.stat() if disk.exists() else None\n"
            "print(json.dumps({'guest':{'vm_name':'example-v16','uuid':'synthetic-owned-uuid'} if s['canonical'] else None,"
            "'records_absent':not s['canonical'],'native':{'retirement_verified':True,'domain_present':'example-v16' in s['domains'],"
            "'disks_absent':not disk.exists(),'already_absent':not s['canonical'],"
            "'disk_identity':{'inode':st.st_ino,'device':st.st_dev} if st else None,"
            "'dynamic_lease_cache':{'rows':0,'expired':0,'unexpired':0}}}))\n")
        publish = root / 'publish.py'
        publish.write_text("import json,os\nfrom pathlib import Path\np=Path(os.environ['RETIRE_FLOW_STATE']);s=json.loads(p.read_text())\n"
            "assert 'example-v16' not in s['domains'];assert not (Path(os.environ['RETIRE_FLOW_VMS'])/'example-v16.disk.qcow2').exists()\n"
            "s['canonical']=False;p.write_text(json.dumps(s))\n")
        role('linux_recovery_release', [
            {'name': 'Require the existing exact retirement interface', 'ansible.builtin.assert': {'that': [
                'linux_recovery_release_operation == "retire_guest"',
                'linux_recovery_release_retire_guest_name == "example-v16"',
                'linux_recovery_release_retire_hypervisor == fixture_pin']}},
            {'name': 'Read saved fixture resource without guest access', 'ansible.builtin.command': {
                'argv': [sys.executable, str(planner)]}, 'register': 'fixture_plan_raw', 'changed_when': False},
            {'name': 'Return exact simulated native/source plan', 'ansible.builtin.set_fact': {
                'recovery_guest_retire_plan': '{{ (fixture_plan_raw.stdout | from_json) | combine({"guest_name":"example-v16","hypervisor":fixture_pin}) }}'}},
            {'name': 'Refuse simulated interrupted shared publication', 'ansible.builtin.assert': {'that': [
                'not (fixture_publication_failure | default(false) | bool)']}, 'when': 'linux_recovery_release_retire_phase == "publish"'},
            {'name': 'Publish fixture shared removal only after actual disposable file deletion',
             'ansible.builtin.command': {'argv': [sys.executable, str(publish)]},
             'when': 'linux_recovery_release_retire_phase == "publish"', 'changed_when': True}])
        retired = roles / 'linux_vm_retire/tasks'
        retired.mkdir(parents=True)
        (retired / 'main.yml').write_text((ROOT / 'src/roles/linux_vm_retire/tasks/main.yml').read_text().replace('ansible.builtin.uri:', 'uri:'))
        plugins = root / 'plugins'; plugins.mkdir()
        (plugins / 'uri.py').write_text("from ansible.plugins.action import ActionBase\nimport json,os\nfrom pathlib import Path\n"
            "class ActionModule(ActionBase):\n"
            " def run(self,tmp=None,task_vars=None):\n"
            "  a=self._task.args;assert a['method']=='DELETE' and a['url'].endswith('/hosts/42/')\n"
            "  p=Path(os.environ['RETIRE_FLOW_STATE']);s=json.loads(p.read_text())\n"
            "  assert not s['canonical'] and 'example-v16' not in s['domains'];s['app']=False;p.write_text(json.dumps(s))\n"
            "  return {'changed':True,'status':204}\n")
        plays = deepcopy(yaml.safe_load((ROOT / 'src/retire_test_linux_vm.yml').read_text()))
        for play in plays:
            play['become'] = False
        (root / 'retire.yml').write_text(yaml.safe_dump(plays, sort_keys=False))
        (root / 'inventory').write_text('[hypervisor]\nhypervisor ansible_connection=local\n')
        return pin, source, clone, other_disk, state, trace

    def run_fixture(self, root, native, pin, *, failed=False):
        return subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', str(root / 'inventory'),
            str(root / 'retire.yml'), '--vault-password-file', str(root / 'vpf'), '-e', json.dumps({
                'teardown_vm_name': 'example-v16', 'retire_test_execute': True, 'fixture_pin': pin,
                'fixture_publication_failure': failed})],
            cwd=ROOT, text=True, capture_output=True, timeout=75,
            env=dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'],
                ANSIBLE_HOME=str(root / 'home'), ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                ANSIBLE_ROLES_PATH=str(root / 'roles') + ':' + str(ROOT / 'src/roles'), ANSIBLE_ACTION_PLUGINS=str(root / 'plugins'),
                ANSIBLE_JINJA2_NATIVE=str(native).lower(), ANSIBLE_NOCOLOR='1',
                AC_AGENTS_RETIRE_TEST_VAULT_FILE=str(root / 'retire_vault.yml'), RETIRE_FLOW_STATE=str(root / 'state.json'),
                RETIRE_FLOW_TRACE=str(root / 'virsh.jsonl'), RETIRE_FLOW_VMS=str(root / 'vms')))

    def test_generic_decommission_preserves_images_other_guests_and_repeats_as_absent_noop(self):
        self.exercise(False)

    def test_interrupted_publication_retains_app_record_and_retries_without_the_vm(self):
        self.exercise(True)

    def exercise(self, interrupted):
        for native in (False, True):
            with self.subTest(native=native), tempfile.TemporaryDirectory(prefix='assistant-retire-flow-') as directory:
                root = Path(directory)
                pin, source, clone, other, state_path, trace = self.fixture(root)
                if interrupted:
                    failed = self.run_fixture(root, native, pin, failed=True)
                    self.assertNotEqual(failed.returncode, 0)
                    state = json.loads(state_path.read_text())
                    self.assertTrue(state['app'])
                    self.assertTrue(state['canonical'])
                    self.assertNotIn('example-v16', state['domains'])
                    self.assertFalse(clone.exists())
                finished = self.run_fixture(root, native, pin)
                self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
                repeated = self.run_fixture(root, native, pin)
                self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
                self.assertEqual(json.loads(state_path.read_text()), {'domains': {'other-v16': 'running'}, 'canonical': False, 'app': False})
                self.assertEqual(source.read_bytes(), b'preserved upstream image')
                self.assertEqual(other.read_bytes(), b'preserved other clone')
                commands = [json.loads(line) for line in trace.read_text().splitlines()]
                self.assertEqual(sum(command[0] == 'shutdown' for command in commands), 1)
                self.assertEqual(sum(command[0] == 'undefine' for command in commands), 1)
                self.assertFalse(any(command[0] == 'destroy' for command in commands))


if __name__ == '__main__':
    unittest.main()
