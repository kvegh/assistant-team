#!/usr/bin/env python3
"""Operator-owned lifecycle and narrowly scoped stock connector IPC adapters."""
import argparse, asyncio, ctypes, ctypes.util, importlib.util, json, os, pathlib, re, socket, sqlite3, shlex, struct, subprocess, sys, time
INSTALL_ROOT = pathlib.Path(__file__).resolve().parents[1]
ACCOUNT_HOME = INSTALL_ROOT.parent

def project_name_validator():
    source=pathlib.Path(__file__).resolve().with_name('project-names.py')
    if not source.exists():source=pathlib.Path(__file__).resolve().parents[3]/'lib/project-names.py'
    spec=importlib.util.spec_from_file_location('project_names',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.validate

PROJECT = os.environ.get('ASSISTANT_PROJECT')
if PROJECT:project_name_validator()(PROJECT)
ROOT = ACCOUNT_HOME / 'projects' / PROJECT if PROJECT else INSTALL_ROOT
BIN = INSTALL_ROOT / 'bin/agents-connector'
SESSION = PROJECT or 'workers'
STATE = ROOT if PROJECT else ROOT / 'state'
ADMIN = STATE / 'broker.sock'
PROFILES = ROOT / 'profiles'
VISIBLE = ['orchestrator', 'builder', 'investigator', 'challenger', 'summarizer']
ALL = VISIBLE + ['observer','private-connector','corporate-connector']
VERSIONS = {'claude':'2.1.292', 'codex':'0.160.1', 'gemini':'0.63.0'}

def role_directory(name, kind):
    base=PROFILES/name
    cfg=json.loads((base/'profile.json').read_text())
    account=cfg.get('account_profile')
    return base/'accounts'/account/kind if account else base/kind

def role_home(name):return role_directory(name,'home')
def role_workspace(name):return role_directory(name,'workspace')

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
            (role_home(name)/'mcp.json').write_text(json.dumps({'mcpServers':{'agents_connector':server}}))
            events={'SessionStart':'session_start','UserPromptSubmit':'user_prompt_submit','PostToolUse':'post_tool_use','Stop':'stop'}
            cfg={'hooks':{e:[{'matcher':'','hooks':[{'type':'command','command':hook(k,'claude')}]}] for e,k in events.items()}}
            (role_home(name)/'settings.json').write_text(json.dumps(cfg))
        elif flavour=='gemini':
            d=role_home(name)/'.gemini';d.mkdir(exist_ok=True)
            events={'BeforeAgent':'before_agent','AfterTool':'after_tool','AfterAgent':'after_agent'}
            cfg={'mcpServers':{'agents_connector':server},'hooks':{e:[{'matcher':'*','hooks':[{'type':'command','name':'connector-'+k,'command':hook(k,'gemini')}]}] for e,k in events.items()}}
            settings=d/'settings.json'
            previous=json.loads(settings.read_text()) if settings.exists() else {}
            previous.update(cfg);settings.write_text(json.dumps(previous))
        else:
            d=role_home(name)/'.codex';d.mkdir(exist_ok=True)
            config='check_for_update_on_startup = false\n[features]\nhooks = true\n[mcp_servers.agents_connector]\ncommand = '+json.dumps(args[0])+'\nargs = '+json.dumps(args[1:])+'\n'
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

def gateway_socket():
    """Label only the listener's kernel socket SID; retain its mount's MCS label."""
    library = ctypes.util.find_library('selinux')
    if not library:
        if pathlib.Path('/sys/fs/selinux/enforce').exists():
            raise RuntimeError('SELinux listener labeling requires the system libselinux library')
        return socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    selinux = ctypes.CDLL(library, use_errno=True)
    enabled = selinux.is_selinux_enabled()
    if enabled == 0:
        return socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    if enabled < 0:
        raise RuntimeError('Could not determine SELinux listener labeling state')
    selinux.getsockcreatecon.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    selinux.setsockcreatecon.argtypes = [ctypes.c_char_p]
    selinux.freecon.argtypes = [ctypes.c_void_p]
    previous = ctypes.c_void_p()
    if selinux.getsockcreatecon(ctypes.byref(previous)) != 0:
        raise RuntimeError('Could not read the previous SELinux socket creation context')
    try:
        previous_context = ctypes.string_at(previous) if previous.value else None
    finally:
        if previous.value:
            selinux.freecon(previous)
    if selinux.setsockcreatecon(b'system_u:system_r:container_t:s0') != 0:
        raise RuntimeError('Could not assign the SELinux container listener socket context')
    listener = None
    try:
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    finally:
        # This setting is thread-local. Restore before any await or RPC work.
        if selinux.setsockcreatecon(previous_context) != 0:
            if listener is not None:
                listener.close()
            raise RuntimeError('Could not restore the SELinux socket creation context')
    return listener

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
        listener = gateway_socket()
        try:
            listener.bind(str(path))
            path.chmod(0o600)
            listener.listen(socket.SOMAXCONN)
            listener.setblocking(False)
            servers.append(await asyncio.start_unix_server(lambda r,w,n=name:client(n,r,w),sock=listener))
        except BaseException:
            listener.close()
            raise
    await asyncio.gather(*(s.serve_forever() for s in servers))

def wait_for_native_session(c, restore=False, timeout=15):
    """Wait for the detached entrypoint; never start a model to probe readiness."""
    deadline=time.monotonic()+timeout
    while True:
        if subprocess.run(['podman','exec',c,'tmux','has-session','-t','native'],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
            return
        running=subprocess.run(['podman','inspect','--format','{{.State.Running}}',c],
                               capture_output=True,text=True)
        if running.returncode or running.stdout.strip()!='true':
            raise ValueError('Container stopped before its native tmux session was ready: '+c)
        # Existing idle containers may have lost their session. Restore only after
        # PID 1 has finished initialization, so we cannot race its tmux creation.
        if restore:
            process=subprocess.run(['podman','exec',c,'cat','/proc/1/comm'],
                                   capture_output=True,text=True)
            if process.returncode==0 and process.stdout.strip()=='sleep':
                run(['podman','exec',c,'tmux','new-session','-d','-s','native','-n','agent'],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                restore=False
                continue
        if time.monotonic()>=deadline:
            raise ValueError('Native tmux session did not become ready within '+str(timeout)+' seconds: '+c)
        time.sleep(0.2)

def start_container(name):
    p=PROFILES/name;spec=json.loads((p/'profile.json').read_text());c=container(name)
    exists=subprocess.run(['podman','container','exists',c]).returncode==0
    if PROJECT:
        shared=ROOT/'workspace'
        if shared.is_symlink():raise ValueError('Shared project workspace must not be a symlink')
        shared.mkdir(mode=0o700,exist_ok=True)
        if exists:
            inspected=json.loads(subprocess.check_output(['podman','inspect',c],text=True))[0]
            mount=next((m for m in inspected['Mounts'] if m['Destination']=='/workspace/shared'),None)
            desired_rw=name!='observer'
            correct=mount and mount['Source']==str(shared) and mount['RW']==desired_rw
            homes=next((m for m in inspected['Mounts'] if m['Destination']=='/home/agent'),None)
            correct=correct and homes and homes['Source']==str(role_home(name))
            if not correct:
                if inspected['State']['Running']:
                    raise ValueError('Shared workspace mount pending: stop project '+PROJECT+' and start it again; active container was preserved')
                run(['podman','rm',c],stdout=subprocess.DEVNULL);exists=False
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
        wait_for_native_session(c,restore=True)
        return
    uid=os.getuid()
    cmd=['podman','run','-d','--name',c,'--userns=keep-id:uid=1000,gid=1000','--user','1000:1000','--read-only','--cap-drop=all','--security-opt=no-new-privileges','--memory=768m','--cpus=1','--pids-limit=256','--network=slirp4netns:allow_host_loopback=false','--tmpfs','/tmp:rw,nosuid,nodev,size=128m','--tmpfs','/run:rw,nosuid,nodev,size=16m','-e','HOME=/home/agent','-e','TERM=xterm-256color','-w','/workspace','-v',str(role_home(name))+':/home/agent:Z','-v',str(role_workspace(name))+':/workspace:Z','-v',str(p/'ipc')+':/ipc:Z','-v',str(INSTALL_ROOT/'bin')+':/opt/connector/bin:ro,z','localhost/assistant-connector-'+spec['flavour']+':'+VERSIONS[spec['flavour']],'/bin/sh','-c','tmux new-session -d -s native -n agent && exec sleep infinity']
    if PROJECT:
        image=cmd.index('localhost/assistant-connector-'+spec['flavour']+':'+VERSIONS[spec['flavour']])
        cmd[image:image]=['-v',str(ROOT/'workspace')+':/workspace/shared:'+('ro,z' if name=='observer' else 'rw,z')]
    if name=='observer':
        image=cmd.index('localhost/assistant-connector-'+spec['flavour']+':'+VERSIONS[spec['flavour']])
        cmd[image:image]=['-v',str(p/'context')+':/context:ro,Z']
    run(cmd,stdout=subprocess.DEVNULL)
    wait_for_native_session(c)


def seed_auth(name):
    profile=PROFILES/name
    cfg=json.loads((profile/'profile.json').read_text())
    flavour=cfg['flavour']
    source_name=cfg.get('auth_directory',{'claude':'claude-work','codex':'codex-priv','gemini':'gemini-work'}[flavour])
    if source_name not in [flavour+'-work',flavour+'-priv']:raise ValueError('unsupported provider auth boundary')
    source=(ACCOUNT_HOME if PROJECT else ROOT.parent)/source_name
    if flavour in ['claude','gemini'] and source_name==flavour+'-work':
        provider=json.loads((source/'.vertex.json').read_text())
        allowed=({'CLAUDE_CODE_USE_VERTEX','CLOUD_ML_REGION','ANTHROPIC_VERTEX_PROJECT_ID','ANTHROPIC_MODEL','ANTHROPIC_DEFAULT_OPUS_MODEL','ANTHROPIC_DEFAULT_SONNET_MODEL','ANTHROPIC_DEFAULT_HAIKU_MODEL'} if flavour=='claude' else {'GOOGLE_GENAI_USE_VERTEXAI','GOOGLE_CLOUD_PROJECT','GOOGLE_CLOUD_LOCATION','GEMINI_MODEL'})
        if set(provider)!=allowed:raise ValueError('Invalid work Vertex configuration')
        adc=source/'.config/gcloud/application_default_credentials.json'
        target=role_home(name)/'.config/gcloud/application_default_credentials.json'
        if not target.is_file():
            target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(adc.read_bytes());target.chmod(0o600)
        settings=role_home(name)/'.vertex.json';settings.write_text(json.dumps(provider));settings.chmod(0o600)
        if flavour=='gemini':
            settings=role_home(name)/'.gemini/settings.json'
            current=json.loads(settings.read_text()) if settings.exists() else {}
            current.setdefault('security',{}).setdefault('auth',{})['selectedType']='vertex-ai'
            settings.parent.mkdir(mode=0o700,parents=True,exist_ok=True);settings.write_text(json.dumps(current))
        return
    files={'claude':['.claude/.credentials.json'],'codex':['.codex/auth.json'],'gemini':['.gemini/oauth_creds.json','.gemini/google_accounts.json']}[flavour]
    seeded=False
    for relative in files:
        src=source/relative;dst=role_home(name)/relative
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            dst.write_bytes(src.read_bytes());dst.chmod(0o600);seeded=True
    metadata_path=next((p for p in [source/'.claude/.claude.json',source/'.claude.json'] if p.is_file()),None)
    if flavour=='claude' and seeded and metadata_path is not None:
        metadata=json.loads(metadata_path.read_text())
        config=role_home(name)/'.claude.json'
        current=json.loads(config.read_text()) if config.exists() else {}
        if 'oauthAccount' in metadata:current['oauthAccount']=metadata['oauthAccount']
        config.write_text(json.dumps(current));config.chmod(0o600)
    if flavour=='gemini' and (source/'.gemini/oauth_creds.json').is_file():
        config=role_home(name)/'.gemini/settings.json'
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
    cmd={'claude':['claude','--mcp-config','/home/agent/mcp.json','--settings','/home/agent/settings.json'],'codex':['codex','-c','check_for_update_on_startup=false','--sandbox','workspace-write','--ask-for-approval','on-request'],'gemini':['gemini']}[flavour]
    if flavour in ['claude','gemini'] and spec.get('auth_directory',flavour+'-work')==flavour+'-work':
        provider=json.loads((role_home(name)/'.vertex.json').read_text())
        for value in provider.values():
            if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_@.-]+',value):raise ValueError('Invalid Vertex environment value')
        provider['GOOGLE_APPLICATION_CREDENTIALS']='/home/agent/.config/gcloud/application_default_credentials.json'
        vertex_command=['env','-u','ANTHROPIC_API_KEY','-u','ANTHROPIC_AUTH_TOKEN','-u','CLAUDE_CODE_OAUTH_TOKEN','-u','GOOGLE_API_KEY','-u','GEMINI_API_KEY',*[key+'='+value for key,value in provider.items()]]
    else:vertex_command=[]
    if name=='observer':refresh_observer();cmd=['claude','--tools','Read,Grep,Glob,Write']
    elif name in ['private-connector','corporate-connector']:cmd=['claude','--tools','']
    run(['podman','exec',container(name),'tmux','set-option','-g','remain-on-exit','on'])
    # Operator launch is explicit; never supply a work prompt or bypass approval.
    run(['podman','exec',container(name),'tmux','respawn-pane','-k','-t','native:agent',shlex.join(vertex_command+cmd)])

def repair_failed_codex_builder():
    """Explicit image-repair operation: preserve every active session and private mount."""
    if not PROJECT:
        raise ValueError('Codex repair requires an explicitly selected project')
    name='builder';profile=PROFILES/name
    if json.loads((profile/'profile.json').read_text())['flavour']!='codex':
        raise ValueError('Selected builder is not a Codex profile; preserved')
    c=container(name)
    dead=subprocess.check_output(['podman','exec',c,'tmux','display-message','-p',
                                  '-t','native:agent','#{pane_dead}'],text=True).strip()
    if dead!='1':
        raise ValueError('Selected Codex builder is active; preserved')
    # Only the dead pane's idle container is replaced. Mounted homes and shared
    # workspaces remain on disk; sibling containers and their tmux panes are untouched.
    run(['podman','rm','--force',c],stdout=subprocess.DEVNULL)
    (profile/'launched').unlink(missing_ok=True)
    launch(name)
    (profile/'launched').touch()

def restore_codex_builder_marker():
    """Restore wake-up bookkeeping for an already live native session, without respawn."""
    if not PROJECT:
        raise ValueError('Codex marker restoration requires an explicitly selected project')
    profile=PROFILES/'builder';c=container('builder')
    if json.loads((profile/'profile.json').read_text())['flavour']!='codex':
        raise ValueError('Selected builder is not a Codex profile; preserved')
    dead=subprocess.check_output(['podman','exec',c,'tmux','display-message','-p',
                                  '-t','native:agent','#{pane_dead}'],text=True).strip()
    command=subprocess.check_output(['podman','exec',c,'tmux','display-message','-p',
                                     '-t','native:agent','#{pane_current_command}'],text=True).strip()
    if dead!='0' or command not in ['codex','node']:
        raise ValueError('A live native Codex builder is required; marker preserved')
    (profile/'launched').touch()

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


def prompt_sections(content):
    """Parse bracket templates or existing legacy role headers before writing anything."""
    headers=list(re.finditer(r'^\[([^\]\r\n]+)\][ \t]*$',content,re.M))
    legacy_headers=list(re.finditer(r'^# Role: ([a-z-]+)[ \t]*$',content,re.M))
    bracket_roles=any(re.match(r'Role:',header.group(1),re.I) for header in headers)
    bracket_format=bracket_roles or bool(headers) and not legacy_headers
    goal=''
    sections={}
    if bracket_format:
        role_lookup={name.replace('-','').casefold():name for name in ALL}
        preamble=content[:headers[0].start()]
        if any(line.strip() and not line.lstrip().startswith('#') for line in preamble.splitlines()):
            raise ValueError('Place active instructions under [Project] or [Role: Name]')
        for index,header in enumerate(headers):
            label=header.group(1).strip()
            body=content[header.end():headers[index+1].start() if index+1<len(headers) else len(content)].strip()
            if label.casefold()=='project':
                if index!=0:raise ValueError('[Project] must appear once before the role sections')
                goal=body
                continue
            match=re.fullmatch(r'Role:[ \t]*(.+)',label,re.I)
            role=role_lookup.get(re.sub(r'[-\s]','',match.group(1)).casefold()) if match else None
            if role is None:raise ValueError('Unknown prompt section: ['+label+']')
            if role in sections:raise ValueError('Duplicate prompt role: '+role)
            sections[role]=body
    else:
        headers=legacy_headers
        goal=content[:headers[0].start()].strip() if headers else ''
        for index,header in enumerate(headers):
            role=header.group(1)
            if role in sections:raise ValueError('Duplicate prompt role: '+role)
            sections[role]=content[header.end():headers[index+1].start() if index+1<len(headers) else len(content)].strip()
    if set(sections)!=set(ALL):
        raise ValueError('Prompt file must contain exactly one section per supported role')
    return goal,sections,bracket_format

def active_prompt_text(text):
    return '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('#')).strip()

def project_prompt_template(content):
    """Use explicit sections; legacy starter prose becomes commented examples."""
    _,sections,bracket_format=prompt_sections(content)
    output=['[Project]','# Describe this project\'s goal, context, boundaries and completion criteria here.','']
    for role in ALL:
        body=sections[role]
        if not bracket_format:
            lines=[]
            for line in body.splitlines():
                if line.lstrip().startswith('#'):continue
                if line.strip()=='Rough initial role prompt; refine through design.':
                    lines.append('# '+line.strip())
                else:lines.append('# Example: '+line if line.strip() else '')
            body='\n'.join(lines)
        output.extend(['[Role: '+role.replace('-',' ').title()+']',body,''])
    return '\n'.join(output)+'\n'

def apply_prompts():
    source=ROOT/'assistant-prompt.md' if PROJECT else ROOT.parent/'templates/assistant-prompts.md'
    goal,sections,bracket_format=prompt_sections(source.read_text())
    if bracket_format:
        goal=active_prompt_text(goal)
        sections={role:active_prompt_text(body) for role,body in sections.items()}
    roster='\n\nCollaboration roles: orchestrator routes and bounds work; builder implements; investigator diagnoses; challenger reviews assumptions; summarizer condenses decisions. Read addressed MCP messages. Distinguish proposals from verified results. Stop completed discussions; pause exhausted subscription work without paid API fallback.\n'
    for role in ALL:
        cfg=json.loads((PROFILES/role/'profile.json').read_text())
        prompt=sections[role]+'\n'
        if PROJECT:prompt='# Project: '+PROJECT+'\n\n'+goal+'\n\n'+prompt
        if PROJECT:
            prompt+='\nProject artifacts: /workspace/shared maps to this project’s workspace. '+('Read-only access; evaluate outcomes without modifying shared artifacts.' if role=='observer' else 'Read/write project artifacts here. Agree file/task ownership through the orchestrator and avoid concurrent edits to the same file.')+' Keep native credentials, private role instructions and account contexts outside this directory. Publish only explicitly authorized project results; never automatically dump private/corporate mail, account data or credentials into shared files.\n'
        if role in VISIBLE:prompt+=roster
        file=role_workspace(role)/ {'claude':'CLAUDE.md','codex':'AGENTS.md','gemini':'GEMINI.md'}[cfg['flavour']]
        temp=file.with_suffix('.pending');temp.write_text(prompt);temp.chmod(0o600);temp.replace(file)

def refresh_observer():
    with sqlite3.connect('file:'+str(STATE/'db.sqlite')+'?mode=ro',uri=True) as db:
        rows=db.execute('select id,from_agent,to_agent,text from messages order by id').fetchall()
    text='# Permitted worker discussion snapshot\n\n'+''.join(f'## Message {i}: {sender} to {recipient or "workers"}\n\n{body}\n\n' for i,sender,recipient,body in rows)
    directory=PROFILES/'observer/context';directory.mkdir(mode=0o700,exist_ok=True)
    file=directory/'discussion.md';file.write_text(text);file.chmod(0o600)
    print('Observer snapshot updated; no SQLite database or private connector context mounted.')

def deliver_observer_report():
    source=role_workspace('observer')/'report.md'
    if not source.is_file():raise ValueError('Observer report.md is not available yet')
    target=role_workspace('orchestrator')/'private-review.md'
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
    if sys.argv[1:2] in [['rename-project'],['destroy'],['archive'],['unarchive'],['--list'],['list-projects'],['--help'],['-h'],['version'],['setup'],['diagnostics']] or sys.argv[1:]==['help']:
        os.execv(sys.executable,[sys.executable,str(INSTALL_ROOT/'routing/project-team.py'),*sys.argv[1:]])
    if not PROJECT:
        project_actions=['create-project','start','stop','restart','status','watch','attach','launch',
                         'apply-prompts','refresh-observer','deliver-observer-report','preflight',
                         'launch-all','stop-containers','destroy','archive','unarchive','rename-project']
        if len(sys.argv)==2 and sys.argv[1] in project_actions:
            raise SystemExit('A project name is required for '+sys.argv[1]+'. Use ~/team --help for parameters')
        os.execv(sys.executable,[sys.executable,str(INSTALL_ROOT/'routing/project-team.py'),*sys.argv[1:]])
    if pathlib.Path(sys.argv[0]).name=='tmux':wake(sys.argv[1:]);return
    if len(sys.argv)>1 and sys.argv[1] not in ['init','gateway','prepare','stop','launch','attach','login','help','check','watch','apply-prompts','refresh-observer','deliver-observer-report']:
        raise SystemExit('Invalid command: '+sys.argv[1]+'. Use ~/team --help for supported commands')
    if PROJECT:project_name_validator()(PROJECT,ACCOUNT_HOME)
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

if __name__=='__main__':
    diagnostic=None;action=None
    if PROJECT and len(sys.argv)>1:
        path=INSTALL_ROOT/'routing/environment-diagnostics.py'
        if path.is_file():
            spec=importlib.util.spec_from_file_location('environment_diagnostics',path)
            diagnostic=importlib.util.module_from_spec(spec);spec.loader.exec_module(diagnostic)
            action={'init':'broker_init','gateway':'gateway','prepare':'containers_prepare','stop':'containers_stop'}.get(sys.argv[1])
    try:
        if diagnostic and action:diagnostic.record(ACCOUNT_HOME,action,'started')
        main()
        if diagnostic and action:diagnostic.record(ACCOUNT_HOME,action,'completed',0)
    except Exception:
        if diagnostic and action:diagnostic.record(ACCOUNT_HOME,action,'failed',1)
        raise
