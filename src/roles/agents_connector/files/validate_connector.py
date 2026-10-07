#!/usr/bin/env python3
"""Offline integration checks: no provider auth or inference."""
import importlib.util,json,os,pathlib,socket,sqlite3,subprocess,time
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('team',root/'routing/connector-team.py');team=importlib.util.module_from_spec(spec);spec.loader.exec_module(team)
def request(name,obj,auth=True):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(5);s.connect(str(root/'profiles'/name/'ipc/agent.sock'))
        if auth:assert team.frame(s,{'kind':'authenticate','agent_token':team.token(name)})['kind']=='agent_info'
        return team.frame(s,obj)
assert not any((root/'profiles'/n/'launched').exists() for n in team.ALL), 'Run offline validation before launching native sessions'
for name in team.ALL:
    p=root/'profiles'/name
    if name in team.VISIBLE:assert request(name,{'kind':'list_agents'})['kind']=='agents'
    for denied in [{'kind':'shutdown'},{'kind':'get_agent','name':'builder'},{'kind':'register_agent','name':'illegal','cli_kind':'claude','workdir':None,'extra_args':[]},{'kind':'read_messages','agent':'other','since':0},{'kind':'tell','from':'other','to':'builder','text':'forged','urgent':False}]:
        if name in team.VISIBLE:assert request(name,denied)['kind']=='error'
    if name in team.VISIBLE:assert request(name,{'kind':'authenticate','agent_token':'wrong'},False)['kind']=='error'
    cfg=json.loads((p/'profile.json').read_text());f=cfg['flavour'];c=team.container(name)
    got=subprocess.check_output(['podman','exec',c,f,'--version'],text=True);assert team.VERSIONS[f] in got
    subprocess.run(['podman','exec',c,f,'--help'],check=True,stdout=subprocess.DEVNULL)
    assert subprocess.check_output(['podman','exec',c,'id','-u'],text=True).strip()=='1000'
    data=json.loads(subprocess.check_output(['podman','inspect',c],text=True))[0]
    assert data['HostConfig']['ReadonlyRootfs']
    assert data['HostConfig']['Memory']==768*1024*1024
    assert all('state' not in m['Source'] for m in data['Mounts'])
    assert not any('/run/podman' in m['Source'] or '/var/run/docker' in m['Source'] for m in data['Mounts'])
    assert subprocess.check_output(['podman','exec',c,'tmux','list-sessions'],text=True).startswith('native:')
    proc=subprocess.check_output(['podman','exec',c,'cat','/proc/1/status'],text=True)
    assert 'CapEff:\t0000000000000000' in proc and 'NoNewPrivs:\t1' in proc
    text=(p/'workspace'/ {'claude':'CLAUDE.md','codex':'AGENTS.md','gemini':'GEMINI.md'}[f]).read_text()
    if name in team.VISIBLE:assert 'observer' not in text.lower() and 'evaluator' not in text.lower()
    if name not in team.VISIBLE:assert not (p/'home/mcp.json').exists() and not (p/'ipc/agent.sock').exists()
    print(name+': native CLI/tmux/isolation and applicable IPC checks passed')
# Verify stock native hook delivery through the filter and SQLite persistence.
message='OFFLINE_FIXTURE_CONTENT_NOT_A_WAKE_PROMPT'
r=request('builder',{'kind':'tell','from':'builder','to':'investigator','text':message,'urgent':False});assert r['kind']=='tell_ack'
hook=subprocess.check_output([str(team.BIN),'hook','--socket',str(root/'profiles/investigator/ipc/agent.sock'),'--agent-token',team.token('investigator'),'--event','user_prompt_submit','--cli-kind','claude'],input='{}',text=True)
assert message in hook
for receiver,kind,event in [('builder','codex','user_prompt_submit'),('challenger','gemini','before_agent')]:
    r=request('orchestrator',{'kind':'tell','from':'orchestrator','to':receiver,'text':message,'urgent':False})
    h=subprocess.check_output([str(team.BIN),'hook','--socket',str(root/'profiles'/receiver/'ipc/agent.sock'),'--agent-token',team.token(receiver),'--event',event,'--cli-kind',kind],input='{}',text=True)
    assert message in h
with sqlite3.connect(root/'state/db.sqlite') as db:assert db.execute('select count(*) from messages where text=?',(message,)).fetchone()[0]>=1
agents=team.rpc({'kind':'list_agents'})['agents'];assert {a['name'] for a in agents}==set(team.VISIBLE)
# Wake targets a harmless cat pane, never a model. Launch marker removed in finally.
p=root/'profiles/challenger';marker=p/'launched';assert not marker.exists()
c=team.container('challenger')
subprocess.run(['podman','exec',c,'tmux','respawn-pane','-k','-t','native:agent','cat'],check=True)
try:
    marker.touch()
    request('challenger',{'kind':'set_agent_state','agent_token':team.token('challenger'),'state':'idle'})
    request('builder',{'kind':'tell','from':'builder','to':'challenger','text':message,'urgent':True})
    time.sleep(0.3)
    capture=subprocess.check_output(['podman','exec',c,'tmux','capture-pane','-p','-t','native:agent'],text=True)
    assert 'New addressed event; read your authenticated inbox.' in capture
    assert message not in capture
    subprocess.run(['podman','exec',c,'tmux','clear-history','-t','native:agent'],check=True)
    subprocess.run(['podman','exec',c,'tmux','respawn-pane','-k','-t','native:agent','cat'],check=True)
    time.sleep(5.1)  # Let stock cooldown expire; isolate the busy-state check.
    request('challenger',{'kind':'set_agent_state','agent_token':team.token('challenger'),'state':'busy'})
    request('builder',{'kind':'tell','from':'builder','to':'challenger','text':'BUSY_FIXTURE','urgent':True})
    time.sleep(0.3)
    capture=subprocess.check_output(['podman','exec',c,'tmux','capture-pane','-p','-t','native:agent'],text=True)
    assert 'New addressed event' not in capture
    request('challenger',{'kind':'set_agent_state','agent_token':team.token('challenger'),'state':'idle'})
    asked=request('builder',{'kind':'ask','from':'builder','to':'challenger','text':message,'urgent':True})
    assert asked['kind']=='ask_ack'
    time.sleep(0.3)
    capture=subprocess.check_output(['podman','exec',c,'tmux','capture-pane','-p','-t','native:agent'],text=True)
    assert 'New addressed event; read your authenticated inbox.' in capture and message not in capture
finally:
    marker.unlink(missing_ok=True)
    subprocess.run(['podman','exec',c,'tmux','respawn-pane','-k','-t','native:agent','/bin/bash'],check=True)
with sqlite3.connect(root/'state/db.sqlite') as db:
    db.execute('delete from messages where text in (?,?)',(message,'BUSY_FIXTURE'))
    db.execute('delete from asks where text=?',(message,))
for name in team.VISIBLE:team.rpc({'kind':'set_agent_state','agent_token':team.token(name),'state':'idle'})
print('SQLite, stock hook, hidden roster and fixed-only real tmux wake passed; no models invoked')
