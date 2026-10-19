"""Exercise refresh safeguards without contacting hosts, GitHub or AAP."""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'src/roles/native_auth_vault_refresh'
TASKS = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
PROTECTED = TASKS[1]
GUARD = next(task for task in PROTECTED['block'] if task['name'].startswith('Reject incomplete'))
COMPARE = next(task for task in PROTECTED['block'] if task['name'].startswith('Detect credential'))


class RefreshStructureTests(unittest.TestCase):
    def test_no_plaintext_payload_file_or_unpinned_trust(self):
        text = (ROLE / 'tasks/main.yml').read_text()
        self.assertIn('StrictHostKeyChecking=yes', text)
        self.assertIn('UserKnownHostsFile=', text)
        self.assertNotIn('ssh-keyscan', text)
        self.assertNotIn('force:', text)
        self.assertTrue(PROTECTED['no_log'])
        encrypted = next(task for task in PROTECTED['block']
                         if task['name'].startswith('Encrypt and publish'))['block'][0]
        self.assertIn('stdin', encrypted['ansible.builtin.command'])
        argv = encrypted['ansible.builtin.command']['argv']
        self.assertEqual(argv[:4], ['ansible-vault', 'encrypt', '--encrypt-vault-id', 'default'])
        self.assertNotIn('content:', text)
        self.assertIn('always', PROTECTED)

    @unittest.skipUnless(shutil.which('ansible-vault'), 'Ansible Vault is required')
    def test_stdin_encryption_handles_inherited_default_vault_password(self):
        with tempfile.TemporaryDirectory(prefix='ac-refresh-encrypt-') as directory:
            root = Path(directory)
            password = root / 'vpf'
            password.write_text('synthetic-refresh-test-password\n')
            password.chmod(0o600)
            encrypted = root / 'snapshot_vault.yml'
            encrypted.write_text('$ANSIBLE_VAULT;synthetic-existing-ciphertext')
            env = os.environ | {'ANSIBLE_VAULT_PASSWORD_FILE': str(password),
                                'ANSIBLE_LOCAL_TEMP': str(root / 'local')}
            result = subprocess.run([
                'ansible-vault', 'encrypt', '--encrypt-vault-id', 'default',
                '--vault-password-file', str(password), '--output', str(encrypted)],
                input='{"native_auth_transfer": {"synthetic": true}}',
                env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(encrypted.read_text().startswith('$ANSIBLE_VAULT;1.'))
            self.assertNotIn('synthetic', encrypted.read_text())


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible is required')
class RefreshGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ac-refresh-test-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.payload = {
            'version': 1, 'purpose': 'bootstrap', 'captured_at': 'new-capture',
            'entries': [{'profile': 'codex-priv', 'provider': 'codex', 'files': [
                {'path': 'auth.json', 'content_b64': 'c3ludGhldGljLW9ubHk='}]}],
            'report': [{'profile': 'codex-priv', 'status': 'ready', 'files': ['auth.json']}],
        }
        self.existing = copy.deepcopy(self.payload)
        self.existing['captured_at'] = 'old-capture'

    def run_tasks(self, expected_changed=None):
        tasks = [dict(GUARD, no_log=True), dict(COMPARE, no_log=True)]
        if expected_changed is not None:
            tasks.append({'ansible.builtin.assert': {'that': [
                '__native_auth_vault_refresh_changed | bool == ' + str(expected_changed)]}})
        play = [{'name': 'Verify protected refresh gates', 'hosts': 'localhost',
                 'gather_facts': False, 'connection': 'local', 'vars': {
                     '__native_auth_vault_refresh_payload': self.payload,
                     '__native_auth_vault_refresh_existing': {'native_auth_transfer': self.existing}},
                 'tasks': tasks}]
        path = self.directory / 'fixture.yml'
        path.write_text(yaml.safe_dump(play))
        env = os.environ | {'ANSIBLE_LOCAL_TEMP': str(self.directory / 'local'),
                            'ANSIBLE_REMOTE_TEMP': str(self.directory / 'remote')}
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)],
                              env=env, capture_output=True, text=True, timeout=30)

    def test_capture_timestamp_does_not_cause_a_new_commit(self):
        result = self.run_tasks(expected_changed=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_changed_credentials_require_a_new_commit(self):
        self.payload['entries'][0]['files'][0]['content_b64'] = 'Y2hhbmdlZC1zeW50aGV0aWM='
        result = self.run_tasks(expected_changed=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_enabled_authentication_is_rejected(self):
        self.payload['report'][0]['status'] = 'missing'
        result = self.run_tasks()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('c3ludGhldGljLW9ubHk=', result.stdout + result.stderr)

    def test_previously_stored_profile_cannot_be_removed(self):
        self.existing['entries'].append({'profile': 'claude-work', 'files': []})
        result = self.run_tasks()
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
