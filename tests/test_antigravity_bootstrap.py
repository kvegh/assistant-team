"""Real fresh Ansible bootstrap with a local fake binary; no provider/model access."""
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible required')
class AntigravityBootstrapTests(unittest.TestCase):
    def exercise(self,role):
        account=pwd.getpwuid(os.getuid())
        if role=='native_auth':
            markers=['agents-connector','environment.config','team','.local/share/assistant-team/instances',
                     '.local/share/assistant-team/build']+[p+'/.native-install.json' for p in
                     ['claude-work','claude-priv','codex-work','codex-priv','gemini-work','gemini-priv','mistral-work','mistral-priv']]
            if any((Path(account.pw_dir)/p).exists() for p in markers):
                self.skipTest('Real user has a legacy installation; do not inspect or modify it')
            if list((Path(account.pw_dir)/'.config/systemd/user').glob('assistant-connector*')):
                self.skipTest('Real user has an existing service namespace; preserve it')
        with tempfile.TemporaryDirectory() as temporary:
            work=Path(temporary);profile=work/'ac-agents/model-environments/gemini-priv'
            artifact=work/'fixture.tar.gz'
            body=b'#!/bin/sh\nprintf "Antigravity 1.3.1 fixture\\n"\n'
            with tarfile.open(artifact,'w:gz') as archive:
                info=tarfile.TarInfo('antigravity');info.size=len(body);info.mode=0o700
                archive.addfile(info,io.BytesIO(body))
            variables={'containers':{'runtime_user':account.pw_name},
                'assistant_install_prefix':str(work),
                'assistant_source_user':account.pw_name,
                'antigravity_auth_profile_home':str(profile),
                'antigravity_auth_runtime_user':account.pw_name,
                'antigravity_auth_url':artifact.as_uri(),
                'antigravity_auth_checksum':'sha512:'+hashlib.sha512(artifact.read_bytes()).hexdigest(),
                'native_auth_native_auth_dirs':[{'directory':'gemini-priv','flavour':'gemini',
                    'provider':'antigravity','version':'1.3.1','entrypoint':'antigravity/1.3.1/antigravity'}]}
            play=work/'play.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','gather_facts':False,
                'vars':variables,'tasks':[{'ansible.builtin.include_role':{'name':role}}]}]))
            env=os.environ.copy();env['ANSIBLE_HOME']=str(work/'ansible')
            env['ANSIBLE_REMOTE_TEMP']=str(work/'remote');env['ANSIBLE_ROLES_PATH']=str(ROOT/'src/roles')
            env.pop('ANSIBLE_VAULT_PASSWORD_FILE',None)
            self.assertFalse((profile/'.native-cli.py').exists())
            for attempt in range(2):
                result=subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(play)],
                    cwd=work,env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                if attempt:self.assertIn('changed=0',result.stdout)
                for command in ['agy','gemini','login']:
                    self.assertTrue((profile/command).is_symlink())
                    self.assertTrue((profile/command).exists())
                for helper in ['.native-cli.py','.login-result.py','.install-paths.py']:
                    self.assertTrue((profile/helper).is_file())
                probe=subprocess.run([str(profile/'agy'),'--version'],cwd=profile,env=env,
                    capture_output=True,text=True)
                self.assertEqual(probe.returncode,0,probe.stderr)
                self.assertIn('1.3.1 fixture',probe.stdout)
            self.assertEqual(json.loads((profile/'.native-install.json').read_text())['provider'],'antigravity')
            self.assertFalse((profile/'.gemini/antigravity-cli/antigravity-oauth-token').exists())

    def test_standalone_role_starts_without_any_launcher_helpers(self):self.exercise('antigravity_auth')
    def test_generic_native_role_bootstraps_fresh_personal_context(self):self.exercise('native_auth')
