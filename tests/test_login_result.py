import importlib.util
import pathlib
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).parents[1] / 'src/roles/native_auth/files/login-result.py'
spec = importlib.util.spec_from_file_location('login_result', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LoginOutcomeTests(unittest.TestCase):
    def test_clear_rejects_config_symlink_before_removing_any_credentials(self):
        with tempfile.TemporaryDirectory() as home:
            root=pathlib.Path(home)/'claude-priv';(root/'.claude').mkdir(parents=True)
            credential=root/'.claude/.credentials.json';credential.write_text('fixture')
            unrelated=pathlib.Path(home)/'unrelated';unrelated.write_text('preserved')
            (root/'.env').symlink_to(unrelated)
            with self.assertRaises(ValueError):module.clear_profile(root,'claude')
            self.assertTrue(credential.exists());self.assertEqual(unrelated.read_text(),'preserved')
    def test_clear_removes_only_selected_profile_auth_and_preserves_provider_and_settings(self):
        with tempfile.TemporaryDirectory() as home:
            root=pathlib.Path(home)/'gemini-priv';root.mkdir()
            (root/'.gemini').mkdir();(root/'.gemini/oauth_creds.json').write_text('{"refresh_token":"fixture"}')
            (root/'.vertex.json').write_text('{"nonsecret":"preserve"}')
            (root/'.env').write_text('GEMINI_API_KEY=fixture\nUNRELATED=preserve\n')
            other=pathlib.Path(home)/'gemini-work';other.mkdir();(other/'untouched').write_text('preserve')
            module.clear_profile(root,'gemini')
            self.assertFalse((root/'.gemini/oauth_creds.json').exists())
            self.assertTrue((root/'.vertex.json').exists())
            self.assertEqual((root/'.env').read_text(),'UNRELATED=preserve\n')
            self.assertEqual((other/'untouched').read_text(),'preserve')
    def test_personal_gemini_rejects_competing_provider_environment_and_preserves_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'.gemini';path.mkdir()
            (path/'settings.json').write_text('{"security":{"auth":{"selectedType":"gemini-api-key"}},"hooks":{}}')
            env=module.personal_gemini(directory,{'GEMINI_API_KEY':'fixture','GOOGLE_GENAI_USE_VERTEXAI':'true','PATH':'retained'})
            self.assertEqual(env,{'PATH':'retained','GEMINI_FORCE_FILE_STORAGE':'true'})
            import json
            value=json.loads((path/'settings.json').read_text())
            self.assertEqual(value['security']['auth']['selectedType'],'oauth-personal')
            self.assertEqual(value['security']['auth']['enforcedType'],'oauth-personal')
            self.assertIn('hooks',value)
    def test_antigravity_uses_only_its_own_saved_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);path=root/'.gemini/antigravity-cli'
            path.mkdir(parents=True)
            (root/'.gemini/oauth_creds.json').write_text('{"refresh_token":"old-gemini-fixture"}')
            self.assertIsNone(module.credential_snapshot(root,'gemini','antigravity'))
            (path/'antigravity-oauth-token').write_text('{"access_token":"antigravity-fixture"}')
            self.assertEqual(len(module.credential_snapshot(root,'gemini','antigravity')),64)
            module.clear_profile(root,'gemini','antigravity')
            self.assertFalse((path/'antigravity-oauth-token').exists())
            self.assertFalse((root/'.gemini/settings.json').exists())

    def test_antigravity_removes_competing_api_and_vertex_auth_without_forcing_storage(self):
        result=module.personal_antigravity({'GEMINI_API_KEY':'fixture','GOOGLE_APPLICATION_CREDENTIALS':'fixture',
            'GEMINI_FORCE_FILE_STORAGE':'true','PATH':'retained','SSH_CONNECTION':'retained'})
        self.assertEqual(result,{'PATH':'retained','SSH_CONNECTION':'retained'})

    def test_cancelled_login_does_not_reuse_old_credential_evidence(self):
        self.assertEqual(module.result(130, 'old', 'old'), 'Failed or cancelled')
        self.assertEqual(module.result(0, 'old', 'old'), 'Failed or cancelled')
        self.assertEqual(module.result(0, 'old', 'old', interactive=True), 'Failed or cancelled')

    def test_successful_native_login_with_saved_credentials_is_not_model_verification(self):
        self.assertEqual(module.result(0, 'old', 'new'), 'Credentials saved; model access unverified')
        self.assertEqual(module.result(0, None, None), 'Failed or cancelled')

    def test_malformed_or_empty_credential_artifact_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / '.codex'
            path.mkdir()
            for content in ['invalid', '{}', '{"tokens": {"access_token": ""}}']:
                (path / 'auth.json').write_text(content)
                self.assertIsNone(module.credential_snapshot(directory, 'codex'))

    def test_valid_credential_evidence_contains_only_a_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / '.gemini'
            path.mkdir()
            (path / 'oauth_creds.json').write_text('{"refresh_token":"fixture-only"}')
            digest = module.credential_snapshot(directory, 'gemini')
            self.assertEqual(len(digest), 64)
            self.assertNotIn('fixture', digest)


class LoginDisplayTests(unittest.TestCase):
    def test_all_result_labels_have_exact_required_prefix(self):
        for message in ["Failed or cancelled", "Credentials saved; model access unverified", "Model access verified"]:
            self.assertEqual(module.display(message), "[AC-Agents]: " + message)

    def test_follow_up_is_provider_specific_and_never_automatic_inference(self):
        self.assertIn('Antigravity', module.follow_up('gemini', None, False))
        self.assertIn('Google Cloud CLI', module.follow_up('claude', 'vertex', False))
        self.assertIn('No scoped saved credential', module.follow_up('vibe', None, False))
        self.assertIn('no model check ran automatically', module.follow_up('codex', None, True))

    def test_vibe_manual_browser_handoff_reports_success_without_opening_network(self):
        import os,subprocess,sys
        with tempfile.TemporaryDirectory() as directory:
            env=module.vibe_browser_handoff(directory,os.environ.copy())
            result=subprocess.run([sys.executable,'-c',"import webbrowser; assert webbrowser.open('https://example.invalid/auth-fixture')"],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0)
            self.assertEqual(result.stdout,'')
            self.assertNotEqual(env.get('BROWSER'),os.environ.get('BROWSER'))
