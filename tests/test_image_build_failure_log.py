"""Real Ansible failure/rescue keeps private diagnostics without secret fields."""
from copy import deepcopy
import getpass
import grp
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]


class ImageBuildFailureLogTests(unittest.TestCase):
    def test_failed_build_is_reraised_with_unique_private_whitelisted_logs_in_both_modes(self):
        for native in (False,True):
            with self.subTest(native=native),tempfile.TemporaryDirectory(prefix='image-build-log-test-')as directory:
                root=Path(directory);plugins=root/'plugins';plugins.mkdir()
                (plugins/'image_failure.py').write_text('''from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  return {'failed':True,'changed':False,'msg':'public build failure','stdout':'public stdout','stderr':'public stderr','rc':23,
   'invocation':{'password':'SECRET_BUILD_CANARY'},'environment':{'token':'SECRET_BUILD_CANARY'},'credential':'SECRET_BUILD_CANARY'}
''')
                tasks=yaml.safe_load((ROOT/'src/roles/agent_images/tasks/build.yml').read_text())
                task=deepcopy(next(value for value in tasks if value['name']=='Build the container image for the selected CLI client'))
                build=task['block'][0];build['image_failure']={};build.pop('redhat.rhel_system_roles.podman_image');build.pop('async');build.pop('poll');build.pop('become_user');build['become']=False
                play=root/'fixture.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars':{'containers':{'runtime_user':getpass.getuser()},'assistant_install_root':str(root/'installed'),
                        '__agent_images_available_harness_image':{'rc':1},'agent_images_rebuild_images':False,
                        'podman_host_runtime_home':str(root),'podman_host_runtime_uid':os.getuid()},'tasks':[task]}],sort_keys=False))
                # Owner/group share the same name on managed hosts; this local runner may differ.
                for rescue in task['rescue']:
                    args=rescue.get('ansible.builtin.file',rescue.get('ansible.builtin.copy',{}))
                    if 'group'in args:args['group']=grp.getgrgid(os.getgid()).gr_name
                play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars':{'containers':{'runtime_user':getpass.getuser()},'assistant_install_root':str(root/'installed'),
                        '__agent_images_available_harness_image':{'rc':1},'agent_images_rebuild_images':False,
                        'podman_host_runtime_home':str(root),'podman_host_runtime_uid':os.getuid()},'tasks':[task]}],sort_keys=False))
                env=dict(os.environ,ANSIBLE_HOME=str(root/'home'),ANSIBLE_LOCAL_TEMP=str(root/'local'),ANSIBLE_REMOTE_TEMP=str(root/'remote'),ANSIBLE_ACTION_PLUGINS=str(plugins),ANSIBLE_JINJA2_NATIVE=str(native).lower())
                for attempt in range(2):
                    result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=45)
                    self.assertNotEqual(result.returncode,0)
                    self.assertNotIn('SECRET_BUILD_CANARY',result.stdout+result.stderr)
                    logs=list((root/'installed/environment-logs/image-build').iterdir());self.assertEqual(len(logs),attempt+1)
                    self.assertEqual((root/'installed/environment-logs').stat().st_mode&0o777,0o700)
                    self.assertEqual((root/'installed/environment-logs/image-build').stat().st_mode&0o777,0o700)
                    for log in logs:
                        self.assertEqual(log.stat().st_mode&0o777,0o600)
                        text=log.read_text();self.assertNotIn('SECRET_BUILD_CANARY',text)
                        self.assertEqual(json.loads(text),{'msg':'public build failure','stdout':'public stdout','stderr':'public stderr','rc':23})


if __name__=='__main__':unittest.main()
