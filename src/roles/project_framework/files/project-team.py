#!/usr/bin/env python3
"""Project-scoped control of the existing native container/broker foundation."""
import argparse, importlib.util, json, os, pathlib, re, sqlite3, subprocess, sys, time
INSTALL = pathlib.Path(__file__).resolve().parents[1]
ACCOUNT_HOME = INSTALL.parent
PROJECTS = ACCOUNT_HOME/'projects'
ROLES = ['orchestrator','builder','investigator','challenger','summarizer','observer','private-connector','corporate-connector']

def project_path(name):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,39}',name):
        raise ValueError('Use 1–40 lowercase letters/digits, underscores or hyphens; start with a letter/digit')
    path=PROJECTS/name
    if PROJECTS.is_symlink() or path.is_symlink():raise ValueError('Project paths must not be symlinks')
    return path

def load(name):
    project_path(name)
    os.environ['ASSISTANT_PROJECT']=name
    spec=importlib.util.spec_from_file_location('project_connector',INSTALL/'routing/connector-team.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def user_env():
    env=os.environ.copy();env['XDG_RUNTIME_DIR']='/run/user/'+str(os.getuid());env['DBUS_SESSION_BUS_ADDRESS']='unix:path='+env['XDG_RUNTIME_DIR']+'/bus'
    return env

def control(action,name):
    subprocess.run(['systemctl','--user',action,'assistant-connector@'+name+'.target'],env=user_env(),check=True)

def create(name):
    path=project_path(name)
    if path.exists():raise ValueError('Project already exists; prompts and state were not overwritten')
    PROJECTS.mkdir(mode=0o700,exist_ok=True);path.mkdir(mode=0o700)
    prompts=(ACCOUNT_HOME/'assistant-prompts.md').read_text()
    (path/'assistant-prompt.md').write_text('# Project goal\n\nDescribe this project’s goal, context, boundaries and completion criteria here.\n\n'+prompts)
    for role in ROLES:
        p=path/'profiles'/role
        for directory in ['home','workspace','ipc','reports']:(p/directory).mkdir(mode=0o700,parents=True,exist_ok=True)
        source=INSTALL/'profiles'/role/'profile.json'
        (p/'profile.json').write_bytes(source.read_bytes())
    core=load(name);core.apply_prompts()
    # The actual stock broker opens/migrates the SQLite database, not a guessed schema.
    env=user_env();env['ASSISTANT_PROJECT']=name;env['PATH']=str(INSTALL/'routing')+':'+env.get('PATH','/usr/bin:/bin')
    with (path/'initialize.log').open('w') as logfile:
        broker=subprocess.Popen([str(core.BIN),'broker','--socket',str(core.ADMIN),'--db',str(path/'db.sqlite'),'--session',name],env=env,stdout=logfile,stderr=logfile)
        try:
            core.initialize()
            with sqlite3.connect(path/'db.sqlite') as db:
                tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
                if not {'agents','messages','asks','replies'}<=tables:raise ValueError('Stock broker schema initialization incomplete')
                if db.execute('select count(*) from agents').fetchone()[0]!=5:raise ValueError('Worker registration incomplete')
        finally:
            broker.terminate()
            try:broker.wait(timeout=10)
            except subprocess.TimeoutExpired:broker.kill();broker.wait()
    core.ADMIN.unlink(missing_ok=True)
    (path/'initialized').touch()
    print('Created project '+name+' with stock SQLite schema, eight isolated profiles and editable assistant-prompt.md; no models or containers started.')

def required_auth(name):
    core=load(name);missing=[]
    for role in ROLES:
        cfg=json.loads((core.PROFILES/role/'profile.json').read_text());flavour=cfg['flavour']
        boundary=cfg.get('auth_directory',{'claude':'claude-work','codex':'codex','gemini':'gemini'}[flavour])
        relative={'claude':'.claude/.credentials.json','codex':'.codex/auth.json','gemini':'.gemini/oauth_creds.json'}[flavour]
        # Existing role credentials can have their own native refresh state.
        credential=core.PROFILES/role/'home'/relative
        if not credential.is_file():credential=ACCOUNT_HOME/boundary/relative
        try:
            data=json.loads(credential.read_text())
            if flavour=='claude':valid=isinstance(data.get('claudeAiOauth'),dict) and bool(data['claudeAiOauth'].get('accessToken'))
            elif flavour=='codex':valid=data.get('auth_mode')=='chatgpt' and isinstance(data.get('tokens'),dict) and bool(data['tokens'].get('access_token'))
            else:valid=bool(data.get('access_token') or data.get('refresh_token'))
        except (OSError,ValueError,TypeError):valid=False
        if not valid and boundary not in missing:missing.append(boundary)
    if missing:raise ValueError('Authentication required before starting ANY project service: '+', '.join('cd ~/'+b+' && ./login' for b in missing))
    return core

def verify_project(name):
    path=project_path(name)
    if not (path/'initialized').is_file():raise ValueError('Project is not initialized; create-project NAME first')
    return path

def launch_all(name):
    core=required_auth(name)
    # Credential seeding is selective; container commands do not inherit host API-key variables.
    for role in ROLES:
        cfg=json.loads((core.PROFILES/role/'profile.json').read_text())
        core.seed_auth(role)
    core.apply_prompts()
    for role in ROLES:
        core.launch(role);(core.PROFILES/role/'launched').touch()
    print('Eight native sessions launched without an initial task prompt. Attach the orchestrator; native approvals remain enabled.')

def stop_containers(name):
    core=load(name)
    existing=[core.container(role) for role in ROLES if subprocess.run(['podman','container','exists',core.container(role)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0]
    if existing:core.run(['podman','stop','--time','10',*existing],stdout=subprocess.DEVNULL)
    for role in ROLES:(core.PROFILES/role/'launched').unlink(missing_ok=True)

def status(name):
    core=load(name)
    result=subprocess.run(['systemctl','--user','is-active','assistant-connector@'+name+'.target'],env=user_env(),capture_output=True,text=True)
    print('Project '+name+': '+result.stdout.strip())
    for role in ROLES:
        found=subprocess.run(['podman','inspect','--format','{{.State.Status}}',core.container(role)],capture_output=True,text=True)
        state=found.stdout.strip() if found.returncode==0 else 'not created'
        print(role+': '+state+(' / native launch requested' if (core.PROFILES/role/'launched').exists() else ''))

def main():
    os.umask(0o077)
    p=argparse.ArgumentParser();p.add_argument('action',choices=['create-project','start','stop','restart','status','watch','attach','launch','apply-prompts','refresh-observer','deliver-observer-report','preflight','launch-all','stop-containers']);p.add_argument('project');p.add_argument('role',nargs='?',choices=ROLES);a=p.parse_args()
    if a.action=='create-project':create(a.project);return
    verify_project(a.project)
    if a.action in ['start','restart']:
        required_auth(a.project);control(a.action,a.project)
    elif a.action=='stop':control('stop',a.project)
    elif a.action=='status':status(a.project)
    elif a.action=='preflight':required_auth(a.project)
    elif a.action=='launch-all':launch_all(a.project)
    elif a.action=='stop-containers':stop_containers(a.project)
    else:
        core=load(a.project)
        if a.action=='watch':core.watch()
        elif a.action=='apply-prompts':core.apply_prompts();print('Applied own role sections and project goal; active conversations reload on next launch.')
        elif a.action=='refresh-observer':core.refresh_observer()
        elif a.action=='deliver-observer-report':core.deliver_observer_report()
        elif a.action in ['attach','launch']:
            if not a.role:p.error('ROLE required')
            if a.action=='launch':required_auth(a.project);core.launch(a.role);(core.PROFILES/a.role/'launched').touch()
            else:core.run(['podman','exec','-it',core.container(a.role),'tmux','attach-session','-t','native'])

if __name__=='__main__':
    try:main()
    except (ValueError,subprocess.CalledProcessError,OSError) as error:
        print('Project operation failed: '+str(error),file=sys.stderr);sys.exit(1)
