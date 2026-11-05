"""Keep retirement outside the inventory whose host the Controller must delete."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('openssl') and shutil.which('ansible-playbook'),
                     'Existing OpenSSL and Ansible are required')
class RetirementExecutionInventoryTests(unittest.TestCase):
    def test_real_delete_conflict_is_refused_before_changes_and_separate_execution_succeeds(self):
        plays = yaml.safe_load((ROOT/'src/retire_test_linux_vm.yml').read_text())
        guard = next(task for task in plays[0]['pre_tasks']
                     if task['name']=='Require a separate execution inventory before retiring a managed VM')
        tasks = yaml.safe_load((ROOT/'src/roles/linux_vm_retire/tasks/main.yml').read_text())
        delete = next(task for task in next(task['block'] for task in tasks if 'block' in task)
                      if task['name']=='Remove only the verified retired VM inventory binding')
        with tempfile.TemporaryDirectory(prefix='retire-inventory-conflict-') as temporary:
            root=Path(temporary);certificate=root/'fixture.pem';key=root/'fixture.key'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),
                            '-out',str(certificate),'-days','1','-subj','/CN=Synthetic retirement authority',
                            '-addext','subjectAltName=IP:127.0.0.1'],check=True,capture_output=True)
            requests=[];active_inventory={'id':3}
            class API(BaseHTTPRequestHandler):
                def log_message(self,*_):pass
                def do_DELETE(self):
                    authorized=self.headers.get('Authorization')=='Bearer synthetic-inventory-token'
                    requests.append({'path':self.path,'authorized':authorized})
                    status=401 if not authorized else 409 if active_inventory['id']==3 else 204
                    self.send_response(status);self.end_headers()
                    if status==409:self.wfile.write(b'{"error":"Resource is being used by running jobs.","active_jobs":[41]}')
            server=ThreadingHTTPServer(('127.0.0.1',0),API);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(certificate),str(key));server.socket=context.wrap_socket(server.socket,server_side=True)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                for native in ('true','false'):
                    for guarded,execution in ((False,3),(True,3),(True,9)):
                        with self.subTest(native=native,guarded=guarded,execution=execution):
                            requests.clear();active_inventory['id']=execution
                            marker=root/'native-stage-started';marker.unlink(missing_ok=True)
                            selected=[]
                            if guarded:selected.append(deepcopy(guard))
                            selected += [{'name':'Mark any later physical stage entry','ansible.builtin.file':{
                                'path':str(marker),'state':'touch','mode':'0600'}},deepcopy(delete)]
                            play=root/'fixture.yml'
                            play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                                'vars':{'awx_job_id':41,'awx_inventory_id':str(execution),
                                    '__inventory_vm_guard_matches':[{'id':42}], '__inventory_vm_guard_host':{'id':42},
                                    '__inventory_vm_guard_controller_host':'https://127.0.0.1:'+str(server.server_port),
                                    '__inventory_vm_guard_token':'synthetic-inventory-token',
                                    '__inventory_vm_guard_ca_path':str(certificate)},'tasks':selected}],sort_keys=False))
                            result=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],cwd=ROOT,
                                text=True,capture_output=True,timeout=30,env=dict(os.environ,
                                    ANSIBLE_HOME=str(root/'home'),ANSIBLE_LOCAL_TEMP=str(root/'local'),
                                    ANSIBLE_REMOTE_TEMP=str(root/'remote'),ANSIBLE_JINJA2_NATIVE=native,
                                    ANSIBLE_NOCOLOR='1',AC_AGENTS_CONTROLLER_INVENTORY_ID='3'))
                            self.assertNotIn('Bearer synthetic-inventory-token',result.stdout+result.stderr)
                            if guarded and execution==3:
                                self.assertNotEqual(result.returncode,0)
                                self.assertFalse(marker.exists(),'Same-inventory refusal must precede physical stages')
                                self.assertEqual(requests,[])
                            else:
                                self.assertTrue(marker.exists())
                                self.assertEqual(requests,[{'path':'/api/controller/v2/hosts/42/','authorized':True}])
                                self.assertEqual(result.returncode==0,execution!=3,result.stdout+result.stderr)
            finally:
                server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':unittest.main()
