#!/usr/bin/env python3
"""Translate native Antigravity lifecycle context into scoped stock broker IPC."""
import argparse
import json
import os
import pathlib
import socket
import struct
import sys

LIMIT = 1048576


def frame(connection, request):
    payload = json.dumps(request).encode()
    connection.sendall(struct.pack('!I', len(payload)) + payload)

    def read(size):
        data = b''
        while len(data) < size:
            part = connection.recv(size - len(data))
            if not part:
                raise EOFError('Broker disconnected')
            data += part
        return data

    size = struct.unpack('!I', read(4))[0]
    if size > LIMIT:
        raise ValueError('Broker response too large')
    return json.loads(read(size))


def context(messages):
    lines = ['[agents-connector] Addressed inbox updates; respond to asks using post_reply.']
    for item in messages:
        label = ('ASK ask_id=' + str(item['ask_id'])) if item.get('ask_id') is not None else 'MESSAGE'
        lines.append(label + ' from ' + str(item['from']) + ': ' + str(item['text']))
    return '\n'.join(lines)


def handle(event, body, connection, agent_token, cursor):
    auth = frame(connection, {'kind': 'authenticate', 'agent_token': agent_token})
    if auth.get('kind') != 'agent_info' or not isinstance(auth.get('name'), str):
        raise ValueError('Broker authentication failed')
    idle = event == 'Stop' and body.get('fullyIdle') is True
    # Keep the loop busy until its inbox has been checked, avoiding a premature nudge.
    state = 'busy'
    response = frame(connection, {'kind': 'set_agent_state', 'agent_token': agent_token, 'state': state})
    if response.get('kind') == 'error':
        raise ValueError('Broker state update failed')
    # A partial stop still has active work; do not consume its pending context.
    if event == 'Stop' and not idle:
        return {}
    since = int(cursor.read_text()) if cursor.exists() else 0
    response = frame(connection, {'kind': 'read_messages', 'agent': auth['name'], 'since': since})
    if response.get('kind') != 'messages' or not isinstance(response.get('messages'), list):
        raise ValueError('Broker inbox read failed')
    messages = response['messages']
    if not messages:
        if idle:
            frame(connection, {'kind': 'set_agent_state', 'agent_token': agent_token, 'state': 'idle'})
        return {}
    text = context(messages)
    cursor.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = cursor.with_suffix('.tmp')
    temporary.write_text(str(max(item['id'] for item in messages)))
    temporary.chmod(0o600)
    temporary.replace(cursor)
    if event == 'Stop':
        return {'decision': 'continue', 'reason': text}
    return {'injectSteps': [{'ephemeralMessage': text}]}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket', required=True)
    parser.add_argument('--agent-token', required=True)
    parser.add_argument('--event', choices=['PreInvocation', 'Stop'], required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Hook input too large')
    body = json.loads(raw or b'{}')
    if not isinstance(body, dict):
        raise ValueError('Hook input requires an object')
    cursor = pathlib.Path(args.socket).parent / 'antigravity' / 'last_seen_message_id'
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(10)
        connection.connect(args.socket)
        output = handle(args.event, body, connection, args.agent_token, cursor)
    print(json.dumps(output))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, EOFError):
        # Never echo hook input, authentication, messages or raw provider errors.
        print('{}')
        print('[AC-Agents]: Antigravity broker hook failed; inspect protected project diagnostics.', file=sys.stderr)
        raise SystemExit(1)
