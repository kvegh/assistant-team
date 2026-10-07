#!/usr/bin/env python3
"""Operator-owned lifecycle and narrowly scoped stock connector IPC adapters."""
import argparse, asyncio, json, os, pathlib, re, socket, sqlite3, shlex, struct, subprocess, sys, time
INSTALL_ROOT = pathlib.Path(__file__).resolve().parents[1]
ACCOUNT_HOME = INSTALL_ROOT.parent
PROJECT = os.environ.get('ASSISTANT_PROJECT')
if PROJECT and not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,39}', PROJECT):
    raise ValueError('Invalid project name')
ROOT = ACCOUNT_HOME / 'projects' / PROJECT if PROJECT else INSTALL_ROOT
BIN = INSTALL_ROOT / 'bin/agents-connector'
SESSION = PROJECT or 'workers'
STATE = ROOT if PROJECT else ROOT / 'state'
ADMIN = STATE / 'broker.sock'
PROFILES = ROOT / 'profiles'
VISIBLE = ['orchestrator', 'builder', 'investigator', 'challenger', 'summarizer']
ALL = VISIBLE + ['observer','private-connector','corporate-connector']
VERSIONS = {'claude':'2.1.292', 'codex':'0.160.1', 'gemini':'0.63.0'}

def frame(s, obj):
    raw=json.dumps(obj).encode();s.sendall(struct.pack('!I',len(raw))+raw)
    def read(n):
        b=b''
        while len(b)<n:
            chunk=s.recv(n-len(b))
            if not chunk: raise EOFError()
            b+=chunk
        return b
    n=struct.unpack('!I',read(4))[0]
    if n>1048576: raise ValueError('oversized response')
    return json.loads(read(n))

def rpc(obj):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(65);s.connect(str(ADMIN));return frame(s,obj)

def run(args, **kw):
    return subprocess.run([str(a) for a in args],check=True,**kw)

def container(name):
    if name not in ALL: raise ValueError('unknown role profile')
    return ('acp-'+PROJECT+'-' if PROJECT else 'ac-')+name

def token(name): return (PROFILES/name/'token').read_text().strip()

def initialize():
    STATE.mkdir(mode=0o700,exist_ok=True)
    for _ in range(100):
        try: rpc({'kind':'list_agents'});break
        except (OSError,EOFError): time.sleep(0.05)
    else: raise RuntimeError('broker did not become ready')
    for name in VISIBLE:
        p=PROFILES/name
        spec=json.loads((p/'profile.json').read_text())
        response=rpc({'kind':'get_agent','name':name})
        if response['kind']=='error':
            response=rpc({'kind':'register_agent','name':name,'cli_kind':spec['flavour'],'workdir':None,'extra_args':[]})
            t=response['agent_token']
        else:t=response['token']
        (p/'token').write_text(t);(p/'token').chmod(0o600)
        args=['/opt/connector/bin/agents-connector','mcp-shim','--socket','/ipc/agent.sock','--agent-token',t]
        server={'command':args[0],'args':args[1:]}
        def hook(event,kind):return ' '.join(['/opt/connector/bin/agents-connector','hook','--socket','/ipc/agent.sock','--agent-token',t,'--event',event,'--cli-kind',kind])
        flavour=spec['flavour']
        if flavour=='claude':
            (p/'home/mcp.json').write_text(json.dumps({'mcpServers':{'agents_connector':server}}))
            events={'SessionStart':'session_start','UserPromptSubmit':'user_prompt_submit','PostToolUse':'post_tool_use','Stop':'stop'}
            cfg={'hooks':{e:[{'matcher':'','hooks':[{'type':'command','command':hook(k,'claude')}]}] for e,k in events.items()}}
            (p/'home/settings.json').write_text(json.dumps(cfg))
        elif flavour=='gemini':
            d=p/'home/.gemini';d.mkdir(exist_ok=True)
            events={'BeforeAgent':'before_agent','AfterTool':'after_tool','AfterAgent':'after_agent'}
            cfg={'mcpServers':{'agents_connector':server},'hooks':{e:[{'matcher':'*','hooks':[{'type':'command','name':'connector-'+k,'command':hook(k,'gemini')}]}] for e,k in events.items()}}
            settings=d/'settings.json'
            previous=json.loads(settings.read_text()) if settings.exists() else {}
            previous.update(cfg);settings.write_text(json.dumps(previous))
        else:
            d=p/'home/.codex';d.mkdir(exist_ok=True)
            config='[features]\nhooks = true\n[mcp_servers.agents_connector]\ncommand = '+json.dumps(args[0])+'\nargs = '+json.dumps(args[1:])+'\n'
            for event,k in {'UserPromptSubmit':'user_prompt_submit','PostToolUse':'post_tool_use','Stop':'stop'}.items():
                config+='[[hooks.'+event+']]\n[[hooks.'+event+'.hooks]]\ntype = "command"\ncommand = '+json.dumps(hook(k,'codex'))+'\n'
            if not (d/'config.toml').exists():(d/'config.toml').write_text(config)
    print('Visible profiles registered; native configs generated without provider credentials.')

async def receive(reader):
    n=struct.unpack('!I',await reader.readexactly(4))[0]
    if n>1048576:raise ValueError('oversized frame')
    return json.loads(await reader.readexactly(n))

async def send(writer,obj):
    raw=json.dumps(obj).encode();writer.write(struct.pack('!I',len(raw))+raw);await writer.drain()

def authorize(name,obj):
    if not isinstance(obj,dict):return False
    kind=obj.get('kind');t=token(name)
    if kind=='authenticate':return obj.get('agent_token')==t
    if kind=='set_agent_state':return obj.get('agent_token')==t and obj.get('state') in ['idle','busy']
    if kind in ['check_replies','wait_for_reply','post_reply']:
        with sqlite3.connect('file:'+str(STATE/'db.sqlite')+'?mode=ro',uri=True) as db:
            ask=db.execute('select from_agent,to_agent from asks where id=?',(obj.get('ask_id'),)).fetchone()
        if not ask or name != ask[1 if kind=='post_reply' else 0]:return False
    if kind in ['tell','ask','post_reply']:
        if obj.get('from')!=name:return False
        if kind!='post_reply' and obj.get('to') not in VISIBLE+[None]:return False
        return isinstance(obj.get('text'),str) and len(obj['text'])<=65536
    if kind=='read_messages':return obj.get('agent')==name
    return kind in ['list_agents','check_replies','wait_for_reply']

async def gateway():
    async def client(name,reader,writer):
        authenticated=False
        try:
            while True:
                obj=await receive(reader)
                permitted=authorize(name,obj) and (authenticated or obj.get('kind') in ['authenticate','set_agent_state'])
                if not permitted:
                    await send(writer,{'kind':'error','message':'Instance IPC policy denied request'});continue
                if obj['kind']=='wait_for_reply':obj['timeout_ms']=min(max(int(obj.get('timeout_ms',0)),0),60000)
                response=await asyncio.to_thread(rpc,obj)
                if obj['kind']=='authenticate' and response.get('kind')=='agent_info':authenticated=True
                await send(writer,response)
        except (EOFError,asyncio.IncompleteReadError,ConnectionError,ValueError,KeyError):pass
        finally:writer.close();await writer.wait_closed()
    servers=[]
    for name in VISIBLE:
        d=PROFILES/name/'ipc';d.mkdir(mode=0o700,exist_ok=True);path=d/'agent.sock'
        if path.exists():path.unlink()
        servers.append(await asyncio.start_unix_server(lambda r,w,n=name:client(n,r,w),path=str(path)))
        path.chmod(0o600)
    await asyncio.gather(*(s.serve_forever() for s in servers))

def start_container(name):
    p=PROFILES/name;spec=json.loads((p/'profile.json').read_text());c=container(name)
    exists=subprocess.run(['podman','container','exists',c]).returncode==0
    if name=='observer':
        refresh_observer()
        if exists:
            mounts=json.loads(subprocess.check_output(['podman','inspect',c],text=True))[0]['Mounts']
            if not any(m['Destination']=='/context' and not m['RW'] for m in mounts):
                if (p/'launched').exists():raise ValueError('Observer must be stopped before adding its read-only context mount')
                current=subprocess.check_output(['podman','exec',c,'tmux','display-message','-p','-t','native:agent','#{pane_current_command}'],text=True).strip()
                if current not in ['bash','sh']:raise ValueError('Observer has active work; refusing container replacement')
                run(['podman','rm','--force',c],stdout=subprocess.DEVNULL);exists=False
    if exists:
        run(['podman','start',c],stdout=subprocess.DEVNULL)
        if subprocess.run(['podman','exec',c,'tmux','has-session','-t','native'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
            run(['podman','exec',c,'tmux','new-session','-d','-s','native','-n','agent'])
        return
    uid=os.getuid()
    cmd=['podman','run','-d','--name',c,'--userns=keep-id:uid=1000,gid=1000','--user','1000:1000','--read-only','--cap-drop=all','--security-opt=no-new-privileges','--memory=768m','--cpus=1','--pids-limit=256','--network=slirp4netns:allow_host_loopback=false','--tmpfs','/tmp:rw,nosuid,nodev,size=128m','--tmpfs','/run:rw,nosuid,nodev,size=16m','-e','HOME=/home/agent','-e','TERM=xterm-256color','-w','/workspace','-v',str(p/'home')+':/home/agent:Z','-v',str(p/'workspace')+':/workspace:Z','-v',str(p/'ipc')+':/ipc:Z','-v',str(INSTALL_ROOT/'bin')+':/opt/connector/bin:ro,z','localhost/assistant-connector-'+spec['flavour']+':'+VERSIONS[spec['flavour']],'/bin/sh','-c','tmux new-session -d -s native -n agent; exec sleep infinity']
    if name=='observer':
        image=cmd.index('localhost/assistant-connector-'+spec['flavour']+':'+VERSIONS[spec['flavour']])
        cmd[image:image]=['-v',str(p/'context')+':/context:ro,Z']
    run(cmd,stdout=subprocess.DEVNULL)


def seed_auth(name):
    profile=PROFILES/name
    cfg=json.loads((profile/'profile.json').read_text())
    flavour=cfg['flavour']
    source_name=cfg.get('auth_directory',{'claude':'claude-work','codex':'codex','gemini':'gemini'}[flavour])
    if source_name not in {'claude':['claude-work','claude-priv'],'codex':['codex'],'gemini':['gemini']}[flavour]:raise ValueError('unsupported provider auth boundary')
    source=(ACCOUNT_HOME if PROJECT else ROOT.parent)/source_name
    files={'claude':['.claude/.credentials.json'],'codex':['.codex/auth.json'],'gemini':['.gemini/oauth_creds.json','.gemini/google_accounts.json']}[flavour]
    seeded=False
    for relative in files:
        src=source/relative;dst=profile/'home'/relative
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            dst.write_bytes(src.read_bytes());dst.chmod(0o600);seeded=True
    metadata_path=next((p for p in [source/'.claude/.claude.json',source/'.claude.json'] if p.is_file()),None)
    if flavour=='claude' and seeded and metadata_path is not None:
        metadata=json.loads(metadata_path.read_text())
        config=profile/'home/.claude.json'
        current=json.loads(config.read_text()) if config.exists() else {}
        if 'oauthAccount' in metadata:current['oauthAccount']=metadata['oauthAccount']
        config.write_text(json.dumps(current));config.chmod(0o600)
    if flavour=='gemini' and (source/'.gemini/oauth_creds.json').is_file():
        config=profile/'home/.gemini/settings.json'
        current=json.loads(config.read_text())
        current.setdefault('security',{}).setdefault('auth',{})['selectedType']='oauth-personal'
        config.write_text(json.dumps(current));config.chmod(0o600)

def launch(name):
    if (PROFILES/name/'launched').exists():
        dead=subprocess.check_output(['podman','exec',container(name),'tmux','display-message','-p','-t','native:agent','#{pane_dead}'],text=True).strip()
        if dead!='1':raise ValueError('session already launched; attach instead')
        (PROFILES/name/'launched').unlink()
    seed_auth(name)
    start_container(name);spec=json.loads((PROFILES/name/'profile.json').read_text());flavour=spec['flavour']
    apply_prompts()
    cmd={'claude':['claude','--mcp-config','/home/agent/mcp.json','--settings','/home/agent/settings.json'],'codex':['codex','--sandbox','read-only','--ask-for-approval','on-request'],'gemini':['gemini']}[flavour]
    if name=='observer':refresh_observer();cmd=['claude','--tools','Read,Grep,Glob,Write']
    elif name in ['private-connector','corporate-connector']:cmd=['claude','--tools','']
    run(['podman','exec',container(name),'tmux','set-option','-g','remain-on-exit','on'])
    # Operator launch is explicit; never supply a work prompt or bypass approval.
    run(['podman','exec',container(name),'tmux','respawn-pane','-k','-t','native:agent',shlex.join(cmd)])

def wake(args):
    # Only upstream literal fixed notices and Enter are accepted; discard sender text.
    if len(args)!=5 or args[:2]!=['send-keys','-l'] or args[2]!='-t':
        if len(args)==4 and args[:2]==['send-keys','-t'] and args[-1]=='Enter':
            target=args[2];payload='Enter'
        else:raise ValueError('unsupported tmux routing action')
    else:
        target=args[3]
        if not re.fullmatch(r'\[agents-connector\] new (message|question) from [A-Za-z0-9_-]+ — see additionalContext for content',args[4]):raise ValueError('non-notification rejected')
        payload='[agents-connector] New addressed event; read your authenticated inbox.'
    session,name=target.split(':',1)
    if session!=SESSION:raise ValueError('wrong session')
    spec=json.loads((PROFILES/name/'profile.json').read_text())
    if not (PROFILES/name/'launched').exists():return
    run(['podman','exec',container(name),'tmux','send-keys']+(['-l'] if payload!='Enter' else [])+['-t','native:agent',payload],stdout=subprocess.DEVNULL)


def apply_prompts():
    source=ROOT/'assistant-prompt.md' if PROJECT else ROOT.parent/'assistant-prompts.md'
    content=source.read_text()
    goal=content.split('# Role:',1)[0].strip() if PROJECT else ''
    headers=list(re.finditer(r'^# Role: ([a-z-]+)\s*$',content,re.M))
    names=[h.group(1) for h in headers]
    if len(names)!=len(set(names)) or set(names)!=set(ALL):raise ValueError('Prompt file must contain exactly one # Role: section per role')
    roster='\n\nCollaboration roles: orchestrator routes and bounds work; builder implements; investigator diagnoses; challenger reviews assumptions; summarizer condenses decisions. Read addressed MCP messages. Distinguish proposals from verified results. Stop completed discussions; pause exhausted subscription work without paid API fallback.\n'
    for i,header in enumerate(headers):
        role=header.group(1);cfg=json.loads((PROFILES/role/'profile.json').read_text())
        prompt=content[header.end():headers[i+1].start() if i+1<len(headers) else len(content)].strip()+'\n'
        if PROJECT:prompt='# Project: '+PROJECT+'\n\n'+goal+'\n\n'+prompt
        if role in VISIBLE:prompt+=roster
        file=PROFILES/role/'workspace'/ {'claude':'CLAUDE.md','codex':'AGENTS.md','gemini':'GEMINI.md'}[cfg['flavour']]
        temp=file.with_suffix('.pending');temp.write_text(prompt);temp.chmod(0o600);temp.replace(file)

def refresh_observer():
    with sqlite3.connect('file:'+str(STATE/'db.sqlite')+'?mode=ro',uri=True) as db:
        rows=db.execute('select id,from_agent,to_agent,text from messages order by id').fetchall()
    text='# Permitted worker discussion snapshot\n\n'+''.join(f'## Message {i}: {sender} to {recipient or "workers"}\n\n{body}\n\n' for i,sender,recipient,body in rows)
    directory=PROFILES/'observer/context';directory.mkdir(mode=0o700,exist_ok=True)
    file=directory/'discussion.md';file.write_text(text);file.chmod(0o600)
    print('Observer snapshot updated; no SQLite database or private connector context mounted.')

def deliver_observer_report():
    source=PROFILES/'observer/workspace/report.md'
    if not source.is_file():raise ValueError('Observer report.md is not available yet')
    target=PROFILES/'orchestrator/workspace/private-review.md'
    target.write_bytes(source.read_bytes());target.chmod(0o600)
    print('Private review delivered only to orchestrator workspace; no worker-broker message sent.')

def watch():
    with socket.socket(socket.AF_UNIX) as sock:
        sock.connect(str(ADMIN))
        # Stock broker streaming subscription, not SQLite or inbox polling.
        raw=json.dumps({'kind':'subscribe_stream'}).encode();sock.sendall(struct.pack('!I',len(raw))+raw)
        def exact(n):
            data=b''
            while len(data)<n:
                chunk=sock.recv(n-len(data))
                if not chunk:raise EOFError('Broker stream ended')
                data+=chunk
            return data
        print('Live worker discussion. Ctrl-C closes this viewer.',flush=True)
        while True:
            size=struct.unpack('!I',exact(4))[0]
            if size>1048576:raise ValueError('Oversized stream event')
            event=json.loads(exact(size))
            if event.get('kind')=='stream_event':
                msg=event['message'];body=''.join(ch if ch in '\n\t' or ord(ch)>=32 and ord(ch)!=127 else '?' for ch in msg['text']);print(f"[{msg['id']}] {msg['from']} -> {msg.get('to') or 'workers'}: {body}",flush=True)

def main():
    if not PROJECT and len(sys.argv)>1 and (sys.argv[1] in ['create-project','start','restart','status'] or len(sys.argv)>2 and sys.argv[1] in ['stop','watch','apply-prompts','refresh-observer','deliver-observer-report'] or len(sys.argv)>3 and sys.argv[1] in ['attach','launch']):
        os.execv(sys.executable,[sys.executable,str(INSTALL_ROOT/'routing/project-team.py'),*sys.argv[1:]])
    if pathlib.Path(sys.argv[0]).name=='tmux':wake(sys.argv[1:]);return
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['init','gateway','prepare','stop','launch','attach','login','help','check','watch','apply-prompts','refresh-observer','deliver-observer-report']);parser.add_argument('name',nargs='?',choices=ALL)
    a=parser.parse_args()
    if a.action=='init':initialize()
    elif a.action=='gateway':asyncio.run(gateway())
    elif a.action=='prepare':
        for n in ALL:start_container(n)
    elif a.action=='stop':
        existing=[container(n) for n in ALL if subprocess.run(['podman','container','exists',container(n)]).returncode==0]
        if existing:run(['podman','stop','--time','10',*existing],stdout=subprocess.DEVNULL)
        for n in ALL:(PROFILES/n/'launched').unlink(missing_ok=True)
    elif a.action in ['launch','attach','login','help']:
        if not a.name:parser.error('name required')
        start_container(a.name);f=json.loads((PROFILES/a.name/'profile.json').read_text())['flavour']
        if a.action=='launch':launch(a.name);(PROFILES/a.name/'launched').touch()
        elif a.action=='attach':run(['podman','exec','-it',container(a.name),'tmux','attach-session','-t','native'])
        elif a.action=='help':run(['podman','exec',container(a.name),f,'--help'])
        else:
            cmd={'claude':['claude','auth','login'],'codex':['codex','login','--device-auth'],'gemini':['gemini']}[f]
            run(['podman','exec','-it',container(a.name)]+cmd)
    elif a.action=='watch':watch()
    elif a.action=='apply-prompts':apply_prompts();print('Role instructions updated; active sessions use them on next launch.')
    elif a.action=='refresh-observer':refresh_observer()
    elif a.action=='deliver-observer-report':deliver_observer_report()
    elif a.action=='check':print(json.dumps(rpc({'kind':'list_agents'})))

if __name__=='__main__':main()
