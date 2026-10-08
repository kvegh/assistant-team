import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'src/roles/native_auth/files'


class NativeBootstrapTests(unittest.TestCase):
    def test_fresh_launcher_version_requires_installed_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / '.install/bin').mkdir(parents=True)
            (root / 'tmp').mkdir()
            node = root / '.install/bin/node'
            node.write_text('#!/bin/sh\nprintf "0.160.1\\n"\n')
            node.chmod(0o700)
            (root / '.native-install.json').write_text(json.dumps({
                'flavour': 'codex', 'entrypoint': 'fixture.js',
            }))
            shutil.copyfile(SOURCE / 'native-cli.py', root / '.native-cli.py')
            command = ['python3', str(root / '.native-cli.py'), '--version']
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn('.login-result.py', failed.stderr)
            shutil.copyfile(SOURCE / 'login-result.py', root / '.login-result.py')
            passed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertEqual(passed.stdout.strip(), '0.160.1')
