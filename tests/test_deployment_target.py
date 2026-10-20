"""Exercise launch-name and recovery selection without provisioning or network access."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ansible-playbook'), 'ansible-playbook unavailable')
class DeploymentTargetTests(unittest.TestCase):
    def run_target(self, *, recovery=False, conflicting=False):
        with tempfile.TemporaryDirectory(prefix='assistant-deployment-target-') as temp:
            base = Path(temp)
            roles = base / 'roles'
            roles.mkdir()
            (roles / 'deployment_target').symlink_to(ROOT / 'src/roles/deployment_target', target_is_directory=True)
            guard = roles / 'inventory_vm_guard/tasks'
            guard.mkdir(parents=True)
            # The shared guard has independent API/safety tests. This fixture supplies
            # a live inventory result different from the stale encrypted recovery IP.
            (guard / 'main.yml').write_text(yaml.safe_dump([
                {'name': 'Check the caller selects the correct lifecycle mode',
                 'ansible.builtin.assert': {'that': [
                     'inventory_vm_guard_name == "example-6"',
                     'inventory_vm_guard_require_existing | bool == expected_existing | bool',
                     'inventory_vm_guard_operation == "lookup"']}},
                {'name': 'Supply an authoritative inventory address',
                 'ansible.builtin.set_fact': {'__inventory_vm_guard_host': {
                     'decoded_variables': {'ansible_host': '192.0.2.6'}}}},
            ]))
            variables = {
                'deployment_vm_name': 'example-6', 'expected_existing': recovery,
                'fresh_definition': {'provisioning': {
                    'vm_name': 'example-5', 'vm_disk_gb': 20,
                    'guest_ssh_user': 'placeholder', 'guest_ssh_password': 'placeholder',
                    'guest_become_password': 'placeholder'},
                    'recovery': {'guest_ip': '192.0.2.5'}},
            }
            if conflicting:
                variables['vm_name'] = 'example-1'
            checks = [
                'deployment_target_definition.provisioning.vm_name == "example-6"',
                'deployment_target_definition.recovery.guest_ip == ""',
                'deployment_target_definition.provisioning.vm_disk_gb == 20',
            ]
            checks.append('hostvars["example-6"].ansible_host == "192.0.2.6"' if recovery
                          else '"provisioned_linux_guest" not in groups')
            playbook = [{'name': 'Validate isolated target resolution', 'hosts': 'localhost',
                         'connection': 'local', 'gather_facts': False, 'vars': variables,
                         'tasks': [
                             {'name': 'Resolve', 'ansible.builtin.include_role': {
                                 'name': 'deployment_target', 'apply': {'tags': ['always']}}, 'tags': ['always']},
                             {'name': 'Check the resulting selection',
                              'ansible.builtin.assert': {'that': checks}, 'tags': ['always']},
                         ]}]
            path = base / 'test.yml'
            path.write_text(yaml.safe_dump(playbook))
            env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(base / 'tmp'))
            args = ['ansible-playbook', '-i', 'localhost,', str(path)]
            if recovery:
                args += ['--tags', 'operator_docs']
            result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=45)
            return result

    def test_new_target_clears_old_recovery_and_preserves_reusable_configuration(self):
        result = self.run_target()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_configuration_only_uses_inventory_address_instead_of_stale_vault(self):
        result = self.run_target(recovery=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_conflicting_legacy_name_fails_before_provisioning(self):
        result = self.run_target(conflicting=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
