import importlib.util
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'src/roles/agents_connector/files/connector-team.py'
spec=importlib.util.spec_from_file_location('watch_format',SOURCE)
team=importlib.util.module_from_spec(spec);spec.loader.exec_module(team)

class WatchFormatTests(unittest.TestCase):
    def setUp(self):
        self.message={'id':8,'from':'builder','to':'orchestrator','text':'Result line\nSecond line','ask_id':3}

    def test_plain_output_preserves_message_and_question_correlation(self):
        self.assertEqual(team.format_watch_message(self.message),'[8] [ask 3] builder -> orchestrator: Result line\nSecond line')

    def test_sender_and_recipient_colored_independently_body_plain(self):
        colored=team.format_watch_message(self.message,color=True)
        self.assertIn('\033[32mbuilder\033[0m -> \033[36morchestrator\033[0m',colored)
        self.assertNotIn('\033',colored.split(': ',1)[1])
        self.assertEqual(re.sub(r'\x1b\[[0-9;]*m','',colored),team.format_watch_message(self.message))

    def test_terminal_only_and_opt_out(self):
        tty=SimpleNamespace(isatty=lambda:True);pipe=SimpleNamespace(isatty=lambda:False)
        self.assertTrue(team.watch_uses_color(tty,{'TERM':'xterm-256color'}))
        for stream,env in [(pipe,{}),(tty,{'NO_COLOR':''}),(tty,{'NO_COLOR':'1'}),(tty,{'TERM':'dumb'})]:
            self.assertFalse(team.watch_uses_color(stream,env))

    def test_broadcast_unknown_roles_and_consistent_colors(self):
        self.message['to']=None;self.message['from']='new-role'
        colored=team.format_watch_message(self.message,color=True)
        self.assertIn('\033[37mnew-role\033[0m -> \033[90mworkers\033[0m',colored)
        self.assertEqual(colored,team.format_watch_message(self.message,color=True))

    def test_untrusted_terminal_control_sequences_cannot_add_color(self):
        self.message.update({'from':'\033[31mforged','to':'bad\nrole','text':'hello\033[31m\x9b31m\x7f'})
        plain=team.format_watch_message(self.message)
        self.assertIn('unknown -> unknown',plain)
        self.assertNotIn('\033',plain);self.assertNotIn('\x9b',plain)
        self.assertTrue(plain.endswith('hello?[31m?31m?'))

    def test_tell_without_correlation_and_reply_with_correlation(self):
        del self.message['ask_id']
        self.assertTrue(team.format_watch_message(self.message).startswith('[8] builder'))
        self.message['ask_id']=3
        self.assertTrue(team.format_watch_message(self.message).startswith('[8] [ask 3] builder'))
