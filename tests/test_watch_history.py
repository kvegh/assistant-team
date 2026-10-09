import contextlib
import importlib.util
import io
from pathlib import Path
import sqlite3
import json
import struct
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'src/roles/agents_connector/files/connector-team.py'
spec=importlib.util.spec_from_file_location('watch_history',SOURCE)
team=importlib.util.module_from_spec(spec);spec.loader.exec_module(team)

class WatchHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        self.override=patch.object(team,'STATE',self.path);self.override.start();self.addCleanup(self.override.stop)
        with sqlite3.connect(self.path/'db.sqlite') as db:
            db.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY,from_agent TEXT,to_agent TEXT,text TEXT,ask_id INTEGER,in_reply_to INTEGER,created_at TEXT)')
            for identifier in [3,1,2]:
                db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?)',(identifier,'builder','orchestrator','body '+str(identifier),7 if identifier==1 else None,7 if identifier==2 else None,'same timestamp'))

    def test_last_entries_oldest_first_with_all_message_types_once(self):
        messages=team.watch_snapshot(2)[0]
        self.assertEqual([m['id'] for m in messages],[2,3])
        self.assertEqual(messages[0]['in_reply_to'],7)
        self.assertEqual([m['id'] for m in team.watch_snapshot(50)[0]],[1,2,3])

    def test_options_match_tail_defaults_and_follow(self):
        for args,expected in [([], (50,False)),(['-50'],(50,False)),(['-f'],(0,True)),(['-20','-f'],(20,True)),(['-f','-20'],(20,True)),(['-0'],(0,False)),(['-0','-f'],(0,True)),(['-200f'],(200,True)),(['-0f'],(0,True))]:
            self.assertEqual(team.watch_history_limit(args),expected)
        for arguments in [['-f','-f'],['-10001'],['50'],['-50','-20'],['--unknown'],['-200f','-f'],['-f','-200f'],['-20f','-30'],['-01f']]:
            with self.subTest(arguments=arguments),self.assertRaises(ValueError):team.watch_history_limit(arguments)

    def test_history_prints_and_exits_without_broker_or_model_operations(self):
        output=io.StringIO()
        with patch.object(team.socket,'socket',side_effect=AssertionError('broker connected')),patch.object(team,'watch_uses_color',return_value=False),contextlib.redirect_stdout(output):
            team.watch(limit=2)
        self.assertEqual(output.getvalue(),'[2] [reply to ask 7] builder -> orchestrator: body 2\n[3] builder -> orchestrator: body 3\n')
        with sqlite3.connect(self.path/'db.sqlite') as db:
            self.assertEqual(db.execute('select count(*) from messages').fetchone()[0],3)

    def test_empty_history_has_no_spurious_entries(self):
        with sqlite3.connect(self.path/'db.sqlite') as db:db.execute('DELETE FROM messages')
        self.assertEqual(team.watch_snapshot(50)[0],[])

    def test_symlink_database_rejected(self):
        (self.path/'db.sqlite').rename(self.path/'other.sqlite');(self.path/'db.sqlite').symlink_to(self.path/'other.sqlite')
        with self.assertRaisesRegex(ValueError,'symlink'):team.watch_snapshot(50)[0]

    def test_snapshot_preserves_color_formatter(self):
        with patch.object(team,'watch_uses_color',return_value=True),contextlib.redirect_stdout(io.StringIO()) as output:
            team.watch(limit=1)
        self.assertIn('\033[32mbuilder\033[0m',output.getvalue())
        self.assertNotIn('\033',output.getvalue().split(': ',1)[1])

    def test_follow_subscribes_before_snapshot_and_skips_boundary_duplicates(self):
        old={'id':3,'from':'builder','to':'orchestrator','text':'already in history'}
        new={'id':4,'from':'orchestrator','to':'builder','text':'new message'}
        frames=[{'kind':'ok'},{'kind':'stream_event','message':old},{'kind':'stream_event','message':new}]
        data=b''.join(struct.pack('!I',len(raw))+raw for raw in [json.dumps(f).encode() for f in frames])
        class Socket:
            subscribed=False
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def connect(self,path):pass
            def sendall(self,raw):self.subscribed=True
            def recv(self,size):
                nonlocal data
                result=data[:size];data=data[size:];return result
        socket=Socket();snapshot=team.watch_snapshot
        def checked_snapshot(limit):
            self.assertTrue(socket.subscribed)
            return snapshot(limit)
        with patch.object(team.socket,'socket',return_value=socket),patch.object(team,'watch_snapshot',side_effect=checked_snapshot),patch.object(team,'watch_uses_color',return_value=False),contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(EOFError):team.watch(limit=1,follow=True)
        self.assertEqual(output.getvalue().count('body 3'),1)
        self.assertNotIn('already in history',output.getvalue())
        self.assertEqual(output.getvalue().count('new message'),1)
