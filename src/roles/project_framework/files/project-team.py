#!/usr/bin/env python3
"""Project-scoped control of the existing native container/broker foundation."""
import argparse, importlib.util, json, os, pathlib, re, sqlite3, subprocess, sys, time, shutil, socket, datetime
INSTALL = pathlib.Path(__file__).resolve().parents[1]
ACCOUNT_HOME = INSTALL.parent
PROJECTS = ACCOUNT_HOME/'projects'
ROLES = ['orchestrator','builder','investigator','challenger','summarizer','observer','private-connector','corporate-connector']
PROJECT_ACTIONS = ['create-project','start','stop','restart','status','watch','attach','launch',
                   'apply-prompts','refresh-observer','deliver-observer-report','preflight',
                   'launch-all','stop-containers','destroy','archive','unarchive','rename-project']
GLOBAL_ACTIONS = ['--help','-h','help','--list','list-projects','version','setup','diagnostics']
HELP = '''Usage: team COMMAND [PARAMETERS]

Environment and discovery:
  --help | -h | help                  Show all supported commands; no project required.
  --list | list-projects             List initialized projects and runtime status; no private content read.
  version                            Show installed version and build metadata.
  setup                              Select enabled account profiles; login is optional.
  setup --list                       List enabled/installed profiles and saved-auth status.
  diagnostics --export PATH          Export safe environment diagnostic metadata to PATH.

Projects:
  create-project NAME                Create project directories, prompts, configs and database.
  start NAME                         Check authentication and start this project's team.
  stop NAME                          Stop this project's target and services.
  destroy NAME                       Stop if running, remove its containers, then delete project/config.
  archive NAME                       Stop if running and retain full content/config; always use NAME-ddmmyyhhmm.
  unarchive ARCHIVE                  Copy retained archive to its dated project name; enable target, leave stopped.
  rename-project OLD NEW             Stop OLD, rename identity/config; preserve enablement, leave stopped.
  restart NAME                       Check authentication and restart this project's team.
  status NAME                        Show this project's target and role/container states.
  watch NAME                         Follow messages; Ctrl-C stops only the viewer.
  attach NAME ROLE                   Attach the role's native tmux session; Ctrl-B D detaches.
  launch NAME ROLE                   Launch one role after checking project authentication.
  preflight NAME                     Validate enabled role assignments and saved authentication.
  launch-all NAME                    Launch all eight native role sessions after preflight.
  stop-containers NAME               Stop only this project's role containers.
  apply-prompts NAME                 Render project instructions; effective on next launch.
  refresh-observer NAME              Update the private observer's discussion snapshot.
  deliver-observer-report NAME       Deliver its report privately to the orchestrator.

NAME: 1-40 lowercase letters/digits, underscores or hyphens; start with a letter/digit.
ROLE: orchestrator, builder, investigator, challenger, summarizer, observer,
      private-connector or corporate-connector.
Account profile listing uses setup --list; project listing uses --list.
Archive: always NAME-ddmmyyhhmm (local 24-hour time); collisions fail before stopping.
An existing exact-name archive requires team rename-project OLD NEW first.
'''

def paths(root):
    source=pathlib.Path(__file__).resolve().with_name('install-paths.py')
    if not source.exists():source=pathlib.Path(__file__).resolve().parents[3]/'lib/install-paths.py'
    spec=importlib.util.spec_from_file_location('installation_paths',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.Paths(root)


def settings():
    spec=importlib.util.spec_from_file_location('environment_config',INSTALL/'routing/environment-config.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def diagnostics():
    spec=importlib.util.spec_from_file_location('environment_diagnostics',INSTALL/'routing/environment-diagnostics.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def configure_roles(name):
    module=settings();mapping=module.assignments(ACCOUNT_HOME,name)
    path=project_path(name)
    for role,account in mapping.items():
        p=path/'profiles'/role;cfg=json.loads((p/'profile.json').read_text())
        vendor=module.PROFILES[account]['vendor']
        c='acp-'+name+'-'+role
        existing=subprocess.run(['podman','inspect','--format','{{.State.Running}}',c],capture_output=True,text=True)
        if existing.returncode==0 and existing.stdout.strip()=='true' and cfg.get('account_profile')!=account:
            raise ValueError('Account change pending: stop '+name+' before changing '+role+'; active container was preserved')
    for role,account in mapping.items():
        p=path/'profiles'/role;cfg=json.loads((p/'profile.json').read_text())
        base=p/'accounts'/account
        # Preserve the original profile's native state once, only within its original boundary.
        old=cfg.get('auth_directory',{'claude':'claude-work','codex':'codex-priv','gemini':'gemini-work'}[cfg['flavour']])
        old={'codex':'codex-priv','gemini':'gemini-work'}.get(old,old)
        for kind in ['home','workspace']:
            destination=base/kind
            destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            if not destination.exists() and not cfg.get('account_profile') and account==old and (p/kind).exists():
                (p/kind).rename(destination)
            else:destination.mkdir(mode=0o700,exist_ok=True)
        cfg.update(account_profile=account,auth_directory=account,flavour=module.PROFILES[account]['vendor'])
        module.atomic(p/'profile.json',cfg)

def project_name_validator():
    source=pathlib.Path(__file__).resolve().with_name('project-names.py')
    if not source.exists():source=pathlib.Path(__file__).resolve().parents[3]/'lib/project-names.py'
    spec=importlib.util.spec_from_file_location('project_names',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.validate


def project_path(name):
    project_name_validator()(name,ACCOUNT_HOME)
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
    (path/'workspace').mkdir(mode=0o700)
    core=load(name)
    prompts=core.project_prompt_template((paths(ACCOUNT_HOME).template).read_text())
    (path/'assistant-prompt.md').write_text(prompts)
    for role in ROLES:
        p=path/'profiles'/role
        for directory in ['home','workspace','ipc','reports']:(p/directory).mkdir(mode=0o700,parents=True,exist_ok=True)
        source=INSTALL/'profiles'/role/'profile.json'
        (p/'profile.json').write_bytes(source.read_bytes())
    core.apply_prompts()
    settings().project(ACCOUNT_HOME,name,create=True)
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
    configure_roles(name)
    core=load(name);missing=[]
    for role in ROLES:
        cfg=json.loads((core.PROFILES/role/'profile.json').read_text());flavour=cfg['flavour']
        boundary=cfg.get('auth_directory',{'claude':'claude-work','codex':'codex-priv','gemini':'gemini-work'}[flavour])
        relative={'claude':'.claude/.credentials.json','codex':'.codex/auth.json','gemini':'.gemini/oauth_creds.json'}[flavour]
        if flavour in ['claude','gemini'] and boundary==flavour+'-work':
            provider_path=paths(ACCOUNT_HOME).model(boundary)/'.vertex.json'
            adc=core.role_home(role)/'.config/gcloud/application_default_credentials.json'
            if not adc.is_file():adc=paths(ACCOUNT_HOME).model(boundary)/'.config/gcloud/application_default_credentials.json'
            try:
                provider=json.loads(provider_path.read_text());data=json.loads(adc.read_text())
                allowed=({'CLAUDE_CODE_USE_VERTEX','CLOUD_ML_REGION','ANTHROPIC_VERTEX_PROJECT_ID','ANTHROPIC_MODEL','ANTHROPIC_DEFAULT_OPUS_MODEL','ANTHROPIC_DEFAULT_SONNET_MODEL','ANTHROPIC_DEFAULT_HAIKU_MODEL'} if flavour=='claude' else {'GOOGLE_GENAI_USE_VERTEXAI','GOOGLE_CLOUD_PROJECT','GOOGLE_CLOUD_LOCATION','GEMINI_MODEL'})
                valid=set(provider)==allowed and all(isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9_@.-]+',x) for x in provider.values())
                kind=data.get('type')
                valid=valid and (kind=='authorized_user' and all(data.get(k) for k in ['client_id','client_secret','refresh_token']) or kind=='service_account' and all(data.get(k) for k in ['client_email','private_key','token_uri']))
            except (OSError,ValueError,TypeError):valid=False
            if not valid and boundary not in missing:missing.append(boundary)
            continue
        # Existing role credentials can have their own native refresh state.
        credential=core.role_home(role)/relative
        if not credential.is_file():credential=paths(ACCOUNT_HOME).model(boundary)/relative
        try:
            data=json.loads(credential.read_text())
            if flavour=='claude':valid=isinstance(data.get('claudeAiOauth'),dict) and bool(data['claudeAiOauth'].get('accessToken'))
            elif flavour=='codex':valid=data.get('auth_mode')=='chatgpt' and isinstance(data.get('tokens'),dict) and bool(data['tokens'].get('access_token'))
            else:valid=bool(data.get('access_token') or data.get('refresh_token'))
        except (OSError,ValueError,TypeError):valid=False
        if not valid and boundary not in missing:missing.append(boundary)
    if missing:raise ValueError('Authentication required before starting ANY project service: '+', '.join('cd '+str(paths(ACCOUNT_HOME).model(b))+' && ./login' for b in missing))
    return core

def verify_project(name):
    path=project_path(name)
    if not (path/'initialized').is_file():raise ValueError('Project is not initialized; create-project NAME first')
    return path

def project_summary(name):
    """Read service/container metadata only; running does not imply model readiness."""
    try:
        units=['assistant-connector@'+name+'.target']+[
            'assistant-connector-'+kind+'@'+name+'.service' for kind in ['broker','gateway','containers']]
        states=[service_state(unit)['ActiveState'] for unit in units]
        if 'failed' in states:return 'failed'
        if 'deactivating' in states:return 'stopping'
        if 'activating' in states:return 'starting'
        if states[0]=='active':return 'running'
        if any(state in ['active','reloading'] for state in states):return 'partial'
        if any(project_container_state(name,role) for role in ROLES):return 'partial'
        return 'stopped'
    except (ValueError,OSError,subprocess.CalledProcessError):
        return 'unknown'

def list_projects():
    """List initialized project names without opening prompts, databases or credentials."""
    if PROJECTS.is_symlink():
        raise ValueError('Project paths must not be symlinks')
    names=[]
    if PROJECTS.exists():
        for path in sorted(PROJECTS.iterdir()):
            if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,39}',path.name):
                continue
            if path.is_symlink() or not path.is_dir():
                continue
            required_files=[path/'initialized',path/'db.sqlite',path/'assistant-prompt.md']
            workspace=path/'workspace'
            files_complete=all(not file.is_symlink() and file.is_file() for file in required_files)
            workspace_complete=not workspace.is_symlink() and workspace.is_dir()
            if files_complete and workspace_complete:
                names.append(path.name)
    if not names:
        print('No initialized projects. Use: team create-project NAME');return
    width=max(4,max(map(len,names)))
    print('NAME'.ljust(width)+'  STATUS')
    summaries=[(name,project_summary(name)) for name in names]
    for name,state in summaries:print(name.ljust(width)+'  '+state)
    if any(state=='unknown' for _,state in summaries):
        print('Unknown status: check the user systemd bus and Podman access; no service was started.')

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

ARCHIVE_METADATA='.assistant-archive.json'

class ArchiveCollisionError(ValueError):
    """A safe minute-resolution name collision, rejected before shutdown."""


def archive_timestamp():
    return datetime.datetime.now().astimezone()

def plan_archive(name, path, when):
    parent=ACCOUNT_HOME/'project-archive';plain=parent/name
    if parent.is_symlink() or parent.exists() and not parent.is_dir():
        raise ValueError('Archive parent must be a directory, not a symlink')
    if plain.exists() or plain.is_symlink():
        raise ArchiveCollisionError('An archive with this exact project name already exists; project was not stopped. Use team rename-project OLD NEW before archiving')
    destination=parent/(name+'-'+when.strftime('%d%m%y%H%M'))
    if destination.exists() or destination.is_symlink():
        raise ArchiveCollisionError('Archive timestamp collision; archives and project were preserved without stopping')
    return {'destination':destination,'archived_at':when.isoformat(timespec='seconds')}

def lifecycle_paths(name, archive=False, when=None):
    path=verify_project(name);config=paths(ACCOUNT_HOME).project_config(name)
    if not archive and not shutil.rmtree.avoids_symlink_attacks:
        raise ValueError('This platform cannot safely remove a project directory')
    if ACCOUNT_HOME.is_symlink() or config.is_symlink() or not config.is_file():
        raise ValueError('Project configuration must be a regular file inside the account home')
    plan=None
    if archive:
        metadata=path/ARCHIVE_METADATA
        if metadata.exists() or metadata.is_symlink():
            raise ValueError('Reserved archive metadata already exists; project was not stopped')
        plan=plan_archive(name,path,when or archive_timestamp())
    return path,config,plan

def service_state(unit):
    result=subprocess.run(['systemctl','--user','show',unit,
                           '--property=ActiveState,LoadState,UnitFileState'],
                          env=user_env(),capture_output=True,text=True)
    values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    absent=values.get('LoadState')=='not-found' and values.get('ActiveState')=='inactive'
    if (result.returncode and not absent or
        values.get('LoadState') not in ['loaded','masked','not-found'] or
        values.get('ActiveState') not in ['active','activating','deactivating','reloading','inactive','failed']):
        raise ValueError('Cannot establish project service state; project files were preserved')
    return values

def project_container_state(name, role):
    c='acp-'+name+'-'+role
    exists=subprocess.run(['podman','container','exists',c],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if exists.returncode==1:return None
    if exists.returncode!=0:raise ValueError('Cannot establish project container state; project files were preserved')
    state=subprocess.run(['podman','inspect','--format','{{.State.Running}}',c],capture_output=True,text=True)
    if state.returncode or state.stdout.strip() not in ['true','false']:
        raise ValueError('Cannot establish project container state; project files were preserved')
    return state.stdout.strip()=='true'

def verify_no_project_listener(path):
    endpoints=[path/'broker.sock']+[path/'profiles'/role/'ipc/agent.sock' for role in ROLES]
    for endpoint in endpoints:
        if endpoint.is_symlink() or endpoint.parent.is_symlink():
            raise ValueError('Project socket paths must not be symlinks')
        if not endpoint.exists():continue
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            try:probe.connect(str(endpoint))
            except (ConnectionRefusedError,FileNotFoundError):continue
            except OSError as error:
                raise ValueError('Cannot establish project writer state; project files were preserved') from error
            raise ValueError('A project broker or gateway is still listening; project files were preserved')

def quiesce_project(name, path):
    units=['assistant-connector@'+name+'.target']+[
        'assistant-connector-'+kind+'@'+name+'.service' for kind in ['broker','gateway','containers']]
    states={unit:service_state(unit) for unit in units}
    running=[unit for unit,state in states.items() if state['ActiveState'] not in ['inactive','failed']]
    if running:subprocess.run(['systemctl','--user','stop',*running],env=user_env(),check=True)
    for unit,state in states.items():
        if state.get('UnitFileState') in ['enabled','enabled-runtime']:
            args=['systemctl','--user','disable']
            if state['UnitFileState']=='enabled-runtime':args.append('--runtime')
            subprocess.run(args+[unit],env=user_env(),check=True)
    containers=['acp-'+name+'-'+role for role in ROLES if project_container_state(name,role)]
    if containers:subprocess.run(['podman','stop','--time','10',*containers],check=True,stdout=subprocess.DEVNULL)
    if any(service_state(unit)['ActiveState'] not in ['inactive','failed'] for unit in units):
        raise ValueError('Project services did not stop; project files were preserved')
    remaining=[]
    for role in ROLES:
        state=project_container_state(name,role)
        if state is True:raise ValueError('Project containers did not stop; project files were preserved')
        if state is False:remaining.append('acp-'+name+'-'+role)
    verify_no_project_listener(path)
    if remaining:subprocess.run(['podman','rm',*remaining],check=True,stdout=subprocess.DEVNULL)

def project_units(name):
    return ['assistant-connector@'+name+'.target']+[
        'assistant-connector-'+kind+'@'+name+'.service' for kind in ['broker','gateway','containers']]

def loaded_project_units(name):
    units=project_units(name);env=user_env();env.update(LC_ALL='C',SYSTEMD_COLORS='0')
    result=subprocess.run(['systemctl','--user','list-units','--all','--no-legend',
                           '--plain','--full','--no-pager',*units],env=env,capture_output=True,text=True)
    if result.returncode:raise ValueError('Cannot verify named systemd instances were forgotten; project files were preserved')
    loaded=[]
    for line in result.stdout.splitlines():
        fields=line.split()
        if not fields:continue
        if len(fields)<4 or fields[0] not in units:
            raise ValueError('Unexpected systemd unit-list response; project files were preserved')
        loaded.append(fields[0])
    return loaded

def forget_project_units(name, timeout=10):
    """Reset only named failures; ListUnits observes GC without loading templates."""
    present=loaded_project_units(name)
    if present:
        reset=subprocess.run(['systemctl','--user','reset-failed',*present],env=user_env(),
                             capture_output=True,text=True)
        if reset.returncode and loaded_project_units(name):
            raise ValueError('Could not clear named systemd instance failures; project files were preserved')
    deadline=time.monotonic()+timeout
    while loaded_project_units(name):
        if time.monotonic()>=deadline:
            raise ValueError('Named systemd instances are still referenced; project files were preserved')
        time.sleep(0.2)


def retire_project(name, archive=False):
    when=archive_timestamp() if archive else None
    path,config,plan=lifecycle_paths(name,archive,when)
    quiesce_project(name,path)
    forget_project_units(name)
    # Recheck operator-editable paths after shutdown, before destructive filesystem work.
    if lifecycle_paths(name,archive,when)[2]!=plan:
        raise ValueError('Archive state changed during shutdown; project files were preserved')
    if archive:
        destination=plan['destination']
        destination.parent.mkdir(mode=0o700,exist_ok=True);destination.parent.chmod(0o700)
        metadata=path/ARCHIVE_METADATA
        created_metadata=False
        try:
            with metadata.open('x') as file:
                created_metadata=True
                os.fchmod(file.fileno(),0o600)
                json.dump({'version':1,'archived_at':plan['archived_at'],'timestamp_basis':'operation_start'},file)
                file.write('\n')
            config.chmod(0o600);path.chmod(0o700)
            path.rename(destination)
        except OSError as error:
            rollback_errors=[]
            for operation,needed in [(lambda:metadata.unlink(),created_metadata)]:
                if needed:
                    try:operation()
                    except OSError:rollback_errors.append(True)
            if rollback_errors:
                raise ValueError('Archive failed and rollback was incomplete; inspect retained project and archive files before retrying') from error
            raise
        print('Archived project '+name+' to '+str(destination)+'; account profiles and other projects were preserved.')
    else:
        shutil.rmtree(path)
        print('Destroyed project '+name+'; account profiles, images and other projects were preserved.')

def status(name):
    core=load(name)
    result=subprocess.run(['systemctl','--user','is-active','assistant-connector@'+name+'.target'],env=user_env(),capture_output=True,text=True)
    print('Project '+name+': '+result.stdout.strip())
    for role in ROLES:
        found=subprocess.run(['podman','inspect','--format','{{.State.Status}}',core.container(role)],capture_output=True,text=True)
        state=found.stdout.strip() if found.returncode==0 else 'not created'
        print(role+': '+state+(' / native launch requested' if (core.PROFILES/role/'launched').exists() else ''))

def unarchive(archive):
    spec=importlib.util.spec_from_file_location('project_unarchive',INSTALL/'routing/unarchive-project.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.restore(sys.modules[__name__],archive)


def main():
    action=sys.argv[1] if len(sys.argv)>1 else None
    if action is None:raise ValueError('A command is required. Use team --help')
    if action not in PROJECT_ACTIONS+GLOBAL_ACTIONS:
        raise ValueError('Invalid command: '+action+'. Use team --help for supported commands')
    if action in ['--help','-h','help']:
        if len(sys.argv)!=2:raise ValueError('Use team --help without additional arguments')
        print(HELP,end='');return
    if sys.argv[1:2] in [['--list'],['list-projects']]:
        if len(sys.argv)!=2:raise ValueError('Use team --list or team list-projects without a project name')
        list_projects();return
    os.umask(0o077)
    if sys.argv[1:]==['version']:
        print((INSTALL/'build-info.json').read_text().strip());return
    if len(sys.argv)>1 and sys.argv[1]=='setup':
        if sys.argv[2:] not in [[],['--list']]:raise ValueError('Use team setup or team setup --list')
        settings().setup(ACCOUNT_HOME,listing=sys.argv[2:]==['--list']);return
    if sys.argv[1:2]==['diagnostics']:
        if len(sys.argv)!=4 or sys.argv[2]!='--export':raise ValueError('Use team diagnostics --export PATH')
        diagnostics().export(ACCOUNT_HOME,sys.argv[3]);return
    if action=='rename-project':
        if len(sys.argv)!=4:raise ValueError('Use team rename-project OLD NEW')
        spec=importlib.util.spec_from_file_location('project_rename',INSTALL/'routing/project-rename.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.rename_project(sys.modules[__name__],sys.argv[2],sys.argv[3]);return
    p=argparse.ArgumentParser();p.add_argument('action',choices=PROJECT_ACTIONS);p.add_argument('project');p.add_argument('role',nargs='?',choices=ROLES);a=p.parse_args()
    if a.action in ['destroy','archive','unarchive'] and a.role:p.error(a.action+' takes exactly NAME')
    if a.action=='create-project':create(a.project);return
    if a.action=='unarchive':unarchive(a.project);return
    verify_project(a.project)
    if a.action in ['start','restart']:
        required_auth(a.project);control(a.action,a.project)
    elif a.action=='stop':control('stop',a.project)
    elif a.action in ['destroy','archive']:retire_project(a.project,archive=a.action=='archive')
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
    action=sys.argv[1] if len(sys.argv)>1 else None
    try:
        main()
        if action in PROJECT_ACTIONS+['setup'] and action in diagnostics().ACTIONS:diagnostics().record(ACCOUNT_HOME,action,'completed',0)
    except (ValueError,subprocess.CalledProcessError,OSError) as error:
        try:
            if action in PROJECT_ACTIONS+['setup'] and action in diagnostics().ACTIONS:
                outcome='archive_collision' if isinstance(error,ArchiveCollisionError) else 'failed'
                diagnostics().record(ACCOUNT_HOME,action,outcome,1)
        except (OSError,ValueError):pass
        print('Project operation failed: '+str(error),file=sys.stderr);sys.exit(1)
