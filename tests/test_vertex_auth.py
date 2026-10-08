import importlib.util,json,os,pathlib,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
class VertexAuthenticationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
  spec=importlib.util.spec_from_file_location('vertex_test',ROOT/'src/roles/vertex_auth/files/vertex-runtime.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
  self.m.root=self.root;self.m.CONFIG=self.root/'.vertex.json';self.m.ADC=self.root/'.config/gcloud/application_default_credentials.json';self.m.ADC.parent.mkdir(parents=True)
  self.cfg={'CLAUDE_CODE_USE_VERTEX':'1','CLOUD_ML_REGION':'global','ANTHROPIC_VERTEX_PROJECT_ID':'fixture-project','ANTHROPIC_MODEL':'claude-fixture','ANTHROPIC_DEFAULT_OPUS_MODEL':'claude-fixture','ANTHROPIC_DEFAULT_SONNET_MODEL':'claude-fixture','ANTHROPIC_DEFAULT_HAIKU_MODEL':'claude-fixture'}
 def tearDown(self):self.temp.cleanup()
 def test_environment_uses_scoped_adc_and_rejects_other_provider_fallback(self):
  self.m.CONFIG.write_text(json.dumps(self.cfg));self.m.ADC.write_text('{}')
  original={'ANTHROPIC_API_KEY':'offline-fixture','CLAUDE_CODE_OAUTH_TOKEN':'offline-fixture','CLAUDE_CODE_USE_BEDROCK':'1'}
  env=self.m.environment(original)
  self.assertEqual(env['GOOGLE_APPLICATION_CREDENTIALS'],str(self.m.ADC));self.assertEqual(env['ANTHROPIC_MODEL'],'claude-fixture');self.assertNotIn('ANTHROPIC_API_KEY',env);self.assertNotIn('CLAUDE_CODE_OAUTH_TOKEN',env);self.assertEqual(len(original),3)
 def test_configuration_cannot_import_arbitrary_environment_or_path(self):
  self.cfg['GOOGLE_APPLICATION_CREDENTIALS']='/outside/fixture';self.m.CONFIG.write_text(json.dumps(self.cfg))
  with self.assertRaises(ValueError):self.m.read_config()
 def test_model_alias_requires_explicit_pin(self):
  self.cfg['ANTHROPIC_MODEL']='opus';self.m.CONFIG.write_text(json.dumps(self.cfg))
  with self.assertRaises(ValueError):self.m.read_config()
 def test_login_without_sdk_fails_before_prompt_or_network(self):
  with patch('builtins.input') as prompt,patch.object(self.m.subprocess,'run') as execute:
   with self.assertRaisesRegex(ValueError,'not installed'):self.m.login({})
   prompt.assert_not_called();execute.assert_not_called()
 def test_guided_login_uses_local_gcloud_and_optional_background_defaults(self):
  sdk=self.root/'.install/google-cloud-sdk/bin/gcloud';sdk.parent.mkdir(parents=True);sdk.touch()
  def fake_auth(args,**kwargs):
   self.assertEqual(args[1:4],['auth','application-default','login']);self.assertIn('--no-launch-browser',args);self.assertEqual(kwargs['env']['CLOUDSDK_CONFIG'],str(self.root/'.config/gcloud'));self.m.ADC.write_text('{"type":"authorized_user","refresh_token":"offline-fixture"}')
  with patch('builtins.input',side_effect=['fixture-project','global','claude-fixture','']),patch.object(self.m.subprocess,'run',side_effect=fake_auth):self.m.login({'HOME':str(self.root)})
  cfg=self.m.read_config();self.assertEqual(cfg['ANTHROPIC_DEFAULT_HAIKU_MODEL'],'claude-fixture');self.assertEqual(self.m.CONFIG.stat().st_mode&0o777,0o600)

 def test_gemini_vertex_login_selects_native_vertex_provider_and_preserves_hooks(self):
  (self.root/'.native-install.json').write_text('{"flavour":"gemini"}')
  settings=self.root/'.gemini/settings.json';settings.parent.mkdir();settings.write_text('{"hooks":{"fixture":[]},"security":{"auth":{"selectedType":"oauth-personal"}}}')
  sdk=self.root/'.install/google-cloud-sdk/bin/gcloud';sdk.parent.mkdir(parents=True);sdk.touch()
  def fake_auth(args,**kwargs):self.m.ADC.write_text('{"type":"authorized_user","refresh_token":"offline-fixture"}')
  with patch('builtins.input',side_effect=['fixture-project','global','gemini-fixture']),patch.object(self.m.subprocess,'run',side_effect=fake_auth):self.m.login({'HOME':str(self.root)})
  value=json.loads(settings.read_text());self.assertEqual(value['security']['auth']['selectedType'],'vertex-ai');self.assertEqual(value['security']['auth']['enforcedType'],'vertex-ai');self.assertIn('fixture',value['hooks'])

 def test_invalid_claude_alias_explains_full_id_without_claiming_access(self):
  sdk=self.root/'.install/google-cloud-sdk/bin/gcloud';sdk.parent.mkdir(parents=True);sdk.touch()
  def fake_auth(*args,**kwargs):self.m.ADC.write_text('{}')
  with patch('builtins.input',side_effect=['fixture-project','global','Opus-5','opus','claude-opus-5','']),patch('builtins.print') as output,patch.object(self.m.subprocess,'run',side_effect=fake_auth):
   self.m.login({})
  messages=[call.args[0] for call in output.call_args_list]
  self.assertEqual(sum('not full IDs' in message for message in messages),2)
  self.assertTrue(any('does not check access' in message for message in messages))
  self.assertEqual(self.m.read_config()['ANTHROPIC_MODEL'],'claude-opus-5')

if __name__=='__main__':unittest.main()
