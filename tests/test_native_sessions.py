"""Exact native conversation preservation, without credentials or model calls."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
import uuid
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / 'src/roles/agents_connector/files/native-sessions.py'
spec = importlib.util.spec_from_file_location('native_sessions', MODULE)
sessions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessions)


class NativeSessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.sid = str(uuid.uuid4())

    def write(self, relative, value):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + '\n')
        return path

    def claude(self, session_id=None, cwd='/workspace', sidechain=False):
        session_id = session_id or self.sid
        path = self.write('.claude/projects/-workspace/' + session_id + '.jsonl',
                          dict(type='mode', mode='normal'))
        with path.open('a') as stream:
            stream.write(json.dumps(dict(type='user', sessionId=session_id,
                                         cwd=cwd, isSidechain=sidechain, message='fixture')) + '\n')
        return path

    def gemini(self, session_id=None, kind='main', suffix='jsonl', cwd='/workspace'):
        session_id = session_id or self.sid
        return self.write('.gemini/tmp/project-slug/chats/session-' + session_id + '.' + suffix,
                          dict(sessionId=session_id, kind=kind,
                               projectHash=hashlib.sha256(cwd.encode()).hexdigest()))

    def codex(self, session_id=None, source='cli', thread_source='user', cwd='/workspace', archived=0):
        path = self.home / '.codex/state_5.sqlite'
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS threads (id TEXT, source TEXT, thread_source TEXT, cwd TEXT, archived INT, agent_path TEXT)')
            db.execute('INSERT INTO threads VALUES (?, ?, ?, ?, ?, NULL)',
                       (session_id or self.sid, source, thread_source, cwd, archived))
        return path

    def mistral(self, session_id=None, cwd='/workspace', parent=None):
        sid = session_id or self.sid
        path = self.write('.vibe/logs/session/session_20261019_120000_' + sid[:8] + '/meta.json',
                          dict(session_id=sid, environment={'working_directory': cwd},
                               parent_session_id=parent))
        path.with_name('messages.jsonl').write_text('not inspected by metadata discovery')
        return path

    def mistral_unified(self, session_id=None, cwd='/workspace', parent=None):
        sid = session_id or self.sid
        base = '.vibe/logs/session/unified/' + sid
        generation = '0000000000000001'
        runtime = self.write(base + '/generations/' + generation + '/runtime-state.json',
                             dict(session_metadata=dict(cwd=cwd, root_session_id=parent or sid,
                                                        parent_session_id=parent),
                                  identity=dict(kind='subagent' if parent else 'root',
                                                depth=1 if parent else 0, session_id=sid,
                                                root_session_id=parent or sid, parent_session_id=parent)))
        digest = lambda path: hashlib.sha256(path.read_bytes()[:-1]).hexdigest()
        manifest = self.write(base + '/generations/' + generation + '/manifest.json',
                              dict(session_id=sid, generation=generation, snapshot_sequence=0,
                                   runtime_state=dict(path='runtime-state.json', sha256=digest(runtime))))
        current = self.write(base + '/CURRENT',
                             dict(store_format='mistral.vibe.unified-session-store/v1', store_format_minor=8,
                                  session_id=sid, generation=generation, snapshot_sequence=0,
                                  manifest_sha256=digest(manifest)))
        return current, manifest, runtime

    def test_mistral_legacy_exact_resume_preserves_private_and_work_isolation(self):
        self.mistral()
        self.assertEqual(['--resume', self.sid], sessions.resume_arguments(self.home, 'mistral', 'mistral-priv', 'builder'))
        with self.assertRaisesRegex(sessions.SessionError, 'does not match'):
            sessions.resume_arguments(self.home, 'mistral', 'mistral-work', 'builder')
        self.mistral(str(uuid.uuid4()))
        self.assertEqual(['--resume', self.sid], sessions.resume_arguments(self.home, 'mistral', 'mistral-priv', 'builder'))

    def test_mistral_native_opaque_ids_are_valid_but_traversal_is_rejected(self):
        self.mistral('session_opaque-123')
        self.assertEqual(['--resume', 'session_opaque-123'], sessions.resume_arguments(self.home, 'mistral', 'mistral-work', 'builder'))
        for value in ('../unsafe', '', None, 'x' * 129, 'two words'):
            with self.assertRaises(sessions.SessionError):
                sessions.session_identifier(value, 'mistral')

    def test_mistral_subagents_foreign_workspace_and_missing_messages_are_excluded(self):
        self.mistral(parent=str(uuid.uuid4()))
        self.mistral(str(uuid.uuid4()), cwd='/elsewhere')
        path = self.mistral(str(uuid.uuid4()))
        path.with_name('messages.jsonl').unlink()
        self.assertEqual(set(), sessions.histories(self.home, 'mistral'))

    def test_mistral_unified_reads_published_runtime_metadata_without_transcripts(self):
        self.mistral_unified()
        self.mistral_unified(str(uuid.uuid4()), parent=self.sid)
        self.mistral_unified(str(uuid.uuid4()), cwd='/elsewhere')
        self.assertEqual(['--resume', self.sid], sessions.resume_arguments(self.home, 'mistral', 'mistral-work', 'investigator'))

    def test_mistral_unified_digest_mismatch_and_invalid_reference_fail_closed(self):
        current, manifest, runtime = self.mistral_unified()
        runtime.write_text('{}\n')
        with self.assertRaisesRegex(sessions.SessionError, 'metadata'):
            sessions.histories(self.home, 'mistral')
        current, manifest, runtime = self.mistral_unified()
        data = json.loads(current.read_text())
        data['generation'] = '../../foreign'
        current.write_text(json.dumps(data) + '\n')
        with self.assertRaisesRegex(sessions.SessionError, 'generation'):
            sessions.histories(self.home, 'mistral')

    def test_mistral_unified_never_reads_projection_named_as_runtime(self):
        current, manifest, runtime = self.mistral_unified()
        data = json.loads(manifest.read_text())
        data['runtime_state']['path'] = 'projection-state.json'
        manifest.write_text(json.dumps(data) + '\n')
        pointer = json.loads(current.read_text())
        pointer['manifest_sha256'] = hashlib.sha256(manifest.read_bytes()[:-1]).hexdigest()
        current.write_text(json.dumps(pointer) + '\n')
        with self.assertRaisesRegex(sessions.SessionError, 'reference'):
            sessions.histories(self.home, 'mistral')

    def test_mistral_ambiguous_histories_need_exact_active_identity(self):
        self.mistral()
        second = str(uuid.uuid4())
        self.mistral_unified(second)
        with self.assertRaisesRegex(sessions.SessionError, 'Multiple native'):
            sessions.resume_arguments(self.home, 'mistral', 'mistral-priv', 'builder')
        sessions.capture(self.home, 'mistral', 'mistral-priv', 'builder', second)
        self.assertEqual(['--resume', second], sessions.resume_arguments(self.home, 'mistral', 'mistral-priv', 'builder'))

    def test_mistral_active_id_uses_own_native_process_lock_and_excludes_child(self):
        child = str(uuid.uuid4())
        self.mistral(child, parent=self.sid)
        descriptors = [Path('/proc/123/fd/55'), Path('/proc/123/fd/56')]
        targets = [str(self.home / '.vibe/logs/session/active' / (sid + '.lock')) for sid in (self.sid, child)]
        original_iterdir = Path.iterdir
        with mock.patch.object(sessions, '_descendants', return_value={123}), mock.patch.object(Path, 'iterdir', side_effect=lambda path: iter(descriptors) if str(path).startswith('/proc/') else original_iterdir(path), autospec=True), mock.patch.object(sessions.os, 'readlink', side_effect=targets), mock.patch.object(sessions, 'histories', return_value={self.sid}):
            self.assertEqual(self.sid, sessions.discover_active(self.home, 'mistral', 123))

    def test_mistral_active_empty_session_is_authoritative_after_clear(self):
        self.mistral()
        sessions.capture(self.home, 'mistral', 'mistral-work', 'builder')
        new_id = str(uuid.uuid4())
        descriptor = Path('/proc/123/fd/55')
        target = str(self.home / '.vibe/logs/session/active' / (new_id + '.lock'))
        original_iterdir = Path.iterdir
        with mock.patch.object(sessions, '_descendants', return_value={123}), mock.patch.object(Path, 'iterdir', side_effect=lambda path: iter([descriptor]) if str(path).startswith('/proc/') else original_iterdir(path), autospec=True), mock.patch.object(sessions.os, 'readlink', return_value=target):
            active = sessions.discover_active(self.home, 'mistral', 123)
        self.assertEqual(new_id, active)
        self.assertIsNone(sessions.capture(self.home, 'mistral', 'mistral-work', 'builder', active))
        self.assertEqual([], sessions.resume_arguments(self.home, 'mistral', 'mistral-work', 'builder'))
        self.assertEqual(new_id, json.loads((self.home / sessions.POINTER).read_text())['session_id'])

    def test_mistral_hook_ignores_subagent_and_records_parent_identity_only(self):
        import subprocess
        environment = dict(os.environ, HOME=str(self.home))
        payload = dict(session_id=self.sid, cwd='/workspace', parent_session_id=str(uuid.uuid4()))
        command = [os.sys.executable, str(MODULE), 'record-hook', 'mistral', 'mistral-priv', 'builder']
        result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, env=environment)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((self.home / sessions.POINTER).exists())
        payload['parent_session_id'] = None
        result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, env=environment)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(self.sid, json.loads((self.home / sessions.POINTER).read_text())['session_id'])

    def test_new_home_has_no_resume_arguments_for_each_provider(self):
        for vendor in ('claude', 'gemini', 'codex', 'antigravity', 'mistral'):
            self.assertEqual([], sessions.resume_arguments(self.home, vendor, vendor + '-work', 'builder'))
        self.assertFalse((self.home / sessions.POINTER).exists())

    def test_claude_adopts_exact_main_after_nonconversation_header(self):
        self.claude()
        self.assertEqual(['--resume', self.sid], sessions.resume_arguments(self.home, 'claude', 'claude-work', 'investigator'))
        pointer = self.home / sessions.POINTER
        self.assertEqual(0o600, stat.S_IMODE(pointer.stat().st_mode))
        metadata = json.loads(pointer.read_text())
        self.assertEqual(self.sid, metadata['session_id'])
        self.assertNotIn('message', metadata)

    def test_exact_saved_id_does_not_change_when_another_history_is_newer(self):
        self.claude()
        sessions.capture(self.home, 'claude', 'claude-work', 'builder', self.sid)
        self.claude(str(uuid.uuid4()))
        self.assertEqual(['--resume', self.sid], sessions.resume_arguments(self.home, 'claude', 'claude-work', 'builder'))

    def test_multiple_histories_require_explicit_current_id(self):
        self.claude()
        second = str(uuid.uuid4())
        self.claude(second)
        with self.assertRaisesRegex(sessions.SessionError, 'Multiple native'):
            sessions.capture(self.home, 'claude', 'claude-work', 'builder')
        sessions.capture(self.home, 'claude', 'claude-work', 'builder', second)
        self.assertEqual(['--resume', second], sessions.resume_arguments(self.home, 'claude', 'claude-work', 'builder'))

    def test_wrong_account_role_and_vendor_are_rejected(self):
        self.claude()
        sessions.capture(self.home, 'claude', 'claude-work', 'investigator')
        for vendor, account, role in [('claude', 'claude-priv', 'investigator'),
                                      ('claude', 'claude-work', 'builder'),
                                      ('gemini', 'claude-work', 'investigator')]:
            with self.assertRaisesRegex(sessions.SessionError, 'does not match'):
                sessions.resume_arguments(self.home, vendor, account, role)

    def test_missing_saved_history_never_silently_starts_fresh(self):
        path = self.claude()
        sessions.capture(self.home, 'claude', 'claude-work', 'builder')
        path.unlink()
        with self.assertRaisesRegex(sessions.SessionError, 'missing'):
            sessions.resume_arguments(self.home, 'claude', 'claude-work', 'builder')

    def test_pending_hook_identity_with_no_history_allows_empty_first_launch(self):
        sessions._save(self.home, 'gemini', 'gemini-work', 'challenger', self.sid, pending=True)
        self.assertEqual([], sessions.resume_arguments(self.home, 'gemini', 'gemini-work', 'challenger'))
        self.gemini()
        self.assertEqual(['--resume', self.sid], sessions.resume_arguments(self.home, 'gemini', 'gemini-work', 'challenger'))
        self.assertFalse(json.loads((self.home / sessions.POINTER).read_text())['pending'])

    def test_pending_empty_identity_does_not_resurrect_another_history(self):
        sessions._save(self.home, 'gemini', 'gemini-work', 'challenger', self.sid, pending=True)
        self.gemini(str(uuid.uuid4()))
        self.assertEqual([], sessions.resume_arguments(self.home, 'gemini', 'gemini-work', 'challenger'))

    def test_pointer_and_history_symlinks_are_rejected(self):
        target = self.write('other.json', {})
        (self.home / sessions.POINTER).symlink_to(target)
        with self.assertRaisesRegex(sessions.SessionError, 'symlink'):
            sessions.resume_arguments(self.home, 'claude', 'claude-work', 'builder')
        (self.home / sessions.POINTER).unlink()
        native = self.home / '.claude/projects/-workspace'
        native.parent.mkdir(parents=True)
        native.symlink_to(self.home)
        self.write(self.sid + '.jsonl', dict(type='user', sessionId=self.sid, cwd='/workspace'))
        with self.assertRaisesRegex(sessions.SessionError, 'symlink'):
            sessions.resume_arguments(self.home, 'claude', 'claude-work', 'builder')

    def test_insecure_and_corrupt_pointer_are_rejected(self):
        self.claude()
        sessions.capture(self.home, 'claude', 'claude-work', 'builder')
        pointer = self.home / sessions.POINTER
        pointer.chmod(0o644)
        with self.assertRaisesRegex(sessions.SessionError, '0600'):
            sessions.resume_arguments(self.home, 'claude', 'claude-work', 'builder')
        pointer.chmod(0o600)
        pointer.write_text('broken')
        with self.assertRaisesRegex(sessions.SessionError, 'Cannot read'):
            sessions.resume_arguments(self.home, 'claude', 'claude-work', 'builder')

    def test_claude_foreign_workspace_and_sidechain_are_not_main_context(self):
        self.claude(cwd='/elsewhere')
        self.claude(str(uuid.uuid4()), sidechain=True)
        self.assertEqual(set(), sessions.histories(self.home, 'claude'))

    def test_gemini_supports_slug_jsonl_and_legacy_json(self):
        for suffix in ('jsonl', 'json'):
            with self.subTest(suffix=suffix):
                path = self.gemini(suffix=suffix)
                self.assertEqual(['--resume', self.sid], sessions.resume_arguments(self.home, 'gemini', 'gemini-work', 'challenger'))
                path.unlink()

    def test_gemini_subagent_and_foreign_workspace_are_excluded(self):
        self.gemini(kind='subagent')
        self.gemini(str(uuid.uuid4()), cwd='/elsewhere')
        self.write('.gemini/tmp/project-slug/chats/parent/subagent-x.jsonl',
                   dict(sessionId=str(uuid.uuid4()), kind='main',
                        projectHash=hashlib.sha256(b'/workspace').hexdigest()))
        self.assertEqual(set(), sessions.histories(self.home, 'gemini'))

    def test_codex_exact_id_resume_excludes_archived_and_spawned_threads(self):
        path = self.codex()
        child = str(uuid.uuid4())
        self.codex(child)
        self.codex(str(uuid.uuid4()), archived=1)
        self.codex(str(uuid.uuid4()), thread_source='subagent')
        self.codex(str(uuid.uuid4()), cwd='/elsewhere')
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE thread_spawn_edges (child_thread_id TEXT)')
            db.execute('INSERT INTO thread_spawn_edges VALUES (?)', (child,))
        self.assertEqual(['resume', self.sid], sessions.resume_arguments(self.home, 'codex', 'codex-priv', 'builder'))

    def test_corrupt_native_database_does_not_cold_start(self):
        path = self.home / '.codex/state_5.sqlite'
        path.parent.mkdir()
        path.write_text('not sqlite')
        with self.assertRaisesRegex(sessions.SessionError, 'database'):
            sessions.resume_arguments(self.home, 'codex', 'codex-priv', 'builder')

    def test_antigravity_requires_main_workspace_and_conversation_database(self):
        base = self.home / '.gemini/antigravity-cli'
        base.mkdir(parents=True)
        with sqlite3.connect(base / 'conversation_summaries.db') as db:
            db.execute('CREATE TABLE conversation_summaries (conversation_id TEXT, workspace_uris TEXT, parent_conversation_id TEXT, nesting_depth INT)')
            db.execute('INSERT INTO conversation_summaries VALUES (?, ?, ?, ?)',
                       (self.sid, '["file:///workspace"]', '', 0))
        self.assertEqual([], sessions.resume_arguments(self.home, 'antigravity', 'gemini-priv', 'challenger'))
        (base / 'conversations').mkdir()
        (base / 'conversations' / (self.sid + '.db')).touch()
        self.assertEqual(['--conversation', self.sid], sessions.resume_arguments(self.home, 'antigravity', 'gemini-priv', 'challenger'))

    def test_exact_live_empty_session_after_clear_does_not_resume_old_context(self):
        self.claude()
        sessions.capture(self.home, 'claude', 'claude-work', 'builder', self.sid)
        new_id = str(uuid.uuid4())
        self.assertIsNone(sessions.capture(self.home, 'claude', 'claude-work', 'builder', new_id))
        self.assertEqual([], sessions.resume_arguments(self.home, 'claude', 'claude-work', 'builder'))
        self.assertEqual(new_id, json.loads((self.home / sessions.POINTER).read_text())['session_id'])

    def test_invalid_uuid_and_unknown_provider_are_rejected(self):
        for value in ('latest', '../unsafe', '', None):
            with self.assertRaises(sessions.SessionError):
                sessions.identifier(value)
        with self.assertRaises(sessions.SessionError):
            sessions.resume_arguments(self.home, 'other', 'other-work', 'builder')

    def test_active_probe_without_native_tmux_returns_no_id(self):
        with mock.patch.object(sessions.subprocess, 'run', side_effect=FileNotFoundError):
            self.assertIsNone(sessions.discover_active(self.home, 'codex'))

    def test_claude_active_registry_matches_live_pid_start_and_workspace(self):
        self.write('.claude/sessions/123.json', dict(pid=123, procStart='999',
                   cwd='/workspace', kind='interactive', entrypoint='cli', sessionId=self.sid))
        proc_stat = '123 (native process (name)) ' + ' '.join(['S', '1'] + ['0'] * 17 + ['999'])
        with mock.patch.object(sessions, '_descendants', return_value={123}), mock.patch.object(Path, 'read_text', return_value=proc_stat):
            self.assertEqual(self.sid, sessions.discover_active(self.home, 'claude', 123))
        self.write('.claude/sessions/123.json', dict(pid=123, procStart='old',
                   cwd='/workspace', kind='interactive', entrypoint='cli', sessionId=self.sid))
        with mock.patch.object(sessions, '_descendants', return_value={123}), mock.patch.object(Path, 'read_text', return_value=proc_stat):
            self.assertIsNone(sessions.discover_active(self.home, 'claude', 123))

    def test_codex_active_id_comes_from_native_open_writer_lock(self):
        fd = Path('/proc/123/fd/55')
        target = str(self.home / '.codex/thread-writer-locks' / (self.sid + '.lock'))
        with mock.patch.object(sessions, '_descendants', return_value={123}), mock.patch.object(Path, 'iterdir', return_value=iter([fd])), mock.patch.object(sessions.os, 'readlink', return_value=target):
            self.assertEqual(self.sid, sessions.discover_active(self.home, 'codex', 123))
        with mock.patch.object(sessions, '_descendants', return_value={123}), mock.patch.object(Path, 'iterdir', return_value=iter([fd])), mock.patch.object(sessions.os, 'readlink', return_value='/another-account/.codex/thread-writer-locks/' + self.sid + '.lock'):
            self.assertIsNone(sessions.discover_active(self.home, 'codex', 123))

    def test_codex_active_probe_excludes_live_subagent_writer_lock(self):
        self.codex()
        child = str(uuid.uuid4())
        self.codex(child, thread_source='subagent')
        descriptors = [Path('/proc/123/fd/55'), Path('/proc/123/fd/56')]
        targets = [str(self.home / '.codex/thread-writer-locks' / (value + '.lock'))
                   for value in (self.sid, child)]
        with mock.patch.object(sessions, '_descendants', return_value={123}), mock.patch.object(Path, 'iterdir', return_value=iter(descriptors)), mock.patch.object(sessions.os, 'readlink', side_effect=targets):
            self.assertEqual(self.sid, sessions.discover_active(self.home, 'codex', 123))

    def test_antigravity_active_map_requires_exact_workspace_key(self):
        self.write('.gemini/antigravity-cli/cache/last_conversations.json',
                   {'/elsewhere': str(uuid.uuid4()), '/workspace': self.sid})
        self.assertEqual(self.sid, sessions.discover_active(self.home, 'antigravity', 123))

    def test_native_hook_records_only_identity_and_rejects_foreign_workspace(self):
        import subprocess
        environment = dict(os.environ, HOME=str(self.home))
        payload = dict(session_id=self.sid, cwd='/workspace', transcript_path='/not-copied', source='startup')
        command = [os.sys.executable, str(MODULE), 'record-hook', 'gemini', 'gemini-work', 'challenger']
        result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, env=environment)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('', result.stdout)
        pointer = json.loads((self.home / sessions.POINTER).read_text())
        self.assertEqual(self.sid, pointer['session_id'])
        self.assertNotIn('transcript_path', pointer)
        payload['cwd'] = '/another-project'
        result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, env=environment)
        self.assertEqual(1, result.returncode)
        self.assertEqual(pointer, json.loads((self.home / sessions.POINTER).read_text()))

    def test_pointer_survives_project_directory_move(self):
        self.claude()
        sessions.capture(self.home, 'claude', 'claude-work', 'builder')
        moved = self.home / 'renamed-home'
        moved.mkdir()
        for name in ('.claude', sessions.POINTER):
            (self.home / name).rename(moved / name)
        self.assertEqual(['--resume', self.sid], sessions.resume_arguments(moved, 'claude', 'claude-work', 'builder'))


if __name__ == '__main__':
    unittest.main()
