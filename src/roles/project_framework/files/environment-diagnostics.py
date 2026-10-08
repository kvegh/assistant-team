"""Bounded operator diagnostics; never accepts result bodies or exception text."""
import datetime
import fcntl
import json
import os
import pathlib
import re
import tarfile
import tempfile
import uuid

ACTIONS={'broker_init','gateway','containers_prepare','containers_stop','deployment','setup','login','clear','create-project','start','stop','restart','status','preflight','launch-all','launch','apply-prompts','refresh-observer','deliver-observer-report','stop-containers','watch','attach'}
RESULTS={'started','completed','failed','cancelled','credentials_saved','credentials_unconfirmed'}
MODULES={'unknown','redhat.rhel_system_roles.podman_image'}|{'ansible.builtin.'+name for name in ['setup','assert','include_vars','add_host','getent','set_fact','file','copy','template','command','shell','stat','user','dnf','unarchive','get_url','include_role','include_tasks','systemd_service','slurp']}


def record(home, action, result, exit_code=None):
    if action not in ACTIONS or result not in RESULTS:raise ValueError('Unsupported diagnostic metadata')
    directory=pathlib.Path(home)/'environment-logs'
    if directory.is_symlink():raise ValueError('Diagnostic directory must not be a symlink')
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    event={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'component':'runtime','action':action,'result':result,'correlation_id':uuid.uuid4().hex}
    if type(exit_code) is int:event['exit_code']=exit_code
    lock=os.open(directory/'lock',os.O_CREAT|os.O_RDWR,0o600)
    with os.fdopen(lock,'w') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        path=directory/'events.jsonl'
        if path.is_symlink():raise ValueError('Diagnostic files must not be symlinks')
        if path.exists() and path.stat().st_size>1048576:
            for number in [3,2,1]:
                old=directory/('events.jsonl.'+str(number));new=directory/('events.jsonl.'+str(number+1))
                if number==3:old.unlink(missing_ok=True)
                elif old.exists():old.rename(new)
            path.rename(directory/'events.jsonl.1')
        fd=os.open(path,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
        with os.fdopen(fd,'w') as file:file.write(json.dumps(event)+'\n')


def export(home,destination):
    directory=pathlib.Path(home)/'environment-logs';destination=pathlib.Path(destination)
    if destination.exists():raise ValueError('Export path already exists')
    with tempfile.TemporaryDirectory() as temp:
        names=[]
        for path in sorted(directory.glob('*.jsonl*')):
            if path.is_symlink() or not path.is_file():raise ValueError('Export rejects nonregular diagnostic files')
            for line in path.read_text().splitlines():
                value=json.loads(line)
                if set(value)-{'timestamp','component','action','result','correlation_id','exit_code','module'}:raise ValueError('Unknown diagnostic fields')
                if value.get('action') not in ACTIONS or value.get('result') not in RESULTS:raise ValueError('Unknown diagnostic values')
                if value.get('component') not in ['runtime','deployment']:raise ValueError('Invalid diagnostic component')
                if not re.fullmatch('[a-f0-9]{32}',value.get('correlation_id','')):raise ValueError('Invalid correlation ID')
                datetime.datetime.fromisoformat(value['timestamp'])
                if 'exit_code' in value and type(value['exit_code']) is not int:raise ValueError('Invalid exit code')
                if 'module' in value and value['module'] not in MODULES:raise ValueError('Invalid diagnostic module')
            target=pathlib.Path(temp)/path.name;target.write_bytes(path.read_bytes());names.append(target)
        with tarfile.open(destination,'w:gz') as archive:
            for path in names:archive.add(path,arcname=path.name,recursive=False)
    destination.chmod(0o600)
