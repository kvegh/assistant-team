#!/usr/bin/env python3
"""Offline checks for user-facing controls and private-role boundaries."""
import importlib.util,json,pathlib,selectors,socket,sqlite3,subprocess,time
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('team',root/'routing/connector-team.py');team=importlib.util.module_from_spec(spec);spec.loader.exec_module(team)
assert not any((team.PROFILES/n/'launched').exists() for n in team.ALL),'Do not inject fixtures during active native sessions'
assert (root.parent/'README.md').is_file()
assert (root.parent/'assistant-prompts.md').is_file()
assert (root.parent/'team').is_file()
for name in team.ALL:
    c=team.container(name)
    data=json.loads(subprocess.check_output(['podman','inspect',c],text=True))[0]
    assert data['State']['Running']
    assert data['HostConfig']['ReadonlyRootfs']
    assert data['HostConfig']['Memory']==768*1024*1024
    subprocess.run(['podman','exec',c,'tmux','has-session','-t','native'],check=True)
    if name not in team.VISIBLE:
        assert not (team.PROFILES/name/'home/mcp.json').exists()
        assert not (team.PROFILES/name/'ipc/agent.sock').exists()
    if name=='observer':assert any(m['Destination']=='/context' and not m['RW'] for m in data['Mounts'])
for directory,cli in [('claude-work','claude'),('claude-priv','claude'),('gemini','gemini'),('codex','codex'),('mistral','vibe')]:
    p=root.parent/directory
    assert (p/'.native-install.json').is_file() and (p/'login').is_file()
    for sub in ['.config','.cache','.local/share','.local/state','tmp']:assert (p/sub).is_dir()
for global_path in ['.claude.json','.claude','.codex','.gemini','.vibe']:
    assert not (root.parent/global_path).exists(),'Provider state escaped a scoped directory'
# Confirm actual stock event subscription and hidden report exclusion.
viewer=subprocess.Popen([str(root.parent/'team'),'watch'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
fixture='OFFLINE_USER_VIEW_FIXTURE'
try:
    selector=selectors.DefaultSelector();selector.register(viewer.stdout,selectors.EVENT_READ)
    assert selector.select(timeout=5)
    assert 'Live worker discussion' in viewer.stdout.readline()
    time.sleep(.1)  # Allow stock broker to enter its subscription handler.
    response=team.rpc({'kind':'tell','from':'builder','to':'investigator','text':fixture,'urgent':False})
    assert response['kind']=='tell_ack'
    assert selector.select(timeout=5)
    assert fixture in viewer.stdout.readline()
finally:
    viewer.terminate();viewer.wait(timeout=5)
    with sqlite3.connect(team.STATE/'db.sqlite') as db:db.execute('delete from messages where text=?',(fixture,))
team.refresh_observer()
report=team.PROFILES/'observer/workspace/report.md'
assert not report.exists(),'Do not replace a real observer report with a fixture'
try:
    report.write_text('OFFLINE_PRIVATE_REVIEW_FIXTURE')
    team.deliver_observer_report()
    assert (team.PROFILES/'orchestrator/workspace/private-review.md').read_text()=='OFFLINE_PRIVATE_REVIEW_FIXTURE'
    assert all(not (team.PROFILES/n/'workspace/private-review.md').exists() for n in team.VISIBLE if n!='orchestrator')
finally:
    report.unlink(missing_ok=True)
    (team.PROFILES/'orchestrator/workspace/private-review.md').unlink(missing_ok=True)
print('Eight tmux containers, five scoped native installations, live event viewer and private report boundary passed without model calls')
