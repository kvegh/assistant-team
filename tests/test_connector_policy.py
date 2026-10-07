import importlib.util
import pathlib
import sqlite3
import tempfile
import unittest
from unittest import mock

SOURCE = pathlib.Path(__file__).parents[1] / 'src/roles/agents_connector/files/connector-team.py'
spec = importlib.util.spec_from_file_location('connector_team', SOURCE)
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class ConnectorPolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = pathlib.Path(self.directory.name)
        self.profiles = root / 'profiles'
        self.state = root / 'state'
        self.state.mkdir()
        for name in team.VISIBLE:
            (self.profiles / name).mkdir(parents=True)
            (self.profiles / name / 'token').write_text(name + '-token')
        self.patch = mock.patch.multiple(team, PROFILES=self.profiles, STATE=self.state)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        with sqlite3.connect(self.state / 'db.sqlite') as db:
            db.execute('create table asks(id integer, from_agent text, to_agent text)')
            db.execute("insert into asks values(1,'builder','investigator')")

    def test_identity_and_administrative_operations_are_denied(self):
        for kind in ['shutdown', 'get_agent', 'register_agent', 'remove_agent', 'subscribe_stream']:
            self.assertFalse(team.authorize('builder', {'kind': kind}))
        self.assertFalse(team.authorize('builder', {'kind': 'authenticate', 'agent_token': 'investigator-token'}))
        self.assertTrue(team.authorize('builder', {'kind': 'authenticate', 'agent_token': 'builder-token'}))
        self.assertFalse(team.authorize('builder', {'kind': 'read_messages', 'agent': 'investigator', 'since': 0}))

    def test_messaging_cannot_spoof_sender_or_address_hidden_roles(self):
        base = {'kind': 'tell', 'from': 'builder', 'to': 'investigator', 'text': 'task', 'urgent': True}
        self.assertTrue(team.authorize('builder', base))
        self.assertFalse(team.authorize('builder', dict(base, **{'from': 'orchestrator'})))
        self.assertFalse(team.authorize('builder', dict(base, to='observer')))
        self.assertFalse(team.authorize('builder', dict(base, to='corporate-connector')))

    def test_only_asker_reads_replies_and_only_recipient_replies(self):
        self.assertTrue(team.authorize('builder', {'kind': 'check_replies', 'ask_id': 1}))
        self.assertFalse(team.authorize('challenger', {'kind': 'check_replies', 'ask_id': 1}))
        self.assertTrue(team.authorize('investigator', {'kind': 'post_reply', 'ask_id': 1, 'from': 'investigator', 'text': 'result'}))
        self.assertFalse(team.authorize('builder', {'kind': 'post_reply', 'ask_id': 1, 'from': 'builder', 'text': 'forged'}))

    def test_prompt_sections_exclude_hidden_roles_and_preserve_source(self):
        root = pathlib.Path(self.directory.name) / 'agents-connector'
        root.mkdir()
        for name in team.ALL:
            path = self.profiles / name
            (path / 'workspace').mkdir(parents=True, exist_ok=True)
            (path / 'profile.json').write_text(__import__('json').dumps({'flavour': 'claude'}))
        source = root.parent / 'assistant-prompts.md'
        original = '\n'.join('# Role: ' + n + '\n' + ('hidden-secret' if n not in team.VISIBLE else 'own-' + n) for n in team.ALL)
        source.write_text(original)
        with mock.patch.object(team, 'ROOT', root):
            team.apply_prompts()
        self.assertEqual(source.read_text(), original)
        for name in team.VISIBLE:
            text = (self.profiles / name / 'workspace/CLAUDE.md').read_text()
            self.assertIn('own-' + name, text)
            self.assertNotIn('hidden-secret', text)

    def test_credentials_seed_only_the_selected_boundary_and_preserve_refresh(self):
        import json
        root = pathlib.Path(self.directory.name) / 'agents-connector'
        root.mkdir()
        for boundary, value in [('claude-work', 'work-fixture'), ('claude-priv', 'private-fixture')]:
            directory = root.parent / boundary / '.claude'
            directory.mkdir(parents=True)
            (directory / '.credentials.json').write_text(value)
            (directory / '.claude.json').write_text(json.dumps({'oauthAccount': {'fixture': True}, 'mcpServers': {'forbidden': {}}}))
        for name, boundary in [('investigator', 'claude-work'), ('private-connector', 'claude-priv')]:
            path = self.profiles / name
            (path / 'home').mkdir(parents=True, exist_ok=True)
            (path / 'profile.json').write_text(json.dumps({'flavour': 'claude', 'auth_directory': boundary}))
        with mock.patch.object(team, 'ROOT', root):
            team.seed_auth('investigator')
            team.seed_auth('private-connector')
            saved = self.profiles / 'investigator/home/.claude/.credentials.json'
            self.assertEqual(saved.read_text(), 'work-fixture')
            saved.write_text('refreshed-fixture')
            team.seed_auth('investigator')
            self.assertEqual(saved.read_text(), 'refreshed-fixture')
        self.assertEqual((self.profiles / 'private-connector/home/.claude/.credentials.json').read_text(), 'private-fixture')
        metadata = json.loads((self.profiles / 'investigator/home/.claude.json').read_text())
        self.assertNotIn('mcpServers', metadata)

    def test_group_stop_targets_all_eight_named_containers_only(self):
        import sys
        for name in team.ALL:
            path = self.profiles / name
            path.mkdir(exist_ok=True)
            (path / 'launched').touch()
        with mock.patch.object(sys, 'argv', ['connector-team.py', 'stop']), mock.patch.object(team.subprocess, 'run') as exists, mock.patch.object(team, 'run') as execute:
            exists.return_value.returncode = 0
            team.main()
            command = execute.call_args.args[0]
        self.assertEqual(command, ['podman', 'stop', '--time', '10', *['ac-' + n for n in team.ALL]])
        self.assertFalse(any((self.profiles / n / 'launched').exists() for n in team.ALL))

    def test_arbitrary_text_and_unsupported_tmux_operations_are_rejected(self):
        with mock.patch.object(team, 'run') as execute:
            with self.assertRaises(ValueError):
                team.wake(['send-keys', '-l', '-t', 'workers:builder', 'untrusted body'])
            with self.assertRaises(ValueError):
                team.wake(['kill-session', '-t', 'workers'])
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
