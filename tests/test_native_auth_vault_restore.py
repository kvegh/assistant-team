"""Synthetic Vault-to-native restoration, without provider access or real credentials."""
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

import test_native_auth_transfer as transfer_fixture

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ansible-playbook') and shutil.which('ansible-vault'),
                     'Existing Ansible executables are required')
class VaultRestoreTests(unittest.TestCase):
    def setUp(self):
        self.fixture = transfer_fixture.TransferTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = Path(self.fixture.tmp.name)
        self.secret_dir = self.root / 'vaults'
        self.secret_dir.mkdir()
        (self.secret_dir / 'configuration').mkdir()
        self.password = self.root / 'vpf'
        self.password.write_text('synthetic-vault-only-password\n')
        self.password.chmod(0o600)
        self.env = os.environ.copy()
        self.env.update({
            'ANSIBLE_LOCAL_TEMP': str(self.root / 'ansible-local'),
            'ANSIBLE_REMOTE_TEMP': str(self.root / 'ansible-remote'),
            'ANSIBLE_VAULT_PASSWORD_FILE': str(self.password),
            'ANSIBLE_ROLES_PATH': str(ROOT / 'src/roles'),
            'ANSIBLE_NOCOLOR': '1',
        })
        self.env.pop('AC_AGENTS_BOOTSTRAP_AUTH_VAULT_FILE', None)
        self.snapshot = self.fixture.capture()
        self.write_snapshot()

    def write_snapshot(self):
        path = self.secret_dir / 'bootstrap-auth_vault.yml'
        path.write_text(yaml.safe_dump({'native_auth_transfer': self.snapshot}))
        path.chmod(0o600)
        completed = subprocess.run(['ansible-vault', 'encrypt', str(path)],
                                   env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def run_role(self, enabled=True, check=False):
        variables = {
            'ansible_become': False,
            'native_auth_vault_restore_enabled': enabled,
            'native_auth_vault_restore_runtime_user': getpass.getuser(),
            'native_auth_vault_restore_profiles_root': str(self.fixture.target),
            'native_auth_vault_restore_environment_config': str(self.fixture.configs[1]),
            'native_auth_vault_restore_report_directory': str(self.root / 'reports'),
            'assistant_secret_config_root': str(self.secret_dir / 'configuration'),
        }
        playbook = self.root / 'restore.yml'
        playbook.write_text(yaml.safe_dump([{
            'name': 'Synthetic restore', 'hosts': 'localhost', 'connection': 'local',
            'gather_facts': False, 'vars': variables,
            'roles': ['native_auth_vault_restore'],
            'post_tasks': [{'name': 'Prove decrypted facts are cleared',
                            'ansible.builtin.assert': {'that': [
                                'native_auth_vault_restore_snapshot | default({}) == {}',
                                '__native_auth_vault_restore_execution.stdout is not defined',
                                '__native_auth_vault_restore_environment.content is not defined']}}],
        }], sort_keys=False))
        argv = ['ansible-playbook', '-i', 'localhost,', str(playbook)] + (['--check'] if check else [])
        result = subprocess.run(argv, env=self.env, capture_output=True, text=True, timeout=90)
        self.assertNotIn('synthetic-access', result.stdout + result.stderr)
        self.assertNotIn('synthetic-refresh', result.stdout + result.stderr)
        self.assertFalse(list(self.root.glob('ansible-remote/ac-auth-vault-restore-*')))
        return result

    def test_restore_all_profiles_then_preserve_newer_credentials_idempotently(self):
        first = self.run_role()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        credential = self.fixture.target / 'codex-priv/.codex/auth.json'
        self.assertTrue(credential.exists())
        credential.write_text('newer-native-credential-stream')
        second = self.run_role()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn('changed=0', second.stdout)
        self.assertEqual(credential.read_text(), 'newer-native-credential-stream')
        report = json.loads((self.root / 'reports/latest.json').read_text())
        self.assertEqual(sum(row['status'] == 'skipped_existing' for row in report['report']), 6)
        self.assertNotIn('entries', report)

    def test_disabled_restore_does_not_require_a_vault_or_touch_native_credentials(self):
        (self.secret_dir / 'bootstrap-auth_vault.yml').unlink()
        result = self.run_role(enabled=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.root / 'reports').exists())
        self.assertFalse((self.fixture.target / 'codex-priv/.codex/auth.json').exists())

    def test_invalid_payload_fails_before_any_credential_write(self):
        self.snapshot['entries'][-1]['files'][0]['path'] = '../escape'
        self.write_snapshot()
        result = self.run_role()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.fixture.target / 'codex-priv/.codex/auth.json').exists())
        self.assertFalse((self.root / 'reports/latest.json').exists())

    def test_disabled_target_profiles_are_not_restored(self):
        config = json.loads(self.fixture.configs[1].read_text())
        config['profiles']['codex-priv']['enabled'] = False
        self.fixture.configs[1].write_text(json.dumps(config))
        result = self.run_role()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.fixture.target / 'codex-priv/.codex/auth.json').exists())
        report = json.loads((self.root / 'reports/latest.json').read_text())
        self.assertIn({'profile': 'codex-priv', 'status': 'target_disabled', 'files': []}, report['report'])

    def test_enabled_target_missing_snapshot_credentials_fails_before_any_write(self):
        config = json.loads(self.fixture.configs[1].read_text())
        config['profiles']['codex-work']['enabled'] = True
        self.fixture.configs[1].write_text(json.dumps(config))
        result = self.run_role()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.fixture.target / 'codex-priv/.codex/auth.json').exists())
        self.assertFalse((self.fixture.target / 'claude-priv/.claude/.credentials.json').exists())
        self.assertFalse((self.root / 'reports/latest.json').exists())

    def test_check_mode_does_not_write_credentials(self):
        result = self.run_role(check=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.fixture.target / 'codex-priv/.codex/auth.json').exists())
        self.assertFalse((self.root / 'reports/latest.json').exists())
