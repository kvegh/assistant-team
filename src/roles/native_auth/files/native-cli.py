#!/usr/bin/env python3
"""Run a real home-local native CLI with all mutable paths scoped to its directory."""
import json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
config=json.loads((root/'.native-install.json').read_text())
prefix=root/'.install'
env=os.environ.copy()
env.update(HOME=str(root),XDG_CONFIG_HOME=str(root/'.config'),XDG_CACHE_HOME=str(root/'.cache'),XDG_DATA_HOME=str(root/'.local/share'),XDG_STATE_HOME=str(root/'.local/state'),TMPDIR=str(root/'tmp'),CLAUDE_CONFIG_DIR=str(root/'.claude'),CODEX_HOME=str(root/'.codex'),VIBE_HOME=str(root/'.vibe'),GEMINI_CLI_HOME=str(root),PATH=str(prefix/'bin')+os.pathsep+env.get('PATH',''),DISABLE_AUTOUPDATER='1',CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
f=config['flavour']
if f=='claude':command=[str(prefix/config['entrypoint'])]
elif f in ['codex','gemini']:command=[str(prefix/'bin/node'),str(prefix/config['entrypoint'])]
else:
    env['PYTHONHOME']=str(prefix)
    env['LD_LIBRARY_PATH']=str(prefix/'lib')+os.pathsep+env.get('LD_LIBRARY_PATH','')
    command=[str(prefix/'bin/python3.12'),str(prefix/config['entrypoint'])]
args=sys.argv[1:]
if pathlib.Path(sys.argv[0]).name=='login':
    if args:raise SystemExit('./login takes no arguments')
    args={'claude':['auth','login'],'codex':['-c','cli_auth_credentials_store="file"','login','--device-auth'],'gemini':[],'vibe':['--setup']}[f]
    if f=='gemini':
        env['NO_BROWSER']='true'
        print('Choose Sign in with Google; use the displayed browser link and verification flow.',flush=True)
os.umask(0o077)
os.chdir(root)
os.execve(command[0],command+args,env)
