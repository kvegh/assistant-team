"""Run the actual complete-deployment plays with local, model-free role fixtures."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Existing Ansible is required')
class CompleteRecoveryTests(unittest.TestCase):
    def fixture(self, root, generic=True, http=False):
        roles = root / 'roles'
        roles.mkdir()

        def role(name, tasks):
            directory = roles / name / 'tasks'
            directory.mkdir(parents=True)
            (directory / 'main.yml').write_text(yaml.safe_dump(tasks, sort_keys=False))

        def record(name):
            return {'name': 'Record fixture stage ' + name, 'ansible.builtin.command': {
                'argv': [sys.executable, '-c',
                         'from pathlib import Path; Path(' + repr(str(root / name)) + ').touch()']},
                    'changed_when': False}

        pin = {'address': '192.0.2.10', 'user': 'fixture', 'port': 2222,
               'machine_id': '1' * 32, 'host_keys': ['ssh-ed25519 AAAA']}
        definition = {'provisioning': {'vm_name': 'example-v16', 'vm_dir': '/example/vms',
            'vm_domain': 'example.invalid', 'vm_network': 'example-network', 'vm_disk_gb': 20,
            'golden_image_path': '/example/upstream.qcow2', 'generic_image': generic,
            'guest_ssh_user': 'fixture', 'guest_ssh_password': 'synthetic-bootstrap-canary',
            'guest_become_password': 'synthetic-bootstrap-canary'},
            'runtime_user': 'fixture', 'enabled_profiles': [], 'validate_projects': True}
        if generic:
            definition['provisioning']['hypervisor_pin'] = pin
        if http is not False:
            definition['container_build_http_bootstrap'] = http
        (root / 'vpf').write_text('synthetic-vault-password')
        (root / 'vpf').chmod(0o600)
        vault = VaultLib([('default', VaultSecret(b'synthetic-vault-password'))])
        (root / 'fresh_vault.yml').write_bytes(vault.encrypt(yaml.safe_dump(definition)))
        (root / 'fresh_vault.yml').chmod(0o600)
        provenance = {'vm_name': 'example-v16', 'uuid': '11111111-2222-3333-4444-555555555555',
                      'disk': '/example/vms/example-v16.disk.qcow2', 'network': 'example-network',
                      'bridge': 'fixture0', 'mac': '02:00:00:00:00:16', 'address': '192.0.2.16',
                      'host_keys': ['ssh-ed25519 AAAA'], 'hypervisor_machine_id': '1' * 32,
                      'source_image_sha256': 'a' * 64}
        role('inventory_vm_guard', [
            {'name': 'Inspect fixture inventory registration', 'ansible.builtin.stat': {
                'path': str(root / 'registered')}, 'register': 'fixture_registration'},
            {'name': 'Require the actual create/retry selection', 'ansible.builtin.assert': {'that': [
                'inventory_vm_guard_name == "example-v16"',
                'fixture_registration.stat.exists == (inventory_vm_guard_require_existing | bool)']}},
            {'name': 'Provide the owned fixture inventory binding', 'ansible.builtin.set_fact': {
                '__inventory_vm_guard_host': {'decoded_variables': {'ansible_host': '127.0.0.1'}}}},
        ])
        provision = record('provisioned')
        provision['tags'] = ['provision']
        # Creating twice is a test failure. A configuration-only retry must skip it.
        provision['ansible.builtin.command']['argv'][-1] = (
            'from pathlib import Path; p=Path(' + repr(str(root / 'provisioned')) +
            '); assert not p.exists(), "provisioning repeated"; p.touch()')
        role('linux_vm', [provision, {'name': 'Bind the fixture guest and provenance',
            'ansible.builtin.add_host': {'name': 'example-v16', 'groups': 'provisioned_linux_guest',
                'ansible_connection': 'local', 'ansible_host': '127.0.0.1',
                'deployment_vm_name': 'example-v16', 'deployment_vm_ip': '192.0.2.16',
                'deployment_vm_vcpus': 2, 'deployment_vm_memory_mb': 4096, 'deployment_vm_disk_gb': 20,
                'deployment_vm_hypervisor_pin': pin if generic else {},
                'deployment_vm_provenance': provenance,
                'deployment_vm_trust_file': '/tmp/linux-vm-recovery-known-hosts-fixture'},
            'tags': ['provision', 'guest_config']}])
        role('deployment_inventory_registration', [record('registered')])
        role('linux_guest', [
            {'name': 'Reject failed authenticated base verification', 'ansible.builtin.assert': {
                'that': ['not (fail_base | default(false) | bool)']}},
            {'name': 'Publish fixture authenticated machine facts', 'ansible.builtin.set_fact': {
                'ansible_facts': {'machine_id': '2' * 32}, 'fixture_base_verified': True}},
            record('base_verified')])
        role('linux_root_growth', [
            {'name': 'Require authenticated base before root growth', 'ansible.builtin.assert': {
                'that': ['fixture_base_verified is sameas true']}},
            record('root_verified'),
            {'name': 'Publish fixture root verification', 'ansible.builtin.set_fact': {'fixture_root_verified': True}}])
        role('linux_recovery_release', [
            {'name': 'Require verified guest identity before either permission', 'ansible.builtin.assert': {
                'that': ['fixture_base_verified is sameas true', 'fixture_root_verified is sameas true',
                         'deployment_vm_verified_provenance.verified is sameas true',
                         'deployment_vm_verified_provenance.machine_id == "' + '2' * 32 + '"',
                         'deployment_vm_verified_provenance.hypervisor_machine_id == deployment_vm_hypervisor_pin.machine_id']}},
            {'name': 'Apply only the approved fixture bootstrap permission',
             'when': 'linux_recovery_release_operation | default("release_guest") == "guest_bootstrap_https"',
             'block': [
                 {'name': 'Refuse bootstrap before auth/identity or after a full release', 'ansible.builtin.assert': {'that': [
                     'not (fail_bootstrap | default(false) | bool)',
                     'deployment_vm_verified_provenance.packages_updated is sameas false',
                     'fixture_released is not defined']}},
                 record('bootstrap_https'),
                 {'name': 'Retain fixture bootstrap state', 'ansible.builtin.set_fact': {'fixture_bootstrap_verified': True}}]},
            {'name': 'Apply HTTP only for the selected explicit fixture profile',
             'when': 'linux_recovery_release_operation | default("release_guest") == "guest_bootstrap_http"',
             'block': [
                 {'name': 'Require separate explicit HTTP approval before software', 'ansible.builtin.assert': {'that': [
                     'hostvars.localhost.fresh_definition.container_build_http_bootstrap is sameas true',
                     'fixture_bootstrap_verified is sameas true',
                     'not (fail_http_bootstrap | default(false) | bool)',
                     'fixture_released is not defined']}},
                 record('bootstrap_http'),
                 {'name': 'Retain fixture HTTP state', 'ansible.builtin.set_fact': {'fixture_http_verified': True}}]},
            {'name': 'Apply full release only after complete installation',
             'when': 'linux_recovery_release_operation | default("release_guest") == "release_guest"',
             'block': [
                 {'name': 'Require successful software and model-free validation', 'ansible.builtin.assert': {'that': [
                     'fixture_installation_verified is sameas true',
                     'native_auth_vault_restore_result is not defined',
                     'native_auth_vault_restore_snapshot is not defined',
                     'deployment_vm_verified_provenance.packages_updated is sameas true']}},
                 record('released'),
                 {'name': 'Retain fixture release state', 'ansible.builtin.set_fact': {'fixture_released': True}}]}])
        role('linux_updates', [
            {'name': 'Require separately reviewed bootstrap access without full release', 'ansible.builtin.assert': {'that': [
                'not (provisioning.generic_image | bool) or fixture_bootstrap_verified | default(false) | bool',
                'not (hostvars.localhost.fresh_definition.container_build_http_bootstrap | default(false) | bool) or fixture_http_verified | default(false) | bool',
                'fixture_released is not defined']}},
            record('updated'),
            {'name': 'Publish completed update check', 'ansible.builtin.set_fact': {'linux_updates_remaining_updates': {'rc': 0}}}])
        for name in ['podman_host', 'codex_sandbox', 'agent_images', 'agents_connector', 'native_auth',
                     'antigravity_team', 'project_framework', 'project_workspace', 'vertex_auth']:
            role(name, [{'name': 'Require update stage for fixture software', 'ansible.builtin.assert': {
                'that': ['linux_updates_remaining_updates.rc == 0']}}, record('software_' + name)])
        role('environment_validation', [
            {'name': 'Simulate a later installation validation failure', 'ansible.builtin.assert': {
                'that': ['not (fail_software | default(false) | bool)']}}, record('installation_verified'),
            {'name': 'Retain completed model-free validation', 'ansible.builtin.set_fact': {
                'fixture_installation_verified': True}}])
        plays = deepcopy(yaml.safe_load((ROOT / 'src/deploy_complete_linux_vm.yml').read_text()))
        for play in plays:
            # Every managed-host operation is replaced by a local unprivileged fixture.
            play['become'] = False
            for task in play.get('pre_tasks', []) + play.get('tasks', []):
                if task.get('ansible.builtin.import_tasks') == 'tasks/verified_generic_guest.yml':
                    task['ansible.builtin.import_tasks'] = str(ROOT / 'src/tasks/verified_generic_guest.yml')
        (root / 'plays.yml').write_text(yaml.safe_dump(plays, sort_keys=False))
        (root / 'inventory').write_text('[hypervisor]\nhypervisor ansible_connection=local\n')

    def run_fixture(self, root, native, *, retry=False, repair=False, **values):
        extra = {'assistant_vm_configuration': str(root / 'fresh_vault.yml'),
                 'deployment_vm_name': 'example-v16', 'native_auth_vault_restore_enabled': False,
                 'vm_vcpus': 2, 'vm_memory_mb': 4096, 'vm_disk_gb': 20, **values}
        command = [sys.executable, '-m', 'ansible.cli.playbook', '-i', str(root / 'inventory'),
                   str(root / 'plays.yml'), '--vault-password-file', str(root / 'vpf'), '-e', json.dumps(extra)]
        if retry:
            command += ['--tags', 'guest_config']
        if repair:
            command += ['--tags', 'repair_inventory_registration']
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90,
            env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                     ANSIBLE_ROLES_PATH=str(root / 'roles') + ':' + str(ROOT / 'src/roles'),
                     ANSIBLE_JINJA2_NATIVE=str(native).lower(), ANSIBLE_NOCOLOR='1'))
        self.assertNotIn('synthetic-bootstrap-canary', result.stdout + result.stderr)
        return result

    def test_explicit_association_repair_never_runs_provision_updates_or_software(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                # Match the real host alias and prove an existing guest group cannot
                # let later plays enter automatic validation or always-tagged tasks.
                (root / 'inventory').write_text('hypervisor ansible_connection=local\n'
                    '[provisioned_linux_guest]\nexample-v16 ansible_connection=local\n')
                for name in ['linux_vm', 'deployment_inventory_registration', 'linux_guest']:
                    tasks = root / ('roles/' + name + '/tasks/main.yml')
                    tasks.write_text(yaml.safe_dump([{'ansible.builtin.fail': {
                        'msg': 'repair reached normal role ' + name}, 'tags': ['always']}]
                        + yaml.safe_load(tasks.read_text()), sort_keys=False))
                    meta = root / ('roles/' + name + '/meta')
                    meta.mkdir()
                    actual = ROOT / ('src/roles/' + name + '/meta/argument_specs.yml')
                    (meta / 'argument_specs.yml').write_text(actual.read_text() if actual.exists() else
                        yaml.safe_dump({'argument_specs': {'main': {'short_description': 'Always validation boundary fixture.', 'options': {}}}}))
                (root / 'roles/deployment_inventory_registration/tasks/repair.yml').write_text(
                    yaml.safe_dump([{'ansible.builtin.file': {'path': str(root / 'repair_only'), 'state': 'touch', 'mode': '0600'}}]))
                result = self.run_fixture(root, native, repair=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((root / 'repair_only').exists())
                for marker in ['provisioned', 'registered', 'updated', 'installation_verified', 'released', 'bootstrap_https']:
                    self.assertFalse((root / marker).exists(), marker)

    def test_complete_pinned_guest_releases_only_after_software_validation_without_auth_restore(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                result = self.run_fixture(root, native)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((root / 'released').exists())
                self.assertTrue((root / 'installation_verified').exists())
                self.assertFalse((root / 'bootstrap_http').exists())

    def test_http_requires_explicit_selected_profile_and_keeps_final_release_after_validation(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, http=True)
                result = self.run_fixture(root, native)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((root / 'bootstrap_http').exists())
                self.assertTrue((root / 'installation_verified').exists())
                self.assertTrue((root / 'released').exists())

    def test_http_approval_cannot_follow_a_different_launch_name_before_inventory_or_provisioning(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, http=True)
                result = self.run_fixture(root, native, deployment_vm_name='different-v16')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Constrain explicit HTTP approval', result.stdout)
                self.assertNotIn('Inspect fixture inventory registration', result.stdout)
                for marker in ['provisioned', 'bootstrap_https', 'bootstrap_http', 'updated', 'released']:
                    self.assertFalse((root / marker).exists(), marker)

    def test_failed_http_permission_stops_before_updates_software_and_full_release(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, http=True)
                result = self.run_fixture(root, native, fail_http_bootstrap=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue((root / 'bootstrap_https').exists())
                for marker in ['bootstrap_http', 'updated', 'installation_verified', 'released']:
                    self.assertFalse((root / marker).exists(), marker)

    def test_invalid_http_approval_or_unpinned_legacy_profile_refuses_before_either_grant(self):
        for generic, value in [(True, 'true'), (False, True)]:
            for native in [False, True]:
                with self.subTest(generic=generic, value=value, native=native), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.fixture(root, generic=generic, http=value)
                    result = self.run_fixture(root, native)
                    self.assertNotEqual(result.returncode, 0)
                    for marker in ['bootstrap_https', 'bootstrap_http', 'updated', 'released']:
                        self.assertFalse((root / marker).exists(), marker)

    def test_failed_base_never_releases_or_starts_updates(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                result = self.run_fixture(root, native, fail_base=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root / 'released').exists())
                self.assertFalse((root / 'updated').exists())

    def test_failed_installation_remains_failed_then_configuration_retry_preserves_vm(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                first = self.run_fixture(root, native, fail_software=True)
                self.assertNotEqual(first.returncode, 0)
                self.assertFalse((root / 'released').exists())
                self.assertFalse((root / 'installation_verified').exists())
                second = self.run_fixture(root, native, retry=True)
                self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
                self.assertTrue((root / 'installation_verified').exists())

    def test_missing_bootstrap_access_never_enables_early_full_release(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                result = self.run_fixture(root, native, fail_bootstrap=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root / 'released').exists())
                self.assertFalse((root / 'updated').exists())

    def test_legacy_complete_profile_does_not_require_recovery_release(self):
        for native in [False, True]:
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, generic=False)
                result = self.run_fixture(root, native)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse((root / 'released').exists())
                self.assertTrue((root / 'installation_verified').exists())


if __name__ == '__main__':
    unittest.main()
