import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

LAUNCHER = pathlib.Path(__file__).parents[1] / 'src/roles/native_auth/files/native-cli.py'


class NativeAuthenticationScopeTests(unittest.TestCase):
    def exercise(self, flavour, login=True):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            directory = base / 'provider'
            caller = base / 'caller-home'
            directory.mkdir()
            caller.mkdir()
            prefix = directory / '.install/bin'
            prefix.mkdir(parents=True)
            capture = prefix / ('node' if flavour in ['codex', 'gemini'] else 'native')
            capture.write_text('#!/usr/bin/python3\nimport json,os,pathlib,sys\npathlib.Path(os.environ["HOME"],"saved-config").write_text("fixture")\nprint(json.dumps({"args":sys.argv[1:],"scope":{k:os.environ.get(k) for k in ["HOME","XDG_CONFIG_HOME","XDG_CACHE_HOME","XDG_DATA_HOME","XDG_STATE_HOME","TMPDIR","CLAUDE_CONFIG_DIR","CODEX_HOME","GEMINI_CLI_HOME","VIBE_HOME","NO_BROWSER"]},"cwd":os.getcwd()}))\n')
            capture.chmod(0o700)
            credential = {'claude':('.claude/.credentials.json', {'claudeAiOauth':{'accessToken':'fixture'}}),'codex':('.codex/auth.json',{'tokens':{'access_token':'fixture'}}),'gemini':('.gemini/oauth_creds.json',{'refresh_token':'fixture'})}[flavour]
            capture.write_text(capture.read_text()+ '\np=pathlib.Path(os.environ[\"HOME\"])/'+repr(credential[0])+';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('+repr(json.dumps(credential[1]))+')\n')
            shutil.copyfile(LAUNCHER.parent/'login-result.py', directory/'.login-result.py')
            shutil.copyfile(LAUNCHER, directory / '.native-cli.py')
            (directory / '.native-cli.py').chmod(0o700)
            (directory / 'login').symlink_to('.native-cli.py')
            (directory / '.native-install.json').write_text(json.dumps({'flavour': flavour, 'entrypoint': 'bin/native'}))
            import os
            environment = os.environ.copy()
            environment['HOME'] = str(caller)
            result = subprocess.run([str(directory / 'login')], env=environment, capture_output=True, text=True, check=True)
            output = json.loads(next(line for line in result.stdout.splitlines() if line.startswith('{')))
            for key, value in output['scope'].items():
                if key != 'NO_BROWSER':
                    self.assertTrue(pathlib.Path(value).is_relative_to(directory), key)
            self.assertEqual(output['cwd'], str(directory))
            self.assertTrue((directory / 'saved-config').exists())
            self.assertFalse((caller / 'saved-config').exists())
            self.assertEqual(environment['HOME'], str(caller))
            return output

    def test_claude_login_and_mutable_paths_are_local(self):
        self.assertEqual(self.exercise('claude')['args'], ['auth', 'login'])

    def test_codex_uses_device_auth_and_file_store(self):
        args = self.exercise('codex')['args']
        self.assertIn('cli_auth_credentials_store="file"', args)
        self.assertEqual(args[-2:], ['login', '--device-auth'])

    def test_gemini_google_browser_flow_keeps_its_home_local(self):
        self.assertEqual(self.exercise('gemini')['scope']['NO_BROWSER'], 'true')


if __name__ == '__main__':
    unittest.main()
