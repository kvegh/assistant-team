import ctypes
import importlib.util
import pathlib
import socket
import tempfile
import unittest
from unittest import mock

SOURCE = pathlib.Path(__file__).parents[1] / 'src/roles/agents_connector/files/connector-team.py'
spec = importlib.util.spec_from_file_location('gateway_socket_team', SOURCE)
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class GatewaySocketTests(unittest.TestCase):
    def library(self, previous=None):
        lib = mock.Mock()
        lib.is_selinux_enabled.return_value = 1
        lib.setsockcreatecon.return_value = 0
        buffer = ctypes.create_string_buffer(previous) if previous else None
        def get_context(pointer):
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof(buffer) if buffer else None
            return 0
        lib.getsockcreatecon.side_effect = get_context
        return lib

    def patch_library(self, lib):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(team.ctypes.util, 'find_library', return_value='libselinux.so.1').start()
        mock.patch.object(team.ctypes, 'CDLL', return_value=lib).start()

    def test_listener_restores_default_before_return_and_exchanges_data(self):
        lib = self.library()
        self.patch_library(lib)
        with tempfile.TemporaryDirectory() as directory, team.gateway_socket() as listener:
            self.assertEqual(lib.setsockcreatecon.call_args_list, [
                mock.call(b'system_u:system_r:container_t:s0'), mock.call(None)])
            path = str(pathlib.Path(directory) / 'ipc.sock')
            listener.bind(path)
            listener.listen(1)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(path)
                with listener.accept()[0] as peer:
                    client.sendall(b'model-free')
                    self.assertEqual(peer.recv(32), b'model-free')

    def test_existing_thread_context_is_preserved_and_released(self):
        lib = self.library(b'system_u:system_r:unconfined_t:s0')
        self.patch_library(lib)
        with team.gateway_socket():
            pass
        self.assertEqual(lib.setsockcreatecon.call_args_list[-1], mock.call(b'system_u:system_r:unconfined_t:s0'))
        lib.freecon.assert_called_once()

    def test_socket_creation_failure_restores_context(self):
        lib = self.library()
        self.patch_library(lib)
        with mock.patch.object(team.socket, 'socket', side_effect=OSError('fixture')), self.assertRaises(OSError):
            team.gateway_socket()
        self.assertEqual(lib.setsockcreatecon.call_args_list[-1], mock.call(None))

    def test_restore_failure_closes_created_listener_and_fails(self):
        lib = self.library()
        lib.setsockcreatecon.side_effect = [0, -1]
        self.patch_library(lib)
        listener = mock.Mock()
        with mock.patch.object(team.socket, 'socket', return_value=listener), self.assertRaisesRegex(RuntimeError, 'restore'):
            team.gateway_socket()
        listener.close.assert_called_once()

    def test_label_failure_never_creates_unlabelled_listener(self):
        lib = self.library()
        lib.setsockcreatecon.return_value = -1
        self.patch_library(lib)
        with mock.patch.object(team.socket, 'socket') as create, self.assertRaisesRegex(RuntimeError, 'assign'):
            team.gateway_socket()
        create.assert_not_called()

    def test_prior_context_query_failure_never_creates_listener(self):
        lib = self.library()
        lib.getsockcreatecon.side_effect = None
        lib.getsockcreatecon.return_value = -1
        self.patch_library(lib)
        with mock.patch.object(team.socket, 'socket') as create, self.assertRaisesRegex(RuntimeError, 'previous'):
            team.gateway_socket()
        create.assert_not_called()

    def test_non_selinux_host_needs_no_context_changes(self):
        lib = self.library()
        lib.is_selinux_enabled.return_value = 0
        self.patch_library(lib)
        with team.gateway_socket():
            pass
        lib.setsockcreatecon.assert_not_called()

    def test_missing_library_fails_closed_only_when_selinux_is_present(self):
        with mock.patch.object(team.ctypes.util, 'find_library', return_value=None):
            with mock.patch.object(team.pathlib.Path, 'exists', return_value=True), self.assertRaisesRegex(RuntimeError, 'libselinux'):
                team.gateway_socket()
            with mock.patch.object(team.pathlib.Path, 'exists', return_value=False), team.gateway_socket():
                pass
