import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import Mock,patch

SOURCE=pathlib.Path(__file__).parents[1]/'src/deploy-environment.py'
spec=importlib.util.spec_from_file_location('portable_deployment',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PortableDeploymentTests(unittest.TestCase):
    def run_fixture(self,local,prefix=None):
        with tempfile.TemporaryDirectory() as home:
            root=pathlib.Path(home);vault=root/'destination.vault';vault.write_text('$ANSIBLE_VAULT;fixture')
            password=root/'vpf';password.write_text('fixture-only')
            args=['deploy','--vault-file',str(vault),'--vault-password-file',str(password),'--log-dir',str(root/'logs')]+(['--local'] if local else [])
            if prefix is not None:args.extend(['--prefix',prefix])
            with patch('sys.argv',args),patch.object(module.shutil,'which',return_value='/fixture/tool'),patch.object(module.subprocess,'check_output',return_value='a'*40),patch.object(module.subprocess,'run',side_effect=[Mock(returncode=17),Mock(returncode=23)]) as execute:
                code=module.main()
            self.assertEqual(code,17)
            first=execute.call_args_list[0].args[0]
            extra=json.loads(first[first.index('-e')+1])
            self.assertEqual(extra['assistant_local'],local)
            transfer=execute.call_args_list[1].args[0]
            transferred=json.loads(transfer[transfer.index('-e')+1])
            for values in [extra,transferred]:
                if prefix is None:self.assertNotIn('assistant_install_prefix',values)
                else:self.assertEqual(values['assistant_install_prefix'],prefix)
            self.assertNotIn('fixture-only',str(first))
            run=next((root/'logs').iterdir());summary=json.loads((run/'summary.json').read_text())
            self.assertEqual(summary['exit_code'],17)

    def test_local_connection_is_additive_and_exit_code_survives_transfer_failure(self):self.run_fixture(True)
    def test_remote_connection_remains_available(self):self.run_fixture(False)

    def test_explicit_destination_prefix_reaches_deployment_and_log_transfer(self):
        for local in [False,True]:
            with self.subTest(local=local):self.run_fixture(local,'/srv/agent installations')

    def test_destination_prefix_rejects_controller_relative_paths_and_traversal(self):
        for value in ['relative','~/agents','/srv/../other','/srv/agents\n']:
            with self.subTest(value=value),self.assertRaises(module.argparse.ArgumentTypeError):
                module.destination_prefix(value)
        self.assertEqual(module.destination_prefix('/srv/agents'),pathlib.Path('/srv/agents'))

    def test_export_ignores_raw_output_and_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as home:
            root=pathlib.Path(home);(root/'summary.json').write_text('{"version":1,"run_id":"fixture","exit_code":1,"status":"failed","token":"secret"}')
            (root/'protected-output.log').write_text('DO_NOT_EXPORT')
            with self.assertRaises(ValueError):module.export(root,root/'bundle.tar.gz')

    def test_export_rejects_secrets_in_allowed_values_and_invalid_types(self):
        for record in [
            {'version':1,'run_id':'secret','exit_code':0,'status':'completed'},
            {'version':1,'run_id':123,'exit_code':0,'status':'completed'},
            {'version':1,'run_id':'a'*32,'exit_code':True,'status':'completed'},
        ]:
            with self.assertRaises(ValueError):module.validate_record(record, summary=True)
        for record in [{'category':'task_failed','module':'secret'}, {'category':'secret'}, {'category':'task_ok','task_id':'secret'}, {'category':'task_ok','module':[]}]:
            with self.assertRaises(ValueError):module.validate_record(record)

    def test_export_rejects_source_and_broken_destination_symlinks(self):
        with tempfile.TemporaryDirectory() as home:
            root=pathlib.Path(home);source=root/'source';source.mkdir()
            alias=root/'alias';alias.symlink_to(source,target_is_directory=True)
            with self.assertRaises(ValueError):module.export(alias,root/'bundle')
            output=root/'broken';output.symlink_to(root/'absent')
            with self.assertRaises(ValueError):module.export(source,output)
            self.assertFalse((root/'absent').exists())

    def test_local_initializer_never_prompts_for_ssh_password(self):
        with tempfile.TemporaryDirectory() as home:
            vault=pathlib.Path(home)/'destination.vault';password=pathlib.Path(home)/'vpf'
            def encrypt(*args,**kwargs):
                payload=json.loads(kwargs['input'])
                self.assertEqual(payload['connection']['host'],'localhost')
                self.assertNotIn('password',payload['connection'])
                vault.write_text('$ANSIBLE_VAULT;fixture')
            with patch('builtins.input',return_value='runtime'),patch.object(module.getpass,'getpass',return_value='') as prompt,patch.object(module.subprocess,'run',side_effect=encrypt):
                module.initialize(vault,password,local=True)
            self.assertEqual(prompt.call_count,1)

    def test_prior_run_replay_uses_prescribed_safe_file_and_original_run_id(self):
        with tempfile.TemporaryDirectory() as home:
            root=pathlib.Path(home);vault=root/'vault';vault.write_text('$ANSIBLE_VAULT;fixture')
            run=root/'run';run.mkdir();run_id='a'*32
            (run/'summary.json').write_text(json.dumps({'version':1,'run_id':run_id,'exit_code':17,'status':'failed'}))
            (run/'target-metadata.jsonl').write_text(json.dumps({'timestamp':'2026-10-08T00:00:00+00:00','component':'deployment','action':'deployment','result':'failed','exit_code':17,'correlation_id':run_id})+'\n')
            args=['deploy','--vault-file',str(vault),'--vault-password-file',str(root/'vpf'),'--transfer-run',str(run),'--local']
            with patch('sys.argv',args),patch.object(module.shutil,'which',return_value='/fixture/tool'),patch.object(module.subprocess,'run',return_value=Mock(returncode=0)) as execute:
                self.assertEqual(module.main(),0)
            cmd=execute.call_args.args[0];extra=json.loads(cmd[cmd.index('-e')+1])
            self.assertEqual(extra['assistant_deployment_run_id'],run_id)
            self.assertEqual(extra['assistant_safe_deployment_metadata'],str(run/'target-metadata.jsonl'))
