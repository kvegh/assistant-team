import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ModelStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        spec=importlib.util.spec_from_file_location('model_status',ROOT/'src/roles/project_framework/files/project-team.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.module.ACCOUNT_HOME=self.home
        self.profiles=self.home/'profiles';self.role=self.profiles/'builder';self.role.mkdir(parents=True)
        self.runtime=self.role/'home';self.runtime.mkdir()
        self.core=SimpleNamespace(PROFILES=self.profiles,role_home=lambda role:self.runtime)

    def config(self,vendor,profile):
        (self.role/'profile.json').write_text(json.dumps({'flavour':vendor,'account_profile':profile}))

    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))

    def metadata(self):return self.module.role_model_metadata(self.core,'builder')

    def test_vertex_role_model_and_boundary(self):
        for vendor,key in [('claude','ANTHROPIC_MODEL'),('gemini','GEMINI_MODEL')]:
            self.config(vendor,vendor+'-work')
            self.write(self.runtime/'.vertex.json',{key:'vendor-model-preview','private_project':'never-display'})
            self.assertEqual(self.metadata(),(vendor+'-work','vendor-model-preview (configured)'))

    def test_codex_ignores_section_model_and_authentication(self):
        self.config('codex','codex-priv')
        directory=self.runtime/'.codex';directory.mkdir()
        (directory/'auth.json').write_text('invalid-secret-must-not-be-read')
        config=directory/'config.toml';config.write_text('# comment [bracket]\nmodel = "code-model"\n[profiles.other]\nmodel = "unrelated-model"\n')
        self.assertEqual(self.metadata(),('codex-priv','code-model (configured)'))
        config.write_text('[profiles.other]\nmodel = "unrelated-model"\n')
        self.assertEqual(self.metadata()[1],'harness default (unverified)')

    def test_native_gemini_and_antigravity_model_settings(self):
        for profile,relative in [('gemini-work','.gemini/settings.json'),('gemini-priv','.gemini/antigravity-cli/settings.json')]:
            self.config('gemini',profile)
            self.write(self.runtime/relative,{'model':{'name':'reasoning-model'}})
            self.assertEqual(self.metadata(),(profile,'reasoning-model (configured)'))

    def test_operator_fallback_only_before_launch(self):
        self.config('claude','claude-priv')
        self.write(self.home/'claude-priv/.claude/settings.json',{'model':'personal-model'})
        self.assertEqual(self.metadata()[1],'personal-model (configured)')
        (self.role/'launched').touch()
        self.assertEqual(self.metadata()[1],'harness default (unverified)')

    def test_malformed_unsafe_and_symlink_values_do_not_leak_or_break_status(self):
        self.config('claude','claude-priv')
        path=self.runtime/'settings.json'
        for value in ['token\nforged output',{'unexpected':'secret'},'x'*129]:
            self.write(path,{'model':value,'token':'never-display'})
            self.assertEqual(self.metadata()[1],'harness default (unverified)')
        path.unlink();path.symlink_to(self.home/'missing')
        self.assertEqual(self.metadata()[1],'harness default (unverified)')
        (self.role/'profile.json').write_text('invalid')
        self.assertEqual(self.metadata(),('unknown','unknown (configuration unavailable)'))

    def test_missing_model_does_not_infer_default(self):
        self.config('gemini','gemini-priv')
        self.write(self.runtime/'.gemini/antigravity-cli/settings.json',{'trustedWorkspaces':['private-path']})
        self.assertEqual(self.metadata(),('gemini-priv','harness default (unverified)'))
