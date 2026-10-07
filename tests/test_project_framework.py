import importlib.util,json,os,pathlib,tempfile,unittest
from unittest.mock import patch
SOURCE=pathlib.Path(__file__).resolve().parents[1]/'src/roles/project_framework/files/project-team.py'
def module():
 s=importlib.util.spec_from_file_location('framework_test',SOURCE);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class ProjectFrameworkTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.m=module();self.m.ACCOUNT_HOME=self.root;self.m.PROJECTS=self.root/'projects';self.m.INSTALL=self.root/'agents-connector'
 def tearDown(self):self.tmp.cleanup()
 def test_invalid_or_symlink_names_never_escape_project_parent(self):
  for name in ['../escape','a/b','UPPER','-bad','a\nunit','a'*41]:
   with self.assertRaises(ValueError):self.m.project_path(name)
  self.m.PROJECTS.mkdir();(self.m.PROJECTS/'alias').symlink_to(self.root,target_is_directory=True)
  with self.assertRaises(ValueError):self.m.project_path('alias')
 def test_role_named_project_stop_routes_to_project_not_default_group(self):
  source=SOURCE.parents[2]/'agents_connector/files/connector-team.py'
  spec=importlib.util.spec_from_file_location('routing_core_test',source);core=importlib.util.module_from_spec(spec)
  with patch.dict(os.environ,{},clear=True):spec.loader.exec_module(core)
  with patch('sys.argv',['team','stop','builder']),patch.object(core.os,'execv',side_effect=SystemExit) as execute:
   with self.assertRaises(SystemExit):core.main()
  self.assertEqual(execute.call_args.args[1][-2:],['stop','builder'])
 def test_missing_auth_refuses_before_systemd_start(self):
  core=type('Core',(),{'PROFILES':self.root/'profiles'})()
  for name in self.m.ROLES:
   p=core.PROFILES/name;p.mkdir(parents=True);(p/'profile.json').write_text(json.dumps({'flavour':'claude','auth_directory':'claude-priv' if name=='private-connector' else 'claude-work'}))
  with patch.object(self.m,'load',return_value=core):
   with self.assertRaisesRegex(ValueError,'before starting ANY'):self.m.required_auth('sample')
 def test_api_key_is_not_accepted_as_chatgpt_subscription_auth(self):
  core=type('Core',(),{'PROFILES':self.root/'profiles'})()
  for name in self.m.ROLES:
   p=core.PROFILES/name;p.mkdir(parents=True);(p/'profile.json').write_text('{"flavour":"codex"}')
  (self.root/'codex/.codex').mkdir(parents=True);(self.root/'codex/.codex/auth.json').write_text('{"OPENAI_API_KEY":"dummy"}')
  with patch.object(self.m,'load',return_value=core):
   with self.assertRaises(ValueError):self.m.required_auth('sample')
 def test_existing_native_refreshed_auth_takes_precedence(self):
  core=type('Core',(),{'PROFILES':self.root/'profiles'})()
  for name in self.m.ROLES:
   p=core.PROFILES/name;(p/'home/.codex').mkdir(parents=True);(p/'profile.json').write_text('{"flavour":"codex"}');(p/'home/.codex/auth.json').write_text('{"auth_mode":"chatgpt","tokens":{"access_token":"offline-test"}}')
  with patch.object(self.m,'load',return_value=core):self.assertIs(self.m.required_auth('sample'),core)
 def test_launch_all_uses_all_eight_profiles_without_task_prompts(self):
  from unittest.mock import Mock
  core=Mock();core.PROFILES=self.root/'profiles'
  for name in self.m.ROLES:
   p=core.PROFILES/name;p.mkdir(parents=True);(p/'profile.json').write_text('{"flavour":"claude"}')
  with patch.object(self.m,'required_auth',return_value=core):self.m.launch_all('sample')
  self.assertEqual([x.args[0] for x in core.launch.call_args_list],self.m.ROLES)
  self.assertEqual([x.args[0] for x in core.seed_auth.call_args_list],self.m.ROLES)
  self.assertTrue(all((core.PROFILES/n/'launched').exists() for n in self.m.ROLES))
if __name__=='__main__':unittest.main()
