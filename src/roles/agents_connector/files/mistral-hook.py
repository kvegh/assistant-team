#!/usr/bin/env python3
"""Connect native Vibe lifecycle hooks to its authenticated project inbox."""
import argparse
import json
import os
import pathlib
import shlex
import socket
import stat
import struct
import subprocess
import sys
import tempfile

LIMIT = 1048576
MARKER = '# AC-Agents managed Mistral connector'


def read_private(path):
    """Read operator configuration without following a redirected private file."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return ''
    with os.fdopen(fd) as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('Mistral configuration must be an owned regular file')
        text = source.read(LIMIT + 1)
        if len(text.encode()) > LIMIT:
            raise ValueError('Mistral configuration exceeds bounded size')
        return text


def write_private(path, text):
    if len(text.encode()) > LIMIT:
        raise ValueError('Mistral configuration exceeds bounded size')
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix='.ac-mistral-', dir=path.parent)
        with os.fdopen(fd, 'w') as output:
            output.write(text)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def without_managed(text):
    """Remove our marked block; preserve every byte outside it."""
    start, end = MARKER + ' BEGIN\n', MARKER + ' END\n'
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError('Invalid managed Mistral configuration block')
        before, rest = text.split(start, 1)
        if end not in rest:
            raise ValueError('Invalid managed Mistral configuration block')
        _, after = rest.split(end, 1)
        text = before + after
    return text


def managed_text(text, body):
    text = without_managed(text)
    start, end = MARKER + ' BEGIN\n', MARKER + ' END\n'
    return text + ('' if not text or text.endswith('\n') else '\n') + start + body + end


def configure(home, server_arguments, agent_token, *, profile, role):
    """Install only scoped inbox integration, retaining native tool permissions."""
    import tomllib
    directory = pathlib.Path(home) / '.vibe'
    # Reject redirected home/config directories before writing a bearer token.
    for path in [directory, *directory.parents]:
        if path.is_symlink():
            raise ValueError('Mistral configuration directory cannot be a symlink')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = directory / 'config.toml'
    original = read_private(config)
    unmanaged = without_managed(original)
    parsed = tomllib.loads(unmanaged)
    servers = parsed.get('mcp_servers', [])
    if not isinstance(servers, list) or not all(isinstance(item, dict) for item in servers):
        raise ValueError('Invalid Mistral MCP configuration')
    if any(item.get('name') == 'agents_connector' for item in servers):
        raise ValueError('Existing unmanaged agents_connector MCP requires operator review')
    defaults = ''.join(key + ' = false\n' for key in ['enable_update_checks', 'enable_auto_update']
                       if key not in parsed)
    server = ('[[mcp_servers]]\nname = "agents_connector"\ntransport = "stdio"\n'
              'command = "python3"\nargs = ' + json.dumps(
                  ['/opt/connector/bin/mcp-results.py'] + list(server_arguments)) + '\n'
              'sampling_enabled = false\ntool_timeout_sec = 180.0\n')
    config_text = managed_text(defaults + original, server)
    tomllib.loads(config_text)
    hooks = directory / 'hooks.toml'
    previous = read_private(hooks)
    unmanaged_hooks = without_managed(previous)
    existing = tomllib.loads(unmanaged_hooks).get('hooks', [])
    if not isinstance(existing, list) or not all(isinstance(item, dict) for item in existing):
        raise ValueError('Invalid Mistral hook configuration')
    if any(item.get('name', '').startswith('ac-agents-') for item in existing):
        raise ValueError('Existing unmanaged AC-Agents Vibe hooks require operator review')
    command = ['python3', '/opt/connector/bin/mistral-hook.py', '--socket', '/ipc/agent.sock',
               '--agent-token', agent_token, '--account-profile', profile, '--role', role]
    entries = ''
    for event in ['pre_tool', 'post_tool', 'post_agent']:
        entries += ('[[hooks]]\nname = "ac-agents-' + event + '"\ntype = '
                    + json.dumps(event) + '\ncommand = '
                    + json.dumps(shlex.join(command + ['--event', event])) + '\ntimeout = 15.0\n')
        if event != 'post_agent':
            entries += 'match = "*"\n'
    hooks_text = managed_text(previous, entries)
    tomllib.loads(hooks_text)
    trust = directory / 'trusted_folders.toml'
    decisions = tomllib.loads(read_private(trust))
    if set(decisions) - {'trusted', 'untrusted'}:
        raise ValueError('Unrecognized Mistral trust configuration requires operator review')
    trusted, untrusted = decisions.get('trusted', []), decisions.get('untrusted', [])
    if not all(isinstance(items, list) and all(isinstance(value, str) for value in items)
               for items in [trusted, untrusted]):
        raise ValueError('Invalid Mistral trust decisions')
    if not any(str(pathlib.PurePosixPath(item)) in ['/', '/workspace'] for item in untrusted):
        if '/workspace' not in trusted:
            trusted.append('/workspace')
    trust_text = 'trusted = ' + json.dumps(trusted) + '\nuntrusted = ' + json.dumps(untrusted) + '\n'
    # Validate both files before replacing either; never touch provider secrets.
    write_private(config, config_text)
    write_private(hooks, hooks_text)
    write_private(trust, trust_text)


def frame(connection, request):
    raw = json.dumps(request).encode()
    if len(raw) > LIMIT:
        raise ValueError('Broker request too large')
    connection.sendall(struct.pack('!I', len(raw)) + raw)

    def read(size):
        result = b''
        while len(result) < size:
            part = connection.recv(size - len(result))
            if not part:
                raise EOFError('Broker disconnected')
            result += part
        return result

    size = struct.unpack('!I', read(4))[0]
    if size > LIMIT:
        raise ValueError('Broker response too large')
    return json.loads(read(size))


def handle(event, body, connection, agent_token, cursor):
    if body.get('parent_session_id'):
        return {}  # A nested Vibe agent cannot mark its parent idle or consume its inbox.
    if body.get('hook_event_name') != event:
        raise ValueError('Mismatched native Mistral hook event')
    auth = frame(connection, {'kind': 'authenticate', 'agent_token': agent_token})
    if (auth.get('kind') != 'agent_info' or not isinstance(auth.get('name'), str)
            or auth.get('cli_kind') != 'mistral'):
        raise ValueError('Broker authentication failed')

    def state(value):
        response = frame(connection, {'kind': 'set_agent_state', 'agent_token': agent_token,
                                      'state': value})
        if response.get('kind') == 'error':
            raise ValueError('Broker state update failed')

    state('busy')
    if event == 'pre_tool':
        return {}
    if cursor.parent.is_symlink():
        raise ValueError('Mistral inbox cursor cannot use a symlink')
    since = int(read_private(cursor) or '0')
    response = frame(connection, {'kind': 'read_messages', 'agent': auth['name'], 'since': since})
    if response.get('kind') != 'messages' or not isinstance(response.get('messages'), list):
        raise ValueError('Broker inbox read failed')
    messages = response['messages']
    if not messages:
        if event == 'post_agent':
            state('idle')
        return {}
    lines = ['[agents-connector] Addressed inbox updates; answer asks using post_reply.']
    for item in messages:
        label = 'ASK ask_id=' + str(item['ask_id']) if item.get('ask_id') is not None else 'MESSAGE'
        lines.append(label + ' from ' + str(item['from']) + ': ' + str(item['text']))
    text = '\n'.join(lines)
    cursor.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if cursor.parent.is_symlink():
        raise ValueError('Mistral inbox cursor cannot use a symlink')
    write_private(cursor, str(max(item['id'] for item in messages)))
    if event == 'post_agent':
        return {'decision': 'deny', 'reason': text}
    return {'hook_specific_output': {'additional_context': text}}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    if sys.argv[1:2] == ['configure']:
        parser.add_argument('action', choices=['configure'])
        parser.add_argument('--home', required=True)
        args = parser.parse_args()
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('Configuration input too large')
        data = json.loads(raw)
        if (not isinstance(data, dict) or not isinstance(data.get('server_arguments'), list)
                or not all(isinstance(item, str) for item in data['server_arguments'])
                or not all(isinstance(data.get(key), str) and data[key]
                           for key in ['agent_token', 'account_profile', 'role'])):
            raise ValueError('Invalid Mistral integration configuration')
        configure(args.home, data['server_arguments'], data['agent_token'],
                  profile=data['account_profile'], role=data['role'])
        return
    parser.add_argument('--socket', required=True)
    parser.add_argument('--agent-token', required=True)
    parser.add_argument('--event', choices=['pre_tool', 'post_tool', 'post_agent'], required=True)
    parser.add_argument('--account-profile', required=True)
    parser.add_argument('--role', required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Hook input too large')
    body = json.loads(raw or b'{}')
    if not isinstance(body, dict):
        raise ValueError('Hook input requires an object')
    if body.get('parent_session_id'):
        print('{}')
        return
    if body.get('hook_event_name') != args.event:
        raise ValueError('Mismatched native Mistral hook event')
    recorder = pathlib.Path(__file__).with_name('native-sessions.py')
    completed = subprocess.run(
        [sys.executable, str(recorder), 'record-hook', 'mistral', args.account_profile, args.role],
        input=raw, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=5)
    if completed.returncode:
        raise ValueError('Mistral session tracking failed')
    cursor = pathlib.Path(args.socket).parent / 'mistral' / 'last_seen_message_id'
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(10)
        connection.connect(args.socket)
        output = handle(args.event, body, connection, args.agent_token, cursor)
    print(json.dumps(output))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, EOFError, subprocess.SubprocessError):
        print('{}')
        print('[AC-Agents]: Mistral broker hook failed; inspect protected project diagnostics.', file=sys.stderr)
        raise SystemExit(1)
