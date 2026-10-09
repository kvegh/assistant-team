#!/usr/bin/env python3
"""Run a real home-local native CLI with all mutable paths scoped to its directory."""
import fcntl,importlib.util,json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
os.umask(0o077)
config=json.loads((root/'.native-install.json').read_text())
prefix=root/'.install'
env=os.environ.copy()
env.update(HOME=str(root),XDG_CONFIG_HOME=str(root/'.config'),XDG_CACHE_HOME=str(root/'.cache'),XDG_DATA_HOME=str(root/'.local/share'),XDG_STATE_HOME=str(root/'.local/state'),TMPDIR=str(root/'tmp'),CLAUDE_CONFIG_DIR=str(root/'.claude'),CODEX_HOME=str(root/'.codex'),VIBE_HOME=str(root/'.vibe'),GEMINI_CLI_HOME=str(root),PATH=str(prefix/'bin')+os.pathsep+env.get('PATH',''),DISABLE_AUTOUPDATER='1',CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
f=config['flavour']
if config.get('provider')=='antigravity':
    env['AGY_CLI_DISABLE_AUTO_UPDATE']='true'
    command=[str(prefix/config['entrypoint'])]
elif f=='claude':command=[str(prefix/config['entrypoint'])]
elif f in ['codex','gemini']:command=[str(prefix/'bin/node'),str(prefix/config['entrypoint'])]
else:
    env['VIBE_TEST_DISABLE_KEYRING']='1'
    env['PYTHONHOME']=str(prefix)
    env['LD_LIBRARY_PATH']=str(prefix/'lib')+os.pathsep+env.get('LD_LIBRARY_PATH','')
    command=[str(prefix/'bin/python3.12'),str(prefix/config['entrypoint'])]
if f=='codex':command += ['-c','check_for_update_on_startup=false']
args=sys.argv[1:]
status_spec=importlib.util.spec_from_file_location('login_result',root/'.login-result.py')
status=importlib.util.module_from_spec(status_spec);status_spec.loader.exec_module(status)
if pathlib.Path(sys.argv[0]).name=='login':
    (root/'tmp').mkdir(mode=0o700,exist_ok=True)
    lock=(root/'tmp/login.lock').open('a')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status.require_idle(root)
    except (BlockingIOError,ValueError) as error:raise SystemExit(status.display(str(error)))
def diagnostic(action,result,code=0):
    path=root.parent/'agents-connector/routing/environment-diagnostics.py'
    if not path.is_file():return
    spec=importlib.util.spec_from_file_location('environment_diagnostics',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    try:module.record(root.parent,action,result,code)
    except (ValueError,OSError):pass
if config.get('provider')=='antigravity':
    env=status.personal_antigravity(env)
elif f=='gemini' and config.get('provider')!='vertex':
    env=status.personal_gemini(root,env)
vertex=None
if f in ['claude','gemini'] and config.get('provider')=='vertex' and sys.argv[1:] not in [['--version'],['--help'],['--clear']]:
    spec=importlib.util.spec_from_file_location('vertex_runtime',root/'.vertex-runtime.py')
    vertex=importlib.util.module_from_spec(spec);spec.loader.exec_module(vertex)
if pathlib.Path(sys.argv[0]).name=='login':
    if args==['--clear']:
        try:copies=status.clear_profile(root,f,config.get('provider'))
        except (ValueError,OSError) as error:raise SystemExit(status.display(str(error)))
        print(status.display('Saved authentication cleared for this profile and '+str(copies)+' matching role contexts. Remote revocation and model access were not tested.'),flush=True)
        diagnostic('clear','completed')
        raise SystemExit(0)
    if args:raise SystemExit(status.display('./login takes no arguments'))
    before=status.credential_snapshot(root,f,config.get('provider'))
    if vertex is not None:
        os.umask(0o077);os.chdir(root)
        try:vertex.login(env);code=0
        except (ValueError,subprocess.CalledProcessError,KeyboardInterrupt) as error:
            code=130 if isinstance(error,KeyboardInterrupt) else 1
            print(status.display('Vertex login did not complete; configuration or SDK prerequisites may need attention.'),flush=True)
        message=status.result(code,before,status.credential_snapshot(root,f,config.get('provider')))
        print(status.display(message),flush=True)
        print(status.display(status.follow_up(f,config.get('provider'),message!='Failed or cancelled')),flush=True)
        diagnostic('login','completed' if code==0 else 'failed',code)
        raise SystemExit(code)
    args={'claude':['auth','login'],'codex':['-c','cli_auth_credentials_store="file"','login','--device-auth'],'gemini':[],'vibe':['--setup']}[f]
    if f=='vibe':
        env=status.vibe_browser_handoff(root,env)
        print(status.display('Open the native displayed sign-in link in your browser manually. Vibe will keep polling for that authorization; no GUI browser is launched here.'),flush=True)
    if config.get('provider')=='antigravity':
        env['NO_BROWSER']='true'
        print(status.display('Choose personal Google sign-in in Antigravity. Complete its displayed browser/code flow yourself; never send authorization codes here. Exit the CLI after signing in to see the saved-auth result.'),flush=True)
    elif f=='gemini':
        env['NO_BROWSER']='true'
        print(status.display('Choose Sign in with Google; use the displayed browser link and verification flow.'),flush=True)
    os.umask(0o077);os.chdir(root)
    try:code=subprocess.call(command+args,env=env)
    except KeyboardInterrupt:code=130
    except OSError:code=1
    after=status.credential_snapshot(root,f,config.get('provider'))
    message=status.result(code,before,after,interactive=f in ['gemini','vibe'])
    print('\n'+status.display(message),flush=True)
    print(status.display(status.follow_up(f,config.get('provider'),message!='Failed or cancelled',existing_saved=bool(after and before==after))),flush=True)
    if message!='Failed or cancelled' and code in [130,-2]:
        print(status.display('Native CLI interrupted after saving new credentials; model access remains unverified.'),flush=True)
    diagnostic('login','credentials_saved' if message!='Failed or cancelled' else 'credentials_unconfirmed',code)
    if message=='Failed or cancelled' and code==0:
        print(status.display('No new completed login was confirmed; existing saved credentials, if any, were preserved.'),flush=True)
        code=1
    raise SystemExit(0 if message!='Failed or cancelled' else code if code>=0 else 128-code)
if vertex is not None and args not in [['--version'],['--help']]:
    try:env=vertex.environment(env)
    except ValueError as error:raise SystemExit(status.display(str(error)))
os.umask(0o077)
os.chdir(root)
os.execve(command[0],command+args,env)
