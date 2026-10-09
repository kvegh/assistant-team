"""Validate deployment path expressions and unit rendering without host changes."""
import base64
import importlib.util
from pathlib import Path
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('ansible'), 'Ansible is required for template validation')
class AnsibleInstallLayoutTests(unittest.TestCase):
    def setUp(self):
        from ansible.parsing.dataloader import DataLoader
        from ansible.template import Templar
        self.templar_type=Templar;self.loader=DataLoader()
        self.tasks=yaml.safe_load((ROOT/'src/roles/install_layout/tasks/main.yml').read_text())

    def resolve(self,prefix):
        variables={'assistant_install_prefix':prefix,'__install_layout_existing_account':['x','x','x','x','/srv/runtime-home','/bin/sh']}
        for task in self.tasks:
            facts=task.get('ansible.builtin.set_fact',{})
            if any(key in facts for key in ['assistant_runtime_home','assistant_install_root','assistant_profiles_root']):
                templar=self.templar_type(loader=self.loader,variables=variables)
                variables.update(templar.template(facts))
        return variables

    def render_unit(self,kind,variables):
        return self.templar_type(loader=self.loader,variables=variables).template(
            (ROOT/f'src/roles/project_framework/templates/assistant-connector-{kind}@.service.j2').read_text())

    def test_default_prefix_uses_destination_runtime_home(self):
        paths=self.resolve('')
        self.assertEqual(paths['assistant_install_root'],'/srv/runtime-home/ac-agents')
        self.assertEqual(paths['assistant_runtime_home'],'/srv/runtime-home')
        self.assertEqual(paths['assistant_profiles_root'],'/srv/runtime-home/ac-agents/model-environments')

    def test_custom_and_root_parents_produce_one_installation_root(self):
        for prefix,expected in [('/opt/demo/','/opt/demo/ac-agents'),('/','/ac-agents'),('/opt/space % parent','/opt/space % parent/ac-agents')]:
            with self.subTest(prefix=prefix):self.assertEqual(self.resolve(prefix)['assistant_install_root'],expected)

    def test_units_quote_custom_paths_keep_runtime_home_and_preserve_instance_specifier(self):
        paths=self.resolve('/opt/space % parent');paths['__project_framework_uid']=1234
        for kind in ['broker','gateway','containers']:
            with self.subTest(kind=kind):
                unit=self.render_unit(kind,paths)
                self.assertIn('Environment="HOME=/srv/runtime-home"',unit)
                self.assertIn('Environment="AC_AGENTS_ROOT=/opt/space %% parent/ac-agents"',unit)
                self.assertIn('ExecStart="/opt/space %% parent/ac-agents/agent-connector/',unit)
                if kind=='broker':self.assertIn('"/opt/space %% parent/ac-agents/projects/%i/db.sqlite"',unit)

    def test_namespace_guard_accepts_only_matching_generated_root(self):
        paths=self.resolve('/opt/space % parent');paths['__project_framework_uid']=1234
        namespace=yaml.safe_load((ROOT/'src/roles/install_layout/tasks/namespace.yml').read_text())
        guard=next(task for task in namespace if task['name']=='Refuse another installation root using this user service namespace')
        expression=guard['ansible.builtin.assert']['that'][0]
        own=self.render_unit('broker',paths)
        for text,expected in [(own,True),(own.replace('space %% parent','other-root'),False),('[Service]\nExecStart=/legacy/path',False)]:
            variables=dict(paths,__install_layout_candidate_root=paths['assistant_install_root'],item={'content':base64.b64encode(text.encode()).decode()})
            actual=self.templar_type(loader=self.loader,variables=variables).template('{{ '+expression+' }}')
            self.assertEqual(actual,expected)


if __name__=='__main__':unittest.main()


class FreshAccountPreflightTests(unittest.TestCase):
    @unittest.skipUnless(__import__('shutil').which('ansible-playbook'), 'Ansible required')
    def test_missing_runtime_account_skips_legacy_home_inspection(self):
        import os
        import subprocess
        import tempfile
        import uuid
        with tempfile.TemporaryDirectory() as temporary:
            work=Path(temporary)
            play=work/'preflight.yml'
            missing='acfixture'+uuid.uuid4().hex[:12]
            play.write_text(yaml.safe_dump([{
                'hosts':'localhost','gather_facts':False,
                'vars':{'containers':{'runtime_user':missing}},
                'tasks':[
                    {'ansible.builtin.include_tasks':str(ROOT/'src/roles/install_layout/tasks/preflight.yml')},
                    {'ansible.builtin.assert':{'that':[
                        '__install_layout_existing_account == []',
                        '__install_layout_legacy_markers.results | selectattr("skipped", "defined") | list | length == __install_layout_legacy_markers.results | length',
                        '__install_layout_legacy_configs.skipped | bool']}}
                ]}]))
            env=os.environ.copy();env['ANSIBLE_HOME']=str(work/'ansible');env['ANSIBLE_REMOTE_TEMP']=str(work/'remote')
            env.pop('ANSIBLE_VAULT_PASSWORD_FILE',None)
            result=subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(play)],
                cwd=work,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('failed=0',result.stdout)
