#!/usr/bin/env python3
"""Explicitly authorized disruptive group lifecycle check; never invoke on live work."""
import importlib.util,pathlib,sqlite3,subprocess,time
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('team',root/'routing/connector-team.py');team=importlib.util.module_from_spec(spec);spec.loader.exec_module(team)
target='assistant-connector.target'
services=['assistant-connector-broker.service','assistant-connector-gateway.service','assistant-connector-containers.service']

def system(*args,check=True):
    return subprocess.run(['systemctl','--user',*args],check=check,capture_output=True,text=True)

def running():
    for s in services+[target]:assert system('is-active',s).stdout.strip()=='active'
    for n in team.VISIBLE:
        c=team.container(n)
        assert subprocess.check_output(['podman','inspect','--format','{{.State.Running}}',c],text=True).strip()=='true'
        subprocess.run(['podman','exec',c,'tmux','has-session','-t','native'],check=True)

def database():
    with sqlite3.connect(root/'state/db.sqlite') as db:
        return {t:db.execute('select * from '+t+' order by id').fetchall() for t in ['agents','messages','asks','replies']}

assert not any((root/'profiles'/n/'launched').exists() for n in team.VISIBLE),'Native sessions must be stopped before lifecycle validation'
for n in team.VISIBLE:
    probe="import pathlib; names=[p.read_text().strip() for p in pathlib.Path('/proc').glob('[0-9]*/comm') if p.exists()]; assert not any(n in ['node','claude','codex','gemini'] or n.startswith('codex') for n in names), 'Native login/model process detected'"
    subprocess.run(['podman','exec',team.container(n),'python3','-c',probe],check=True)
    command=subprocess.check_output(['podman','exec',team.container(n),'tmux','display-message','-p','-t','native:agent','#{pane_current_command}'],text=True).strip()
    assert command in ['bash','sh'],'Active native work detected; refusing lifecycle test'
assert system('is-enabled',target).stdout.strip()=='enabled'
for s in services:assert system('is-enabled',s,check=False).stdout.strip()=='disabled'
for n in team.VISIBLE:
    for directory in ['home','workspace']:
        (root/'profiles'/n/directory/'.lifecycle-check').write_text('persist through group lifecycle')
before=database()
try:
    running()
    system('stop',target)
    deadline=time.monotonic()+120
    while True:
        states={s:system('is-active',s,check=False).stdout.strip() for s in services+[target]}
        if all(value=='inactive' for value in states.values()):break
        if 'failed' in states.values() or time.monotonic()>deadline:raise RuntimeError('Group stop failed: '+str(states))
        time.sleep(0.5)
    for n in team.VISIBLE:assert subprocess.check_output(['podman','inspect','--format','{{.State.Running}}',team.container(n)],text=True).strip()=='false'
    print('Target stop: all three services inactive, only the five managed containers stopped')
    system('start',target);running()
    system('restart',target);running()
    assert database()==before,'SQLite data changed across lifecycle'
    for n in team.VISIBLE:
        for directory in ['home','workspace']:
            assert (root/'profiles'/n/directory/'.lifecycle-check').read_text()=='persist through group lifecycle'
    print('Target start/restart: services and native tmux containers running; SQLite and persistent data unchanged')
finally:
    system('start',target)
    for n in team.VISIBLE:
        for directory in ['home','workspace']:(root/'profiles'/n/directory/'.lifecycle-check').unlink(missing_ok=True)
