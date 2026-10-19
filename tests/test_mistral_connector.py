import importlib.util
import io
import json
import os
import pathlib
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from unittest import mock


FILE = pathlib.Path(__file__).parents[1] / 'src/roles/agents_connector/files/mistral-hook.py'
SPEC = importlib.util.spec_from_file_location('mistral_hook_test', FILE)
hook = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hook)


class MistralHookTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.cursor = pathlib.Path(temporary.name) / 'state/cursor'
        self.messages = [{'id': 7, 'from': 'orchestrator', 'text': 'Report readiness', 'ask_id': 3}]

    def invoke(self, event, messages, body=None):
        requests = []

        def frame(_, request):
            requests.append(request)
            if request['kind'] == 'authenticate':
                return {'kind': 'agent_info', 'name': 'investigator', 'cli_kind': 'mistral'}
            if request['kind'] == 'read_messages':
                return {'kind': 'messages', 'messages': messages}
            return {'kind': 'ok'}

        with mock.patch.object(hook, 'frame', side_effect=frame):
            result = hook.handle(event, body or {'hook_event_name': event}, None,
                                 'fixture-private-token', self.cursor)
        return result, requests

    def test_pretool_only_marks_busy_and_preserves_native_approval(self):
        output, requests = self.invoke('pre_tool', self.messages)
        self.assertEqual(output, {})
        self.assertEqual([item['kind'] for item in requests], ['authenticate', 'set_agent_state'])
        self.assertEqual(requests[-1]['state'], 'busy')
        self.assertFalse(self.cursor.exists())

    def test_posttool_injects_native_context_and_uses_authenticated_identity(self):
        output, requests = self.invoke('post_tool', self.messages)
        self.assertIn('ASK ask_id=3', output['hook_specific_output']['additional_context'])
        self.assertEqual(requests[-1], {'kind': 'read_messages', 'agent': 'investigator', 'since': 0})
        self.assertEqual(self.cursor.read_text(), '7')
        self.assertEqual(self.cursor.stat().st_mode & 0o777, 0o600)
        _, later = self.invoke('post_tool', [])
        self.assertEqual(later[-1]['since'], 7)
        self.assertNotIn('idle', [item.get('state') for item in requests])

    def test_postagent_pending_inbox_requests_native_retry(self):
        output, requests = self.invoke('post_agent', self.messages)
        self.assertEqual(output['decision'], 'deny')
        self.assertIn('post_reply', output['reason'])
        self.assertNotIn('idle', [item.get('state') for item in requests])

    def test_postagent_quiescent_marks_idle(self):
        output, requests = self.invoke('post_agent', [])
        self.assertEqual(output, {})
        self.assertEqual(requests[-1]['state'], 'idle')

    def test_nested_agent_cannot_consume_or_change_parent_inbox(self):
        output, requests = self.invoke('post_agent', self.messages,
                                       {'parent_session_id': 'parent', 'hook_event_name': 'post_agent'})
        self.assertEqual(output, {})
        self.assertEqual(requests, [])

    def test_bad_authentication_cannot_read_messages(self):
        with mock.patch.object(hook, 'frame', return_value={'kind': 'error'}) as rpc:
            with self.assertRaisesRegex(ValueError, 'authentication'):
                hook.handle('post_agent', {'hook_event_name': 'post_agent'}, None, 'fixture', self.cursor)
        self.assertEqual(rpc.call_count, 1)

    def test_another_native_flavour_registration_is_not_misrepresented(self):
        with mock.patch.object(hook, 'frame', return_value={
                'kind': 'agent_info', 'name': 'investigator', 'cli_kind': 'claude'}) as rpc:
            with self.assertRaisesRegex(ValueError, 'authentication'):
                hook.handle('pre_tool', {'hook_event_name': 'pre_tool'}, None, 'fixture', self.cursor)
        self.assertEqual(rpc.call_count, 1)

    def test_runtime_records_original_session_metadata_before_broker_access(self):
        raw = b'{"hook_event_name":"pre_tool","session_id":"fixture-session","cwd":"/workspace"}'
        arguments = ['mistral-hook.py', '--socket', '/ipc/agent.sock', '--agent-token', 'fixture',
                     '--event', 'pre_tool', '--account-profile', 'mistral-priv', '--role', 'builder']
        with mock.patch.object(sys, 'argv', arguments), \
                mock.patch.object(sys, 'stdin', mock.Mock(buffer=io.BytesIO(raw))), \
                mock.patch.object(sys, 'stdout', io.StringIO()), \
                mock.patch.object(hook.subprocess, 'run', return_value=mock.Mock(returncode=0)) as record, \
                mock.patch.object(hook.socket, 'socket'), \
                mock.patch.object(hook, 'handle', return_value={}) as handle:
            old_umask = os.umask(0o077)
            try:
                hook.main()
            finally:
                os.umask(old_umask)
        self.assertEqual(record.call_args.args[0][-4:], ['record-hook', 'mistral', 'mistral-priv', 'builder'])
        self.assertEqual(record.call_args.kwargs['input'], raw)
        self.assertEqual(record.call_args.kwargs['stdout'], subprocess.DEVNULL)
        self.assertEqual(handle.call_args.args[1]['session_id'], 'fixture-session')

    def test_failed_session_tracking_prevents_broker_inbox_consumption(self):
        raw = b'{"hook_event_name":"post_agent"}'
        arguments = ['mistral-hook.py', '--socket', '/ipc/agent.sock', '--agent-token', 'fixture',
                     '--event', 'post_agent', '--account-profile', 'mistral-work', '--role', 'builder']
        with mock.patch.object(sys, 'argv', arguments), \
                mock.patch.object(sys, 'stdin', mock.Mock(buffer=io.BytesIO(raw))), \
                mock.patch.object(hook.subprocess, 'run', return_value=mock.Mock(returncode=1)), \
                mock.patch.object(hook.socket, 'socket') as connect:
            old_umask = os.umask(0o077)
            try:
                with self.assertRaisesRegex(ValueError, 'session tracking'):
                    hook.main()
            finally:
                os.umask(old_umask)
        connect.assert_not_called()

    def test_mismatched_hook_event_is_rejected_before_authentication(self):
        with mock.patch.object(hook, 'frame') as rpc:
            with self.assertRaisesRegex(ValueError, 'Mismatched'):
                hook.handle('pre_tool', {'hook_event_name': 'post_agent'}, None, 'fixture', self.cursor)
        rpc.assert_not_called()

    def test_cursor_link_cannot_read_outside_role_state(self):
        outside = self.cursor.parent.parent / 'outside'
        outside.write_text('private-not-an-integer')
        self.cursor.parent.mkdir()
        self.cursor.symlink_to(outside)
        with self.assertRaises(OSError):
            self.invoke('post_tool', self.messages)
        self.assertEqual(outside.read_text(), 'private-not-an-integer')

    def test_wire_framing_handles_fragmented_response(self):
        client, server = socket.socketpair()
        self.addCleanup(client.close)
        self.addCleanup(server.close)
        seen = []

        def broker():
            size = struct.unpack('!I', server.recv(4))[0]
            seen.append(json.loads(server.recv(size)))
            raw = json.dumps({'kind': 'agent_info', 'name': 'investigator'}).encode()
            for byte in struct.pack('!I', len(raw)) + raw:
                server.sendall(bytes([byte]))

        worker = threading.Thread(target=broker)
        worker.start()
        response = hook.frame(client, {'kind': 'authenticate', 'agent_token': 'fixture'})
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(response['name'], 'investigator')
        self.assertEqual(seen[0]['kind'], 'authenticate')


class MistralConfigurationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = pathlib.Path(temporary.name)
        self.native = self.home / '.vibe'
        self.native.mkdir()
        self.arguments = ['/opt/connector/bin/agents-connector', 'mcp-shim', '--socket',
                          '/ipc/agent.sock', '--agent-token', 'fixture-token']

    def configure(self):
        hook.configure(self.home, self.arguments, 'fixture-token', profile='mistral-work', role='investigator')

    def test_native_configuration_and_hooks_keep_permissions_at_defaults(self):
        self.configure()
        config = tomllib.loads((self.native / 'config.toml').read_text())
        self.assertFalse(config['enable_update_checks'])
        self.assertFalse(config['enable_auto_update'])
        self.assertEqual(config['mcp_servers'][0]['name'], 'agents_connector')
        self.assertEqual(config['mcp_servers'][0]['args'][1:], self.arguments)
        self.assertFalse(config['mcp_servers'][0]['sampling_enabled'])
        self.assertNotIn('tools', config)
        self.assertNotIn('auto_approve', config)
        hooks = tomllib.loads((self.native / 'hooks.toml').read_text())['hooks']
        self.assertEqual([item['type'] for item in hooks], ['pre_tool', 'post_tool', 'post_agent'])
        self.assertTrue(all('--account-profile mistral-work --role investigator' in item['command']
                            for item in hooks))
        trust = tomllib.loads((self.native / 'trusted_folders.toml').read_text())
        self.assertEqual(trust, {'trusted': ['/workspace'], 'untrusted': []})
        self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in self.native.iterdir()))

    def test_rerun_is_idempotent_and_preserves_operator_text_and_other_mcp_servers(self):
        original = '# Operator preferences\nactive_model = "chosen-model"\nenable_auto_update = true\n'
        original += '[[mcp_servers]]\nname = "other"\ntransport = "stdio"\ncommand = "custom"\n'
        (self.native / 'config.toml').write_text(original)
        self.configure()
        paths = [self.native / name for name in ['config.toml', 'hooks.toml', 'trusted_folders.toml']]
        before = [path.read_text() for path in paths]
        self.configure()
        self.assertEqual(before, [path.read_text() for path in paths])
        self.assertIn(original, before[0])
        parsed = tomllib.loads(before[0])
        self.assertTrue(parsed['enable_auto_update'])
        self.assertEqual([item['name'] for item in parsed['mcp_servers']], ['other', 'agents_connector'])

    def test_text_after_managed_block_survives_a_rerun(self):
        self.configure()
        config = self.native / 'config.toml'
        config.write_text(config.read_text() + '\n[tools.bash]\npermission = "ask"\n')
        self.configure()
        parsed = tomllib.loads(config.read_text())
        self.assertEqual(parsed['tools']['bash']['permission'], 'ask')

    def test_explicit_workspace_denial_is_not_overridden(self):
        for denied in ['/', '/workspace']:
            with self.subTest(denied=denied):
                (self.native / 'trusted_folders.toml').write_text(
                    'trusted = []\nuntrusted = ' + json.dumps([denied]) + '\n')
                self.configure()
                data = tomllib.loads((self.native / 'trusted_folders.toml').read_text())
                self.assertEqual(data['trusted'], [])
                self.assertEqual(data['untrusted'], [denied])

    def test_unmanaged_connector_collision_requires_operator_review(self):
        (self.native / 'config.toml').write_text('[[mcp_servers]]\nname = "agents_connector"\n')
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            self.configure()
        self.assertFalse((self.native / 'hooks.toml').exists())

    def test_unmanaged_hook_and_invalid_toml_are_not_overwritten(self):
        bad = '[[hooks]]\nname = "ac-agents-custom"\n'
        (self.native / 'hooks.toml').write_text(bad)
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            self.configure()
        self.assertEqual((self.native / 'hooks.toml').read_text(), bad)
        (self.native / 'config.toml').write_text('bad = [')
        with self.assertRaises(tomllib.TOMLDecodeError):
            self.configure()

    def test_redirected_config_cannot_receive_broker_token(self):
        outside = self.home / 'outside'
        outside.write_text('private-fixture')
        (self.native / 'config.toml').symlink_to(outside)
        with self.assertRaises(OSError):
            self.configure()
        self.assertEqual(outside.read_text(), 'private-fixture')

    def test_configure_command_accepts_secrets_only_on_stdin(self):
        payload = {'server_arguments': self.arguments, 'agent_token': 'fixture-token',
                   'account_profile': 'mistral-priv', 'role': 'builder'}
        completed = subprocess.run([sys.executable, str(FILE), 'configure', '--home', str(self.home)],
                                   input=json.dumps(payload), text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, '')
        self.assertEqual(completed.stderr, '')
        config = tomllib.loads((self.native / 'config.toml').read_text())
        self.assertIn('fixture-token', config['mcp_servers'][0]['args'])

    def test_configure_error_never_echoes_payload_or_config_secrets(self):
        payload = {'server_arguments': self.arguments, 'agent_token': 'fixture-private-token',
                   'account_profile': 'mistral-priv', 'role': 'builder'}
        (self.native / 'config.toml').write_text('secret = "fixture-private-secret"\nbad = [')
        completed = subprocess.run([sys.executable, str(FILE), 'configure', '--home', str(self.home)],
                                   input=json.dumps(payload), text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn('fixture-private-token', completed.stdout + completed.stderr)
        self.assertNotIn('fixture-private-secret', completed.stdout + completed.stderr)
        self.assertIn('[AC-Agents]', completed.stderr)


if __name__ == '__main__':
    unittest.main()
