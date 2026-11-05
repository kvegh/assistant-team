"""Prove real URI JSON association preserves integer IDs in both native modes."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,os
from pathlib import Path
import subprocess,sys,tempfile,threading,unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]


class InventoryRegistrationTests(unittest.TestCase):
    def test_legacy_field_template_sends_a_string_in_non_native_mode(self):
        self.run_registration(False,legacy=True)

    def test_actual_uri_registration_sends_integer_association_id_in_both_modes(self):
        for native in (False,True):
            with self.subTest(native=native):self.run_registration(native)

    def run_registration(self,native,legacy=False):
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def respond(self,status,body):
                data=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def do_GET(self):
                if self.path=='/api/controller/v2/inventories/3/groups/?name=assistant_team':self.respond(200,{'count':1,'results':[{'id':2}]})
                else:self.respond(404,{})
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append((self.path,body))
                if self.headers.get('Authorization')!='Bearer synthetic-lifecycle-token':self.respond(403,{});return
                if self.path=='/api/controller/v2/hosts/':self.respond(201,{'id':19})
                elif self.path=='/api/controller/v2/groups/2/hosts/' and type(body.get('id')) is int and body['id']==19:self.respond(204,{})
                else:self.respond(400,{'id':['Expected an integer.']})
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix='inventory-registration-native-')as directory:
                root=Path(directory);tasks=deepcopy(yaml.safe_load((ROOT/'src/roles/deployment_inventory_registration/tasks/main.yml').read_text()))
                if legacy:tasks[0]['block'][-1]['ansible.builtin.uri']['body']={'id':'{{ __deployment_inventory_created_host.json.id | int }}'}
                for block in tasks:block['no_log']=False
                play=root/'fixture.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars':{'__deployment_target_creates':True,'__deployment_target_name':'example-v07',
                    '__inventory_vm_guard_controller_host':'http://127.0.0.1:'+str(server.server_port),'__inventory_vm_guard_inventory_id':'3','__inventory_vm_guard_token':'synthetic-lifecycle-token'},
                    'pre_tasks':[{'ansible.builtin.add_host':{'name':'example-v07','groups':'provisioned_linux_guest','deployment_vm_name':'example-v07','deployment_vm_ip':'192.0.2.55'}}],
                    'tasks':tasks}],sort_keys=False))
                env=dict(os.environ,ANSIBLE_HOME=str(root/'home'),ANSIBLE_LOCAL_TEMP=str(root/'local'),ANSIBLE_REMOTE_TEMP=str(root/'remote'),ANSIBLE_JINJA2_NATIVE=str(native).lower(),ANSIBLE_NOCOLOR='1')
                result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=45)
                self.assertEqual(result.returncode==0,not legacy,result.stdout+result.stderr)
                self.assertEqual(len(requests),2)
                self.assertEqual(requests[-1],('/api/controller/v2/groups/2/hosts/',{'id':'19' if legacy else 19}))
                self.assertEqual(json.loads(requests[0][1]['variables']),{'assistant_vm_name':'example-v07','ansible_host':'192.0.2.55'})
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
