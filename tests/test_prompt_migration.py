import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]/'src/roles'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    with patch.dict(os.environ,{},clear=True):spec.loader.exec_module(module)
    return module
CORE=load('migration_core',BASE/'agents_connector/files/connector-team.py')
MIGRATE=load('migration',BASE/'project_framework/files/migrate-prompts.py')

class MigrationTests(unittest.TestCase):
    def test_preserves_goal_role_prose_and_heading_text_with_protected_backup(self):
        with tempfile.TemporaryDirectory() as home:
            path=Path(home)/'assistant-prompt.md'
            text='# My goal\nCUSTOM_GOAL\n'+''.join('# Role: '+role+'\n# '+role.replace('-',' ').title()+'\nRough initial role prompt; refine through design.\n# Custom heading\nCUSTOM_'+role+'\n' for role in CORE.ALL)
            path.write_text(text)
            self.assertTrue(MIGRATE.migrate(path,CORE))
            goal,sections,modern=CORE.prompt_sections(path.read_text())
            self.assertTrue(modern)
            self.assertIn('My goal',CORE.active_prompt_text(goal))
            for role in CORE.ALL:
                active=CORE.active_prompt_text(sections[role])
                self.assertIn('Custom heading',active)
                self.assertIn('CUSTOM_'+role,active)
                self.assertNotIn('Rough initial',active)
            backups=list(Path(home).glob('*.before-bracket-migration-*'))
            self.assertEqual(len(backups),1)
            self.assertEqual(backups[0].read_text(),text)
            self.assertEqual(backups[0].stat().st_mode & 0o777,0o600)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertFalse(MIGRATE.migrate(path,CORE))
            self.assertEqual(len(list(Path(home).glob('*.before-bracket-migration-*'))),1)

    def test_invalid_role_set_is_not_modified_or_backed_up(self):
        with tempfile.TemporaryDirectory() as home:
            path=Path(home)/'assistant-prompt.md';path.write_text('# Role: builder\nKEEP')
            with self.assertRaises(ValueError):MIGRATE.migrate(path,CORE)
            self.assertEqual(path.read_text(),'# Role: builder\nKEEP')
            self.assertEqual(len(list(Path(home).iterdir())),1)
