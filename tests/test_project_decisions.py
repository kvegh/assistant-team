import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'src/roles/agents_connector/files/connector-team.py'
spec=importlib.util.spec_from_file_location('project_decisions',SOURCE)
team=importlib.util.module_from_spec(spec);spec.loader.exec_module(team)

class DecisionLogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        profiles=self.root/'profiles'
        self.override=patch.multiple(team,ROOT=self.root,PROFILES=profiles,PROJECT='example')
        self.override.start();self.addCleanup(self.override.stop)
        for role in ['orchestrator','summarizer','builder']:
            base=profiles/role;base.mkdir(parents=True)
            (base/'profile.json').write_text(json.dumps({'flavour':'claude'}))
            (base/'workspace').mkdir();(base/'workspace/CLAUDE.md').write_text('User goal and role instructions: preserve this.\n')

    def test_empty_owner_only_log_created_once_existing_content_preserved(self):
        team.ensure_decision_log();log=self.root/'workspace/DECISIONS.log'
        self.assertEqual(log.read_bytes(),b'')
        self.assertEqual(stat.S_IMODE(log.stat().st_mode),0o600)
        log.write_text('existing approved outcome\n');before=log.stat().st_mtime_ns
        team.ensure_decision_log()
        self.assertEqual(log.read_text(),'existing approved outcome\n')
        self.assertEqual(log.stat().st_mtime_ns,before)

    def test_owned_blocks_preserve_user_text_and_are_idempotent(self):
        self.assertEqual(team.update_decision_log_instructions(),2)
        for role in ['orchestrator','summarizer']:
            target=team.role_workspace(role)/'CLAUDE.md'
            self.assertTrue(target.read_text().startswith('User goal and role instructions: preserve this.\n'))
            self.assertEqual(target.read_text().count(team.DECISION_BLOCK_START),1)
        self.assertEqual(team.update_decision_log_instructions(),0)
        self.assertEqual((team.role_workspace('builder')/'CLAUDE.md').read_text(),'User goal and role instructions: preserve this.\n')

    def test_block_refresh_keeps_operator_additions_before_and_after(self):
        team.update_decision_log_instructions()
        target=team.role_workspace('summarizer')/'CLAUDE.md';old=target.read_text()
        target.write_text('prefix\n'+old+'suffix\n')
        with patch.dict(team.DECISION_LOG_INSTRUCTIONS,{'summarizer':'Updated policy'}):
            self.assertEqual(team.update_decision_log_instructions(),1)
        self.assertTrue(target.read_text().startswith('prefix\nUser goal'))
        self.assertTrue(target.read_text().endswith('suffix\n'))
        self.assertIn('Updated policy',target.read_text())

    def test_symlink_log_or_workspace_refused(self):
        (self.root/'workspace').mkdir();(self.root/'workspace/DECISIONS.log').symlink_to(self.root/'outside')
        with self.assertRaisesRegex(ValueError,'regular'):team.ensure_decision_log()
        (self.root/'workspace/DECISIONS.log').unlink();(self.root/'workspace').rmdir()
        (self.root/'workspace').symlink_to(self.root)
        with self.assertRaisesRegex(ValueError,'symlink'):team.ensure_decision_log()

    def test_malformed_block_is_not_overwritten(self):
        target=team.role_workspace('orchestrator')/'CLAUDE.md'
        text='User wording\n'+team.DECISION_BLOCK_START;target.write_text(text)
        with self.assertRaisesRegex(ValueError,'Malformed'):team.update_decision_log_instructions()
        self.assertEqual(target.read_text(),text)

    def test_policy_requires_acceptance_and_excludes_private_or_routine_content(self):
        policy=team.DECISION_LOG_INSTRUCTIONS['summarizer']
        for requirement in ['explicit evidence of acceptance','Append only','sole intended writer','Proposals are not accepted','hidden-role identity','credentials','Do not use timers']:
            self.assertIn(requirement,policy)
