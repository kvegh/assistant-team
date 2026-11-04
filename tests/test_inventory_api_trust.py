"""Exercise real inventory URI calls with default and supplemental private TLS."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('openssl') and shutil.which('ansible-playbook'),
                     'Existing OpenSSL and Ansible are required')
class InventoryApiTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='assistant-inventory-tls-')
        cls.root = Path(cls.temporary.name)
        cls.ca = cls.root / 'server-ca.pem'
        cls.other = cls.root / 'supplemental-ca.pem'
        for certificate, subject in [(cls.ca, 'Synthetic inventory authority'),
                                     (cls.other, 'Unrelated synthetic supplemental authority')]:
            key = certificate.with_suffix('.key')
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-keyout', str(key), '-out', str(certificate), '-days', '1',
                '-subj', '/CN=' + subject, '-addext', 'subjectAltName=IP:127.0.0.1'],
                check=True, capture_output=True)
        cls.malformed = cls.root / 'malformed.pem'
        cls.malformed.write_text('invalid supplemental certificate input')
        cls.requests = []

        class API(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                type(self).respond(self)

            def respond(self):
                cls.requests.append(self.path)
                expected = '/api/controller/v2/inventories/7/hosts/?page_size=200'
                if self.path == expected:
                    authorized = self.headers.get('Authorization') == 'Bearer synthetic-inventory-token'
                    self.send_response(200 if authorized else 401)
                    body = b'{"count":0,"results":[],"next":null}' if authorized else b'{}'
                else:
                    self.send_response(200)
                    body = b'{}'
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)

        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), API)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(cls.ca), str(cls.ca.with_suffix('.key')))
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temporary.cleanup()

    def run_guard(self, native, *, default, supplemental, verify_global=False):
        self.requests.clear()
        with tempfile.TemporaryDirectory(prefix='assistant-inventory-tls-run-') as directory:
            root = Path(directory)
            tasks = [{'name': 'Exercise actual inventory trust and ownership guard',
                      'ansible.builtin.include_role': {'name': 'inventory_vm_guard'}}]
            if verify_global:
                tasks += [
                    {'name': 'Probe unchanged default trust without the role-specific CA',
                     'ansible.builtin.uri': {'url': 'https://127.0.0.1:%s/default-trust-probe' % self.server.server_port,
                                            'validate_certs': True},
                     'register': 'default_probe', 'failed_when': False, 'no_log': True},
                    {'name': 'Require default trust to remain independent',
                     'ansible.builtin.assert': {'that': ['default_probe.status == -1']}}]
            tasks += [
                {'name': 'Inspect combined certificate privacy', 'ansible.builtin.stat': {
                    'path': '{{ __inventory_vm_guard_ca_path }}'}, 'register': 'combined'},
                {'name': 'Require private scoped supplemental trust', 'ansible.builtin.assert': {'that': [
                    'combined.stat.mode == "0600"',
                    '__inventory_vm_guard_ca_path != lookup("env", "AC_AGENTS_CONTROLLER_CA_BUNDLE")',
                    '__inventory_vm_guard_token == "synthetic-inventory-token"']}},
            ]
            play = root / 'guard.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'inventory_vm_guard_name': 'example-v16', 'inventory_vm_guard_operation': 'lookup',
                         'inventory_vm_guard_require_existing': False},
                'tasks': [{'block': tasks, 'always': [
                    {'name': 'Remove this fixture CA file', 'ansible.builtin.file': {
                        'path': '{{ __inventory_vm_guard_combined_ca.path }}', 'state': 'absent'},
                     'when': '__inventory_vm_guard_combined_ca.path is defined', 'no_log': True}]}]}], sort_keys=False))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
                env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                    ANSIBLE_ROLES_PATH=str(ROOT / 'src/roles'), ANSIBLE_JINJA2_NATIVE=str(native).lower(),
                    SSL_CERT_FILE=str(default), AC_AGENTS_CONTROLLER_HOST='https://127.0.0.1:%s' % self.server.server_port,
                    AC_AGENTS_CONTROLLER_TOKEN='synthetic-inventory-token', AC_AGENTS_CONTROLLER_INVENTORY_ID='7',
                    AC_AGENTS_CONTROLLER_CA_BUNDLE=str(supplemental), ANSIBLE_NOCOLOR='1'))
            self.assertNotIn('Bearer synthetic-inventory-token', result.stdout + result.stderr)
            return result

    def test_existing_runtime_ca_survives_an_unrelated_supplemental_bundle(self):
        for native in [False, True]:
            with self.subTest(native=native):
                result = self.run_guard(native, default=self.ca, supplemental=self.other)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(self.requests), 1)

    def test_supplemental_ca_adds_only_scoped_trust_without_changing_defaults(self):
        for native in [False, True]:
            with self.subTest(native=native):
                result = self.run_guard(native, default=self.other, supplemental=self.ca, verify_global=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(self.requests), 1)

    def test_untrusted_or_malformed_ca_cannot_disable_certificate_verification(self):
        for supplemental in [self.other, self.malformed]:
            for native in [False, True]:
                with self.subTest(native=native, malformed=supplemental == self.malformed):
                    result = self.run_guard(native, default=self.other, supplemental=supplemental)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(self.requests, [])


if __name__ == '__main__':
    unittest.main()
