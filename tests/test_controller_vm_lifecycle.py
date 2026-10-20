"""Exercise lifecycle setup identity guards and launch surveys without AAP access."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'src/roles/controller_vm_lifecycle'
TASKS = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())[0]['block']
TEMPLATE = yaml.safe_load((ROLE / 'tasks/template.yml').read_text())


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible is required')
class LifecycleLaunchTests(unittest.TestCase):
    def run_tasks(self, tasks, variables):
        with tempfile.TemporaryDirectory(prefix='ac-lifecycle-test-') as directory:
            path = Path(directory) / 'check.yml'
            path.write_text(yaml.safe_dump([{
                'name': 'Check controller lifecycle policy offline',
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': variables, 'tasks': tasks,
            }], sort_keys=False))
            return subprocess.run(
                ['ansible-playbook', '-i', 'localhost,', str(path)],
                env=os.environ | {'ANSIBLE_LOCAL_TEMP': str(Path(directory) / 'tmp')},
                capture_output=True, text=True, timeout=30,
            )

    def test_privileged_and_ambiguous_lifecycle_tokens_are_rejected(self):
        guard = next(task for task in TASKS if task['name'].startswith('Refuse administrator'))
        for admin, auditor, count, success in [
            (False, False, 1, True), (True, False, 1, False),
            (False, True, 1, False), (False, False, 2, False),
        ]:
            with self.subTest(admin=admin, auditor=auditor, count=count):
                result = self.run_tasks([guard], {
                    '__controller_vm_lifecycle_principal': {'json': {
                        'count': count, 'results': [{'id': 7, 'is_superuser': admin,
                                                  'is_system_auditor': auditor}],
                    }},
                })
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_teardown_survey_defaults_to_preflight_and_accepts_no_arbitrary_variables(self):
        settings = next(task for task in TEMPLATE if task['name'].startswith('Define lifecycle'))
        confirmation = next(task for task in TEMPLATE if task['name'].startswith('Add explicit retirement'))
        result = self.run_tasks([settings, confirmation, {
            'name': 'Check launch policy and boolean-compatible choices',
            'ansible.builtin.assert': {'that': [
                'not __controller_vm_lifecycle_template_fields.ask_variables_on_launch',
                'not __controller_vm_lifecycle_template_fields.allow_simultaneous',
                '__controller_vm_lifecycle_survey.spec[0].required',
                "__controller_vm_lifecycle_survey.spec[0].default == ''",
                "__controller_vm_lifecycle_survey.spec[0].variable == 'teardown_vm_name'",
                "__controller_vm_lifecycle_survey.spec[1].default == 'false'",
                "__controller_vm_lifecycle_survey.spec[1].choices.splitlines() == ['false', 'true']",
            ]},
        }], {
            'controller_vm_lifecycle_inventory': 2,
            'controller_vm_lifecycle_project': 56,
            'controller_vm_lifecycle_execution_environment': 6,
            '__controller_vm_lifecycle_template': {
                'name': 'Synthetic teardown', 'playbook': 'src/retire_test_linux_vm.yml',
                'description': 'Synthetic target', 'variable': 'teardown_vm_name', 'teardown': True,
            },
        })
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
