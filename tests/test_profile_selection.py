"""Real model-free Ansible selection checks using protected temporary directories."""
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]
PROFILES=[v+'-'+c for v in ['claude','gemini','codex','mistral'] for c in ['work','priv']]
SELECTED=['claude-work','claude-priv','gemini-work','gemini-priv','codex-priv','mistral-priv']

@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible required')
class ProfileSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'conf').mkdir(mode=0o700)
        self.config=self.root/'conf/environment.conf'

    def run_selection(self,selected=None,reconcile=False):
        values={'containers':{'runtime_user':pwd.getpwuid(os.getuid()).pw_name},
                '__project_framework_home':str(self.root),
                'project_framework_reconcile_profiles':reconcile}
        if selected is not None:values['project_framework_enabled_profiles']=selected
        play=self.root/'play.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','gather_facts':False,
            'vars':values,'tasks':[{'ansible.builtin.include_role':{'name':'project_framework','tasks_from':'profile_selection'}}]}]))
        env=os.environ.copy();env['ANSIBLE_HOME']=str(self.root/'ansible')
        env['ANSIBLE_REMOTE_TEMP']=str(self.root/'remote');env['ANSIBLE_ROLES_PATH']=str(ROOT/'src/roles')
        env.pop('ANSIBLE_VAULT_PASSWORD_FILE',None)
        return subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(play)],
            cwd=self.root,env=env,capture_output=True,text=True)

    def test_empty_default_does_not_create_policy(self):
        result=self.run_selection();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(self.config.exists())

    def test_explicit_seed_matches_runtime_schema_and_protects_operator_edits(self):
        result=self.run_selection(SELECTED);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        value=json.loads(self.config.read_text())
        self.assertEqual(value,{'version':1,'profiles':{p:{'enabled':p in SELECTED} for p in PROFILES}})
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode),0o600)
        source=ROOT/'src/roles/project_framework/files/environment-config.py'
        spec=importlib.util.spec_from_file_location('seed_config_validator',source)
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        self.assertEqual(helper.environment(self.root),value)
        value['profiles']['claude-work']['enabled']=False
        self.config.write_text(json.dumps(value));original=self.config.read_bytes()
        result=self.run_selection(SELECTED);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.config.read_bytes(),original)
        result=self.run_selection(SELECTED,reconcile=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(json.loads(self.config.read_text())['profiles']['claude-work']['enabled'])

    def test_unknown_or_duplicate_profiles_fail_before_creation(self):
        for selected in [['unknown-priv'],['claude-work','claude-work']]:
            with self.subTest(selected=selected):
                result=self.run_selection(selected)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(self.config.exists())
