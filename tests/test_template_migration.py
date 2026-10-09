"""Exercise canonical template path protection with real local Ansible; no model or host access."""
import json
import os
import pathlib
import pwd
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible is required')
class CanonicalTemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = pathlib.Path(self.temp.name)
        self.old = self.home / 'assistant-prompts.md'
        self.new = self.home / 'conf/templates/assistant.prompt.md.template'

    def run_migration(self):
        play = [{
            'name': 'Test local template migration', 'hosts': 'localhost',
            'connection': 'local', 'gather_facts': False,
            'vars': {'assistant_install_root': str(self.home),
                     'containers': {'runtime_user': pwd.getpwuid(os.getuid()).pw_name}},
            'tasks': [{'name': 'Run migration tasks', 'ansible.builtin.import_tasks':
                       str(ROOT / 'src/roles/agents_connector/tasks/prompt_template.yml')}],
        }]
        fixture = self.home / 'migration.json'
        fixture.write_text(json.dumps(play))
        env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.home / 'ansible-tmp'),
                   ANSIBLE_REMOTE_TEMP=str(self.home / 'remote-tmp'))
        env.pop('ANSIBLE_VAULT_PASSWORD_FILE', None)
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(fixture)],
                              cwd=self.home, env=env, capture_output=True, text=True)

    def test_preserves_operator_bytes_and_is_idempotent(self):
        original = b'[Role: Investigator]\nEdited operator text\n'
        self.new.parent.mkdir(parents=True)
        self.new.write_bytes(original)
        first = self.run_migration()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertFalse(self.old.exists())
        self.assertEqual(self.new.read_bytes(), original)
        self.assertEqual(self.new.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.new.parent.stat().st_mode & 0o777, 0o700)
        second = self.run_migration()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn('changed=0', second.stdout)

    def test_canonical_template_symlink_preserves_legacy_and_external_files(self):
        self.old.write_text('original')
        self.new.parent.mkdir(parents=True)
        outside=self.home/'outside-template';outside.write_text('different')
        self.new.symlink_to(outside)
        result = self.run_migration()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Canonical template', result.stdout)
        self.assertEqual(self.old.read_text(), 'original')
        self.assertEqual(self.new.read_text(), 'different')

    def test_linked_template_directory_is_rejected(self):
        outside = self.home / 'outside'
        outside.mkdir()
        self.new.parent.parent.mkdir()
        self.new.parent.symlink_to(outside, target_is_directory=True)
        self.old.write_text('original')
        result = self.run_migration()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Canonical template', result.stdout)
        self.assertTrue(self.old.exists())
        self.assertFalse((outside / self.new.name).exists())

    def test_fresh_install_prepares_only_directory(self):
        result = self.run_migration()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.new.parent.is_dir())
        self.assertFalse(self.new.exists())
