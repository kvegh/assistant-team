#!/usr/bin/env python3
"""Replace only one Gemini role's stock-MCP command; never restart its session."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import tempfile


def configure(home, project, role):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,39}(?:-[0-9]{10})*', project):
        raise ValueError('Invalid project identifier')
    if role not in ('orchestrator', 'builder', 'investigator', 'challenger'):
        raise ValueError('Unsupported collaboration role')
    profile = Path(home) / 'projects' / project / 'profiles' / role
    metadata = profile / 'profile.json'
    if any(path.is_symlink() for path in [metadata] + list(metadata.parents)) or not metadata.is_file():
        raise ValueError('Role metadata must be an existing regular file')
    selected = json.loads(metadata.read_text())
    if not isinstance(selected, dict):
        raise ValueError('Invalid role metadata; preserved')
    if selected.get('flavour') != 'gemini':
        raise ValueError('Selected role is not a Gemini role')
    account = selected.get('account_profile')
    if account not in (None, 'gemini-work', 'gemini-priv'):
        raise ValueError('Unsupported Gemini account boundary')
    native = profile / 'accounts' / account / 'home' if account else profile / 'home'
    settings = native / '.gemini/settings.json'
    for path in [settings] + list(settings.parents):
        if path.is_symlink():
            raise ValueError('Symlink settings paths are not modified')
    info = settings.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('Native settings must be an operator-owned regular file')
    original = settings.read_bytes()
    config = json.loads(original)
    if not isinstance(config, dict) or not isinstance(config.get('mcpServers'), dict):
        raise ValueError('Invalid MCP settings; preserved')
    server = config['mcpServers'].get('agents_connector')
    if not isinstance(server, dict):
        raise ValueError('Expected stock connector server configuration')
    args = server.get('args')
    wrapped = server.get('command') == 'python3' and isinstance(args, list) and args[:1] == ['/opt/connector/bin/mcp-results.py']
    stock = args[1:] if wrapped else [server.get('command')] + args if isinstance(args, list) else []
    if len(stock) != 6 or stock[:5] != ['/opt/connector/bin/agents-connector', 'mcp-shim', '--socket', '/ipc/agent.sock', '--agent-token']:
        raise ValueError('Unexpected stock MCP command; preserved')
    if not isinstance(stock[-1], str) or not stock[-1]:
        raise ValueError('Missing existing broker authentication; preserved')
    if wrapped:
        return False
    config['mcpServers']['agents_connector'] = dict(server, command='python3', args=['/opt/connector/bin/mcp-results.py'] + stock)
    descriptor, backup = tempfile.mkstemp(prefix='.mcp-result-backup-', dir=settings.parent)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(original)
    descriptor, staged = tempfile.mkstemp(prefix='.mcp-result-pending-', dir=settings.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(config, stream)
            stream.flush()
            os.fsync(stream.fileno())
        Path(staged).replace(settings)
    finally:
        Path(staged).unlink(missing_ok=True)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('role')
    args = parser.parse_args()
    try:
        changed = configure(Path.home(), args.project, args.role)
    except (OSError, ValueError, TypeError):
        raise SystemExit('Gemini MCP configuration repair refused; settings preserved')
    print(json.dumps({'changed': changed, 'native_restarted': False, 'mcp_reconnect_required': True}))
