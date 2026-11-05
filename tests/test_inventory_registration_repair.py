"""Bounded interrupted registration: no association before ownership/native proof."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FILTER = load(ROOT / 'src/filter_plugins/inventory_registration.py', 'repair_filter')
PROBE = load(ROOT / 'src/roles/deployment_inventory_registration/files/verify_interrupted_registration.py', 'repair_probe')


def page(rows):
    return {'count': len(rows), 'results': rows, 'next': None}


def host():
    return {'id': 19, 'name': 'example-v16', 'inventory': 3, 'enabled': True,
            'variables': json.dumps({'assistant_vm_name': 'example-v16', 'ansible_host': '192.168.42.60'})}


def group():
    return {'id': 2, 'name': 'assistant_team', 'inventory': 3}


class RepairTests(unittest.TestCase):
    def test_wrong_host_inventory_group_name_or_ownership_are_refused(self):
        self.assertEqual(FILTER.repair_binding(page([host()]), page([group()]), '3', 'example-v16')['host_id'], 19)
        for row, managed in [({**host(), 'inventory': 4}, group()), (host(), {**group(), 'inventory': 4}),
                             (host(), {**group(), 'name': 'prod'}), ({**host(), 'name': 'other-v16'}, group())]:
            with self.subTest(row=row, managed=managed), self.assertRaises(Exception):
                FILTER.repair_binding(page([row]), page([managed]), '3', 'example-v16')
        for rows in ([], [host(), host()]):
            with self.assertRaises(Exception):
                FILTER.repair_binding(page(rows), page([group()]), '3', 'example-v16')

    def test_every_existing_direct_or_inherited_membership_is_refused(self):
        self.assertTrue(FILTER.ungrouped(page([])))
        for name in ('assistant_team', 'prod', 'other'):
            with self.assertRaises(Exception):
                FILTER.ungrouped(page([{'name': name}]))

    def test_native_clone_descriptor_and_disk_mismatch_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'upstream.qcow2'; source.write_bytes(b'source')
            disk = root / 'example-v16.disk.qcow2'; disk.write_bytes(b'clone')
            machine = Path('/etc/machine-id').read_text().strip()
            config = {'vm_name': 'example-v16', 'generic_image': True, 'vm_dir': str(root),
                      'golden_image_path': str(source), 'vm_network': 'internal', 'vm_vcpus': 2,
                      'vm_memory_mb': 4096, 'vm_disk_gb': 20, 'hypervisor_pin': {'machine_id': machine},
                      'isolation_policy': {'bridges': ['virbr1']}}
            identity = '11111111-2222-4333-8444-555555555555'
            descriptor = {'schema_version': 1, 'deployment_type': 'generic-recovery', 'vm_name': 'example-v16',
                          'uuid': identity, 'hypervisor_machine_id': machine,
                          'source_image_sha256': hashlib.sha256(b'source').hexdigest(), 'host_keys': ['ssh-ed25519 AAAA']}
            def native(*args):
                if 'domuuid' in args: return identity
                if 'dumpxml' in args:
                    return '<domain><name>example-v16</name><uuid>'+identity+'</uuid><description>'+json.dumps(descriptor)+'</description><memory unit="KiB">4194304</memory><vcpu>2</vcpu><devices><disk type="file" device="disk"><source file="'+str(disk)+'"/></disk><interface type="network"><mac address="52:54:00:11:22:33"/><source network="internal"/></interface></devices></domain>'
                if 'qemu-img' in args: return json.dumps({'format': 'qcow2', 'virtual-size': 20*1073741824})
                if 'net-dumpxml' in args: return '<network><name>internal</name><bridge name="virbr1"/></network>'
                if 'net-dhcp-leases' in args: return '52:54:00:11:22:33 ipv4 192.168.42.60/24 example-v16'
                if 'list' in args: return 'example-v16'
                raise AssertionError(args)
            data = {'name': 'example-v16', 'address': '192.168.42.60', 'provisioning': config}
            original_lstat = Path.lstat
            def root_owned(path):
                result = list(original_lstat(path)); result[4] = 0
                return os.stat_result(result)
            with patch.object(PROBE, 'run', side_effect=native), patch.object(Path, 'lstat', root_owned):
                self.assertTrue(PROBE.verify(data)['verified'])
                descriptor['vm_name'] = 'original-production'
                with self.assertRaisesRegex(ValueError, 'provenance'): PROBE.verify(data)
                descriptor['vm_name'] = 'example-v16'; config['vm_dir'] = str(root/'other')
                with self.assertRaises(Exception): PROBE.verify(data)

    def run_native_role(self, native, case='apply'):
        with tempfile.TemporaryDirectory(prefix='assistant-registration-repair-') as directory:
            root=Path(directory); plugins=root/'plugins';plugins.mkdir();writes=root/'writes.json'
            (plugins/'uri.py').write_text('''from ansible.plugins.action import ActionBase
import json,os
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  a=self._task.args;u=a['url'];case=os.environ['REPAIR_CASE'];path=os.environ['REPAIR_WRITES']
  h={'id':19,'name':'example-v16','inventory':4 if case=='wrong_inventory' else 3,'enabled':True,'variables':json.dumps({'assistant_vm_name':'example-v16','ansible_host':'192.168.42.60'})}
  g={'id':2,'name':'prod' if case=='wrong_group' else 'assistant_team','inventory':3}
  if a.get('method')=='POST':
   assert a['body']=={'id':19} and type(a['body']['id'])is int
   open(path,'w').write(json.dumps(a['body']));return {'changed':True}
  if '/inventories/'in u:r=[h]if'/hosts/'in u else[g]
  elif os.path.exists(path):r=[g]
  else:r=[{'name':'prod'}]if case=='prod' else([]if case!='existing'else[g])
  return {'changed':False,'json':{'count':len(r),'results':r,'next':None}}
''')
            (plugins/'command.py').write_text('''from ansible.plugins.action import ActionBase
import json,os
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  return {'changed':False,'stdout':json.dumps({'verified':os.environ['REPAIR_CASE']!='native_mismatch','vm_name':'example-v16','address':'192.168.42.60'}),'rc':0}
''')
            roles=root/'roles';target=roles/'deployment_inventory_registration';(target/'tasks').mkdir(parents=True)
            for stub,content in [('linux_vm','- ansible.builtin.set_fact:\n    __linux_vm_recovery_trust: {path: ""}\n'),('inventory_vm_guard','- ansible.builtin.set_fact:\n    __inventory_vm_guard_ca_path: ""\n')]:
                path=roles/stub/'tasks';path.mkdir(parents=True);(path/('trust.yml'if stub=='inventory_vm_guard'else'recovery-preflight.yml')).write_text(content)
            tasks=(ROOT/'src/roles/deployment_inventory_registration/tasks/repair.yml').read_text().replace('ansible.builtin.uri:','uri:').replace('ansible.builtin.command:','command:')
            (target/'tasks/repair.yml').write_text(tasks);(target/'files').mkdir();(target/'files/verify_interrupted_registration.py').write_text('fixture')
            play=root/'play.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'groups':{'hypervisor':['localhost']},'deployment_vm_name':'example-v16','provisioning':{'vm_name':'example-v16','generic_image':True,'vm_dir':'/opt/vms','golden_image_path':'/opt/images/upstream.qcow2','vm_network':'internal','vm_disk_gb':20,'hypervisor_pin':{},'isolation_policy':{}}},'tasks':[{'ansible.builtin.include_role':{'name':'deployment_inventory_registration','tasks_from':'repair','apply':{'tags':['repair_inventory_registration']}},'tags':['repair_inventory_registration']}]}],sort_keys=False))
            env=dict(os.environ,ANSIBLE_HOME=str(root/'home'),ANSIBLE_LOCAL_TEMP=str(root/'tmp'),ANSIBLE_REMOTE_TEMP=str(root/'remote'),ANSIBLE_ACTION_PLUGINS=str(plugins),ANSIBLE_FILTER_PLUGINS=str(ROOT/'src/filter_plugins'),ANSIBLE_ROLES_PATH=str(roles),ANSIBLE_JINJA2_NATIVE=str(native).lower(),REPAIR_CASE=case,REPAIR_WRITES=str(writes),AC_AGENTS_CONTROLLER_HOST='https://controller.example.invalid',AC_AGENTS_CONTROLLER_TOKEN='synthetic',AC_AGENTS_CONTROLLER_INVENTORY_ID='3')
            inventory=root/'inventory';inventory.write_text('localhost ansible_connection=local\n')
            args=[sys.executable,'-m','ansible.cli.playbook','-i',str(inventory),str(play),'--tags','repair_inventory_registration']
            if case=='preview':args.append('--check')
            result=subprocess.run(args,cwd=ROOT,env=env,text=True,capture_output=True,timeout=45)
            self.assertEqual(result.returncode==0,case in ('apply','preview'),result.stdout+result.stderr)
            self.assertEqual(writes.exists(),case=='apply',result.stdout+result.stderr)

    def test_actual_role_apply_and_check_preview_in_both_native_modes(self):
        for native in (False,True):
            for case in ('apply','preview'):
                with self.subTest(native=native,case=case):self.run_native_role(native,case)

    def test_actual_role_refuses_all_mismatches_before_api_write(self):
        for case in ('wrong_inventory','wrong_group','existing','prod','native_mismatch'):
            with self.subTest(case=case):self.run_native_role(False,case)


if __name__=='__main__':unittest.main()
