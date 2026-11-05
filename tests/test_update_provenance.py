"""Keep guest update provenance tied to the real DNF verification result."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Existing Ansible is required')
class UpdateProvenanceTests(unittest.TestCase):
    def test_actual_update_register_controls_provenance_and_pending_updates_stop_publication(self):
        producer = yaml.safe_load((ROOT/'src/roles/linux_updates/tasks/main.yml').read_text())
        verification = next(task for task in producer if task.get('ansible.builtin.command', {}).get('argv')
                            == ['dnf', '--refresh', 'check-update'])
        provenance = yaml.safe_load((ROOT/'src/tasks/verified_generic_guest.yml').read_text())[0]
        for native in ('true', 'false'):
            for case, rc in (('skipped', None), ('verified', 0), ('pending', 100)):
                with self.subTest(native=native, case=case), tempfile.TemporaryDirectory(prefix='update-provenance-') as temporary:
                    root = Path(temporary)
                    output = root/'provenance.json'
                    tasks = []
                    if rc is not None:
                        check = deepcopy(verification)
                        # Replace only the local command transport; keep the actual
                        # producer's register, changed_when and failure condition.
                        check['ansible.builtin.command']['argv'] = [sys.executable, '-c', 'raise SystemExit('+str(rc)+')']
                        tasks.append(check)
                    tasks += [deepcopy(provenance), {'name':'Inspect only the synthetic provenance result',
                        'ansible.builtin.copy':{'dest':str(output),
                                               'content':'{{ deployment_vm_verified_provenance | to_json }}',
                                               'mode':'0600'}}]
                    variables = {'deployment_vm_provenance':{'vm_name':'example-v07'},
                                 'ansible_facts':{'machine_id':'2'*32}, 'deployment_vm_vcpus':2,
                                 'deployment_vm_memory_mb':4096, 'deployment_vm_disk_gb':20}
                    if case == 'skipped':
                        # A stale similarly named input cannot replace an actual
                        # completed check from the producer role.
                        variables['linux_updates_remaining_updates'] = {'rc':0}
                    play = root/'fixture.yml'
                    play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                                                    'vars':variables,'tasks':tasks}],sort_keys=False))
                    result = subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],
                        cwd=ROOT, capture_output=True, text=True, timeout=30,
                        env=dict(os.environ,ANSIBLE_HOME=str(root/'home'),ANSIBLE_LOCAL_TEMP=str(root/'local'),
                                 ANSIBLE_REMOTE_TEMP=str(root/'remote'),ANSIBLE_JINJA2_NATIVE=native,ANSIBLE_NOCOLOR='1'))
                    if case == 'pending':
                        self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                        self.assertFalse(output.exists(),'A failed DNF check cannot publish successful provenance')
                    else:
                        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                        actual = json.loads(output.read_text())
                        self.assertIs(actual['packages_updated'],case=='verified')


if __name__=='__main__':unittest.main()
