import importlib.util
import json
import pathlib
import shlex
import tempfile
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).parents[1]/'src/roles/agents_connector/files/connector-team.py'
spec = importlib.util.spec_from_file_location('codex_startup_team',SOURCE)
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class CodexStartupPolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        root=pathlib.Path(self.directory.name)
        self.profiles=root/'profiles';self.profiles.mkdir()
        builder=self.profiles/'builder';builder.mkdir()
        (builder/'profile.json').write_text(json.dumps({'flavour':'codex','account_profile':'codex-priv'}))
        self.home=builder/'accounts/codex-priv/home';self.home.mkdir(parents=True)
        patcher=patch.multiple(team,PROFILES=self.profiles,STATE=root/'state',VISIBLE=['builder'],READERS=[])
        patcher.start();self.addCleanup(patcher.stop)

    def initialize(self):
        def response(obj):
            return {'kind':'agents'} if obj['kind']=='list_agents' else {'kind':'agent_info','token':'model-free-fixture'}
        with patch.object(team,'rpc',side_effect=response):team.initialize()

    def test_new_config_has_top_level_managed_update_policy_and_hooks(self):
        self.initialize()
        import tomllib
        cfg=tomllib.loads((self.home/'.codex/config.toml').read_text())
        self.assertIs(cfg['check_for_update_on_startup'],False)
        self.assertIs(cfg['features']['hooks'],True)
        self.assertIn('agents_connector',cfg['mcp_servers'])

    def test_existing_operator_config_is_preserved_byte_for_byte(self):
        path=self.home/'.codex/config.toml';path.parent.mkdir()
        original=b'# operator fixture\nmodel = "fixture-model"\ncheck_for_update_on_startup = true\n'
        path.write_bytes(original)
        self.initialize()
        self.assertEqual(path.read_bytes(),original)

    def test_container_launch_disables_update_check_and_retains_security_flags(self):
        with patch.object(team,'seed_auth'),patch.object(team,'start_container'),patch.object(team,'apply_prompts'),patch.object(team,'run') as run:
            team.launch('builder')
        commands=[call.args[0] for call in run.call_args_list]
        argv=shlex.split(commands[-1][-1])
        self.assertEqual(argv,['codex','--no-daemon','-c','check_for_update_on_startup=false','--sandbox','workspace-write','--ask-for-approval','on-request'])
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',argv)
        self.assertFalse((self.home/'.codex/config.toml').exists())
