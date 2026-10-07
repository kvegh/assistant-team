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

    def test_arbitrary_text_and_unsupported_tmux_operations_are_rejected(self):
        with mock.patch.object(team, 'run') as execute:
            with self.assertRaises(ValueError):
                team.wake(['send-keys', '-l', '-t', 'workers:builder', 'untrusted body'])
            with self.assertRaises(ValueError):
                team.wake(['kill-session', '-t', 'workers'])
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
