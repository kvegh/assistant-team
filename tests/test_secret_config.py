"""Exercise controller-side Vault resolution without host or provider access."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'src/roles/secret_config'
PLAYBOOKS = (
    'configure_agents_connector', 'configure_assistant_containers',
    'deploy_complete_linux_vm', 'deploy_linux_vm', 'inspect_container_host',
    'recover_claude_auth', 'recover_codex_auth', 'retire_test_linux_vm',
    'transfer_native_auth',
)


class ExternalConfigurationStructureTests(unittest.TestCase):
    def test_consumers_have_no_application_vault_fallback(self):
        for name in PLAYBOOKS:
            with self.subTest(playbook=name):
                text = (ROOT / 'src' / (name + '.yml')).read_text()
                self.assertNotIn('../vars/', text)
                plays = yaml.safe_load(text)
                loaders = [task for play in plays for task in play.get('pre_tasks', [])
                           if task.get('ansible.builtin.include_role', {}).get('name') == 'secret_config']
                self.assertTrue(loaders)
                for loader in loaders:
                    self.assertIn('always', loader.get('tags', []))
                    self.assertIn('always', loader['ansible.builtin.include_role']['apply']['tags'])

    def test_transfer_does_not_reload_environment_by_default(self):
        play = yaml.safe_load((ROOT / 'src/transfer_native_auth.yml').read_text())[0]
        self.assertEqual(len(play['pre_tasks']), 2)
        self.assertIn('when', play['pre_tasks'][1])
        self.assertEqual(play['pre_tasks'][1]['vars']['secret_config_file'],
                         '{{ native_auth_transfer_config_file }}')

    def test_supported_environment_mapping_covers_configuration_and_auth(self):
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        self.assertEqual(set(defaults['secret_config_environment_variables']), {
            'environment', 'fresh_test', 'retire_test', 'claude_auth_recovery',
            'codex_auth_recovery', 'bootstrap_auth',
        })
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        load = next(task for task in tasks if 'ansible.builtin.include_vars' in task)
        self.assertTrue(load['no_log'])


class ControllerSnapshotStructureTests(unittest.TestCase):
    def test_all_six_ciphertext_inputs_are_injected_as_secret_files(self):
        defaults = yaml.load(
            (ROOT / 'src/roles/controller_secret_configs/defaults/main.yml').read_text(),
            Loader=yaml.BaseLoader,
        )
        files = defaults['controller_secret_configs_files']
        self.assertEqual(len(files), 6)
        self.assertEqual(files['bootstrap_auth'], 'bootstrap-auth_vault.yml')
        fields = {field['id']: field for field in
                  defaults['controller_secret_configs_inputs']['fields']}
        required = defaults['controller_secret_configs_inputs']['required']
        injectors = defaults['controller_secret_configs_injectors']
        for name in files:
            self.assertEqual(fields[name + '_vault']['secret'], 'true')
            self.assertIn(name + '_vault', required)
            self.assertIn('template.' + name, injectors['file'])
        self.assertEqual(injectors['env']['AC_AGENTS_BOOTSTRAP_AUTH_VAULT_FILE'],
                         '{{ tower.filename.bootstrap_auth }}')
        tasks = yaml.safe_load(
            (ROOT / 'src/roles/controller_secret_configs/tasks/main.yml').read_text())
        status = next(task['ansible.builtin.command']['argv'] for task in tasks
                      if task['name'] == 'Require committed encrypted configuration inputs')
        self.assertIn('vaults/bootstrap-auth_vault.yml', status)
        slurp = next(task for task in tasks if 'ansible.builtin.slurp' in task)
        self.assertTrue(slurp['no_log'])
        self.assertEqual(slurp['ansible.builtin.slurp']['src'],
                         '{{ controller_secret_configs_checkout }}/vaults/{{ item.value }}')

    def test_migration_attaches_new_then_detaches_only_the_previous_credential(self):
        defaults = yaml.load(
            (ROOT / 'src/roles/controller_secret_configs/defaults/main.yml').read_text(),
            Loader=yaml.BaseLoader,
        )
        self.assertNotEqual(defaults['controller_secret_configs_credential_name'],
                            defaults['controller_secret_configs_previous_credential_name'])
        tasks = yaml.safe_load(
            (ROOT / 'src/roles/controller_secret_configs/tasks/associate.yml').read_text())
        self.assertIn('Attach the snapshot', tasks[1]['name'])
        detach = tasks[2]
        self.assertIn("'disassociate': true", detach['ansible.builtin.uri']['body'])
        self.assertIn('previous.json.results[0].id', detach['ansible.builtin.uri']['body'])
        self.assertTrue(detach['no_log'])
        self.assertTrue(any('associations.json.results' in condition
                            for condition in detach['when']))


@unittest.skipUnless(shutil.which('ansible-playbook') and shutil.which('ansible-vault'),
                     'Existing Ansible executables are required')
class ExternalConfigurationAnsibleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='assistant-external-config-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.password = self.root / 'vpf'
        self.password.write_text('synthetic-test-only-password\n')
        self.password.chmod(0o600)
        self.config = self.root / 'configuration'
        self.config.mkdir()
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith('AC_AGENTS_') and key.endswith('_VAULT_FILE'):
                del self.env[key]
        self.env.update({
            'ANSIBLE_VAULT_PASSWORD_FILE': str(self.password),
            'ANSIBLE_LOCAL_TEMP': str(self.root / 'ansible-local'),
            'ANSIBLE_REMOTE_TEMP': str(self.root / 'ansible-remote'),
            'ANSIBLE_ROLES_PATH': str(ROOT / 'src/roles'),
            'ANSIBLE_NOCOLOR': '1',
        })

    def encrypt(self, name, marker):
        path = self.config / name
        path.write_text(yaml.safe_dump({'fixture_marker': marker}))
        result = subprocess.run(['ansible-vault', 'encrypt', str(path)],
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(path.read_text().startswith('$ANSIBLE_VAULT;'))
        return path

    @staticmethod
    def loader(namespace='', explicit='', name='environment'):
        return {
            'name': 'Load synthetic external configuration',
            'ansible.builtin.include_role': {'name': 'secret_config'},
            'vars': {'secret_config_name': name,
                     'secret_config_namespace': namespace,
                     'secret_config_file': explicit},
        }

    def run_play(self, tasks, env=None):
        play = self.root / 'fixture.yml'
        play.write_text(yaml.safe_dump([{
            'name': 'Test external configuration loading', 'hosts': 'localhost',
            'gather_facts': False, 'connection': 'local',
            'vars': {'assistant_secret_config_root': str(self.config)}, 'tasks': tasks,
        }], sort_keys=False))
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                              env=env or self.env, capture_output=True, text=True, timeout=60)

    def test_encrypted_fallback_global_and_namespaced_load(self):
        self.encrypt('environment_vault.yml', 'companion')
        result = self.run_play([
            self.loader('protected_configuration'),
            {'ansible.builtin.assert': {'that': [
                "protected_configuration.fixture_marker == 'companion'",
                'fixture_marker is undefined',
            ]}},
            self.loader(),
            {'ansible.builtin.assert': {'that': ["fixture_marker == 'companion'"]}},
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_credential_environment_overrides_companion_default(self):
        self.encrypt('environment_vault.yml', 'companion')
        override = self.encrypt('injected_vault.yml', 'credential')
        env = self.env | {'AC_AGENTS_ENVIRONMENT_VAULT_FILE': str(override)}
        result = self.run_play([self.loader(), {'ansible.builtin.assert': {
            'that': ["fixture_marker == 'credential'"]}}], env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_relative_override_wins_over_credential_and_default(self):
        self.encrypt('environment_vault.yml', 'companion')
        injected = self.encrypt('injected_vault.yml', 'credential')
        self.encrypt('explicit_vault.yml', 'explicit')
        env = self.env | {'AC_AGENTS_ENVIRONMENT_VAULT_FILE': str(injected)}
        result = self.run_play([self.loader(explicit='configuration/explicit_vault.yml'),
                               {'ansible.builtin.assert': {
                                   'that': ["fixture_marker == 'explicit'"]}}], env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bootstrap_auth_loads_from_companion_vaults_root(self):
        self.encrypt('../bootstrap-auth_vault.yml', 'encrypted-bootstrap')
        result = self.run_play([
            self.loader('protected_auth', name='bootstrap_auth'),
            {'ansible.builtin.assert': {'that': [
                "protected_auth.fixture_marker == 'encrypted-bootstrap'",
                'fixture_marker is undefined',
            ]}},
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bootstrap_auth_injected_path_overrides_local_snapshot(self):
        self.encrypt('../bootstrap-auth_vault.yml', 'local-bootstrap')
        override = self.encrypt('bootstrap_injected_vault.yml', 'injected-bootstrap')
        env = self.env | {'AC_AGENTS_BOOTSTRAP_AUTH_VAULT_FILE': str(override)}
        result = self.run_play([
            self.loader('protected_auth', name='bootstrap_auth'),
            {'ansible.builtin.assert': {'that': [
                "protected_auth.fixture_marker == 'injected-bootstrap'",
            ]}},
        ], env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_explicit_override_fails_without_silent_fallback(self):
        self.encrypt('environment_vault.yml', 'companion')
        result = self.run_play([self.loader(explicit='missing_vault.yml')])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('External encrypted configuration is unavailable', result.stdout)

    def test_wrong_vault_password_fails_without_loading_values(self):
        self.encrypt('environment_vault.yml', 'protected-marker-not-for-output')
        self.password.write_text('different-test-password\n')
        result = self.run_play([self.loader()])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('protected-marker-not-for-output', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
