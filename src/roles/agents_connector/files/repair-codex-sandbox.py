#!/usr/bin/env python3
"""Explicitly replace only a sandbox-blocked Codex builder and resume its session."""
import argparse
import importlib.util
import json
import pathlib
import shlex
import subprocess
import uuid

spec = importlib.util.spec_from_file_location('codex_sandbox_core', pathlib.Path(__file__).with_name('connector-team.py'))
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--session-id', required=True)
args = parser.parse_args()
uuid.UUID(args.session_id)
if not core.PROJECT:
    raise ValueError('An explicit project is required')
profile = core.PROFILES / 'builder'
if json.loads((profile / 'profile.json').read_text())['flavour'] != 'codex':
    raise ValueError('The selected builder is not Codex')
container = core.container('builder')
current = json.loads(subprocess.check_output(['podman', 'inspect', container], text=True))[0]
if current.get('ProcessLabel', '').split(':')[2:3] == ['ac_agents_codex.process']:
    print(json.dumps({'changed': False, 'reason': 'Dedicated domain already active; session preserved'}))
    raise SystemExit(0)
sessions = list((core.role_home('builder') / '.codex/sessions').glob('**/*' + args.session_id + '.jsonl'))
if len(sessions) != 1 or sessions[0].is_symlink():
    raise ValueError('The exact saved conversation could not be verified')
with sessions[0].open() as stream:
    first = json.loads(stream.readline())
if first.get('type') != 'session_meta' or first.get('payload', {}).get('id') != args.session_id:
    raise ValueError('Saved conversation identity differs; builder preserved')
dead = subprocess.check_output(['podman', 'exec', container, 'tmux', 'display-message', '-p', '-t', 'native:agent', '#{pane_dead}'], text=True).strip()
if dead != '0':
    raise ValueError('Expected live saved builder session is absent; builder preserved')
raw = subprocess.check_output(['podman', 'exec', container, 'tmux', 'display-message', '-p', '-t', 'native:agent', '#{pane_start_command}'], text=True).strip()
command = shlex.split(raw)
if len(command) == 1:
    command = shlex.split(command[0])
if not command or command[0] != 'codex' or 'resume' in command or '--sandbox' not in command or command[command.index('--sandbox') + 1] != 'workspace-write':
    raise ValueError('Original native launch does not match the expected restricted Codex session')
command += ['resume', args.session_id]
# Stopping the exact container interrupts only this saved builder conversation;
# it never approves a pending outside-sandbox or unrelated MCP operation.
# All mounted profile/workspace/IPC state remains on disk and is reused unchanged.
core.run(['podman', 'stop', '--time', '10', container], stdout=subprocess.DEVNULL)
core.run(['podman', 'rm', container], stdout=subprocess.DEVNULL)
(profile / 'launched').unlink(missing_ok=True)
core.start_container('builder')
core.run(['podman', 'exec', container, 'tmux', 'set-option', '-g', 'remain-on-exit', 'on'])
core.run(['podman', 'exec', container, 'tmux', 'respawn-pane', '-k', '-t', 'native:agent', shlex.join(command)])
(profile / 'launched').touch()
print(json.dumps({'changed': True, 'reason': 'Same saved builder conversation resumed in the dedicated domain'}))
