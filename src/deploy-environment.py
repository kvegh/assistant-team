#!/usr/bin/env python3
"""User-operated deployment; destination credentials never leave the operator's machine."""
import argparse
import datetime
import getpass
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

REPOSITORY=pathlib.Path(__file__).resolve().parents[1]
MODULES={'ansible.builtin.'+name for name in ['setup','assert','include_vars','add_host','getent','set_fact','file','copy','template','command','shell','stat','user','dnf','unarchive','get_url','include_role','include_tasks','systemd_service','slurp']}|{'redhat.rhel_system_roles.podman_image'}


def validate_record(record,summary=False):
    if not isinstance(record,dict):raise ValueError('Diagnostic record must be an object')
    if summary:
        if set(record)!={'version','run_id','exit_code','status'} or type(record['version']) is not int or record['version']!=1 or not isinstance(record['run_id'],str) or not re.fullmatch('[a-f0-9]{32}',record['run_id']) or record['status'] not in ['completed','failed']:raise ValueError('Invalid diagnostic summary')
    else:
        if set(record)-{'category','task_id','module','exit_code'} or record.get('category') not in ['task_ok','task_failed','connection_failed','task_skipped','playbook_finished']:raise ValueError('Invalid diagnostic event')
        if 'module' in record and (not isinstance(record['module'],str) or record['module'] not in MODULES|{'unknown'}):raise ValueError('Invalid diagnostic module')
        if 'task_id' in record:
            try:uuid.UUID(record['task_id'])
            except (ValueError,AttributeError,TypeError):raise ValueError('Invalid task UUID')
    if 'exit_code' in record and type(record['exit_code']) is not int:raise ValueError('Invalid diagnostic exit code')


def destination_vars(args):
    return {'assistant_destination_vault':str(args.vault_file.resolve()),'assistant_local':args.local}


def transfer_command(args,safe,run_id):
    return ['ansible-playbook',str(REPOSITORY/'src/transfer_deployment_diagnostics.yml'),'--vault-password-file',str(args.vault_password_file.resolve()),'-e',json.dumps(dict(destination_vars(args),assistant_safe_deployment_metadata=str(safe),assistant_deployment_run_id=run_id))]


def export(directory,destination):
    directory=pathlib.Path(directory)
    if any(p.is_symlink() for p in [directory,*directory.parents]):raise ValueError('Diagnostic export source must not traverse symlinks')
    if not directory.is_dir():raise ValueError('Diagnostic source must be a directory')
    files=[]
    for name in ['summary.json','events.jsonl']:
        path=directory/name
        if path.is_symlink():raise ValueError('Diagnostic exports reject symlinks')
        if not path.exists():continue
        if not path.is_file():raise ValueError('Diagnostic metadata must be regular files')
        # Reconstruct prescribed schemas; never copy arbitrary files or remote output.
        records=[json.loads(line) for line in path.read_text().splitlines()] if name.endswith('jsonl') else [json.loads(path.read_text())]
        for record in records:validate_record(record,summary=name=='summary.json')
        files.append((name,records))
    destination=pathlib.Path(destination)
    if destination.is_symlink() or destination.exists():raise ValueError('Export destination already exists or is a symlink')
    if any(p.is_symlink() for p in destination.parents):raise ValueError('Export destination must not traverse symlinks')
    with tempfile.TemporaryDirectory() as temp:
        for name,records in files:
            (pathlib.Path(temp)/name).write_text(''.join(json.dumps(r)+'\n' for r in records) if name.endswith('jsonl') else json.dumps(records[0]))
        with destination.open('xb') as output, tarfile.open(fileobj=output,mode='w:gz') as bundle:
            for name,_ in files:bundle.add(pathlib.Path(temp)/name,arcname=name,recursive=False)
    destination.chmod(0o600)


def initialize(vault,password_file,local=False):
    if vault.exists():raise ValueError('Destination Vault already exists; it was not overwritten')
    data={'connection':{'host':'localhost' if local else input('Destination SSH address: ').strip(),'user':getpass.getuser() if local else input('SSH login user: ').strip()},
          'runtime_user':input('Separate unprivileged runtime user: ').strip(),'install_google_cloud_sdk':False}
    password='' if local else getpass.getpass('SSH password (blank uses your SSH key): ')
    sudo=getpass.getpass('Sudo password (blank uses configured sudo): ')
    if password:data['connection']['password']=password
    if sudo:data['connection']['become_password']=sudo
    subprocess.run(['ansible-vault','encrypt','--vault-password-file',str(password_file),'--output',str(vault),'-'],input=json.dumps(data),text=True,check=True)
    vault.chmod(0o600)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--vault-file',type=pathlib.Path)
    p.add_argument('--vault-password-file',type=pathlib.Path)
    p.add_argument('--init-vault',action='store_true')
    p.add_argument('--syntax-check',action='store_true')
    p.add_argument('--local',action='store_true',help='Deploy on this same machine using Ansible local connection, without SSH')
    p.add_argument('--log-dir',type=pathlib.Path,default=pathlib.Path.home()/'.local/state/assistant-team/deployment-logs')
    p.add_argument('--export',type=pathlib.Path)
    p.add_argument('--run-directory',type=pathlib.Path)
    p.add_argument('--transfer-run',type=pathlib.Path,help='Replay one earlier safe deployment metadata spool to this destination')
    a=p.parse_args();os.umask(0o077)
    if a.export:
        if not a.run_directory:p.error('--export requires --run-directory')
        export(a.run_directory,a.export);return 0
    if not a.vault_file or not a.vault_password_file:p.error('Supply your own --vault-file and --vault-password-file')
    for tool in ['ansible-playbook','ansible-vault']:
        if not shutil.which(tool):raise ValueError(tool+' is required; install approved controller dependencies first')
    if a.init_vault:initialize(a.vault_file.resolve(),a.vault_password_file.resolve(),a.local);return 0
    if not a.vault_file.is_file() or not a.vault_file.read_bytes().startswith(b'$ANSIBLE_VAULT;'):raise ValueError('Destination config must be an Ansible Vault-encrypted file')
    if a.transfer_run:
        safe=a.transfer_run/'target-metadata.jsonl';summary=a.transfer_run/'summary.json'
        if safe.is_symlink() or summary.is_symlink() or not safe.is_file() or not summary.is_file():raise ValueError('Replay requires prescribed regular metadata files')
        info=json.loads(summary.read_text());validate_record(info,summary=True)
        # Target schema validation is independent of remote connection and credentials.
        allowed={'timestamp','component','action','result','exit_code','correlation_id','module'}
        for line in safe.read_text().splitlines():
            value=json.loads(line)
            if set(value)-allowed or value.get('component')!='deployment' or value.get('action')!='deployment' or value.get('result') not in ['completed','failed'] or not re.fullmatch('[a-f0-9]{32}',value.get('correlation_id','')):raise ValueError('Invalid replay metadata')
            datetime.datetime.fromisoformat(value['timestamp'])
            if 'module' in value and value['module'] not in MODULES|{'unknown'}:raise ValueError('Invalid replay module')
            if type(value.get('exit_code')) is not int:raise ValueError('Invalid replay exit code')
        with tempfile.TemporaryDirectory() as temporary:
            env=os.environ.copy();config=pathlib.Path(temporary)/'ansible.cfg';config.write_text('[defaults]\nretry_files_enabled=False\ndisplay_args_to_stdout=False\n');env['ANSIBLE_CONFIG']=str(config)
            return subprocess.run(transfer_command(a,safe.resolve(),info['run_id']),env=env,cwd=REPOSITORY).returncode
    if a.log_dir.is_symlink():raise ValueError('Deployment log directory must not be a symlink')
    a.log_dir.mkdir(mode=0o700,parents=True,exist_ok=True);a.log_dir.chmod(0o700)
    old=sorted([d for d in a.log_dir.iterdir() if d.is_dir() and not d.is_symlink() and re.fullmatch('[a-f0-9]{32}',d.name)],key=lambda d:d.stat().st_mtime)
    for previous in old[:-9]:
        permitted={'ansible.cfg','protected-output.log','protected-transfer.log','summary.json','events.jsonl','target-metadata.jsonl'}
        if all(p.name in permitted and p.is_file() and not p.is_symlink() for p in previous.iterdir()):
            for file in previous.iterdir():file.unlink()
            previous.rmdir()
    run_id=uuid.uuid4().hex;directory=a.log_dir/run_id;directory.mkdir(mode=0o700)
    env=os.environ.copy()
    env['ANSIBLE_CONFIG']=str(directory/'ansible.cfg')
    env['ANSIBLE_CALLBACK_PLUGINS']=str(REPOSITORY/'src/callback_plugins')
    env['ANSIBLE_CALLBACKS_ENABLED']='deployment_metadata'
    env['ASSISTANT_DEPLOYMENT_LOG_DIR']=str(directory)
    try:
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPOSITORY,text=True,stderr=subprocess.DEVNULL).strip()
        dirty=subprocess.check_output(['git','status','--porcelain'],cwd=REPOSITORY,text=True,stderr=subprocess.DEVNULL)
        env['ASSISTANT_BUILD_COMMIT']=revision+('-dirty' if dirty else '')
    except (OSError,subprocess.CalledProcessError):pass
    # Explicit config avoids repository-relative vpf and temporary developer SSH repair paths.
    (directory/'ansible.cfg').write_text('[defaults]\nretry_files_enabled=False\ndisplay_args_to_stdout=False\n[diff]\nalways=False\n')
    command=['ansible-playbook',str(REPOSITORY/'src/deploy_environment.yml'),'--vault-password-file',str(a.vault_password_file.resolve()),'-e',json.dumps(destination_vars(a))]
    if a.syntax_check:command.append('--syntax-check')
    with (directory/'protected-output.log').open('w') as output:
        result=subprocess.run(command,env=env,cwd=REPOSITORY,stdout=output,stderr=subprocess.STDOUT)
    summary={'version':1,'run_id':run_id,'exit_code':result.returncode,'status':'completed' if result.returncode==0 else 'failed'}
    (directory/'summary.json').write_text(json.dumps(summary)+'\n')
    target_event={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'component':'deployment','action':'deployment','result':'completed' if result.returncode==0 else 'failed','exit_code':result.returncode,'correlation_id':run_id}
    target_events=[target_event]
    events=directory/'events.jsonl'
    if events.is_file():
        for line in events.read_text().splitlines():
            entry=json.loads(line)
            if entry.get('category') not in ['task_ok','task_failed','connection_failed','task_skipped']:continue
            event=dict(target_event)
            event['result']='failed' if entry['category'] in ['task_failed','connection_failed'] else 'completed'
            event['module']=entry.get('module') if entry.get('module') in MODULES else 'unknown'
            event['correlation_id']=uuid.uuid4().hex
            if type(entry.get('exit_code')) is int:event['exit_code']=entry['exit_code']
            target_events.append(event)
    safe=directory/'target-metadata.jsonl';safe.write_text(''.join(json.dumps(event)+'\n' for event in target_events))
    if not a.syntax_check:
        transfer=transfer_command(a,safe,run_id)
        with (directory/'protected-transfer.log').open('w') as output:
            moved=subprocess.run(transfer,env=env,cwd=REPOSITORY,stdout=output,stderr=subprocess.STDOUT)
        print('Target diagnostic metadata '+('persisted in runtime ~/environment-logs' if moved.returncode==0 else 'remains in local spool: target unavailable or runtime account not yet created'))
    print('Deployment '+summary['status']+'; exit '+str(result.returncode)+'. Protected local diagnostics: '+str(directory))
    print('Review protected-output.log locally. Share only an explicit metadata export; it excludes output, target details and credentials.')
    return result.returncode


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        print('Deployment operation failed: '+str(error),file=sys.stderr);sys.exit(1)
