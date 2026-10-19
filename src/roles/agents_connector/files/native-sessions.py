#!/usr/bin/env python3
"""Preserve exact native conversation identities; never select a newest session."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import uuid


class SessionError(ValueError):
    """Saved conversation identity cannot safely be restored."""


POINTER = '.ac-agents-session.json'
WORKSPACE = '/workspace'


def identifier(value):
    try:
        result = str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError) as exc:
        raise SessionError('Invalid native conversation identifier') from exc
    if str(value).lower() != result:
        raise SessionError('Invalid native conversation identifier')
    return result


def provider(vendor):
    aliases = {'agy': 'antigravity', 'agv': 'antigravity'}
    vendor = aliases.get(vendor, vendor)
    if vendor not in ('claude', 'codex', 'gemini', 'antigravity', 'mistral'):
        raise SessionError('Unsupported native conversation provider')
    return vendor


def session_identifier(value, vendor):
    # Vibe's own session-lease validator permits opaque IDs as well as UUIDs.
    if vendor == 'mistral':
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', value):
            raise SessionError('Invalid native conversation identifier')
        return value
    return identifier(value)


def _mistral_document(home, path, digest=None):
    """Read native metadata without opening checkpoints, projections or journals."""
    path = safe_file(home, path)
    try:
        if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise ValueError('invalid native metadata digest')
        body = path.read_bytes()
        if not body.endswith(b'\n'):
            raise ValueError('unterminated native document')
        body = body[:-1]
        if digest is not None and hashlib.sha256(body).hexdigest() != digest:
            raise ValueError('native metadata digest mismatch')
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError('invalid metadata')
        return value
    except (OSError, ValueError) as exc:
        raise SessionError('Cannot read Mistral conversation metadata: ' + path.name) from exc


def _mistral_unified(home, base):
    """Read the published runtime identity; Vibe stores no transcript in it."""
    found = set()
    for path in safe_file(home, base / 'unified').glob('*/CURRENT'):
        current = _mistral_document(home, path)
        sid = session_identifier(current.get('session_id'), 'mistral')
        generation = current.get('generation')
        if (path.parent.name != sid
                or current.get('store_format') != 'mistral.vibe.unified-session-store/v1'
                or not isinstance(current.get('store_format_minor', 1), int)
                or not 1 <= current.get('store_format_minor', 1) <= 8
                or not isinstance(generation, str) or not re.fullmatch(r'[0-9]{16}', generation)):
            raise SessionError('Invalid Mistral conversation generation')
        directory = path.parent / 'generations' / generation
        manifest = _mistral_document(home, directory / 'manifest.json', current.get('manifest_sha256', ''))
        if (manifest.get('session_id') != sid or manifest.get('generation') != generation
                or manifest.get('snapshot_sequence') != current.get('snapshot_sequence')):
            raise SessionError('Mistral conversation generation identity mismatch')
        descriptor = manifest.get('runtime_state')
        filename = descriptor.get('path') if isinstance(descriptor, dict) else None
        if filename != 'runtime-state.json':
            raise SessionError('Invalid Mistral runtime metadata reference')
        runtime = _mistral_document(home, directory / filename, descriptor.get('sha256', ''))
        metadata, identity = runtime.get('session_metadata'), runtime.get('identity')
        if not isinstance(metadata, dict) or not isinstance(identity, dict):
            raise SessionError('Invalid Mistral runtime identity')
        if (metadata.get('cwd') == WORKSPACE and not metadata.get('parent_session_id')
                and metadata.get('root_session_id') == sid
                and identity.get('session_id') == sid
                and identity.get('root_session_id') == sid
                and identity.get('kind') == 'root' and identity.get('depth') == 0
                and not identity.get('parent_session_id')):
            found.add(sid)
    return found


def safe_file(home, path):
    """Refuse symlink traversal while inspecting native local metadata."""
    home, path = Path(home), Path(path)
    try:
        relative = path.relative_to(home)
    except ValueError as exc:
        raise SessionError('Native conversation metadata is outside its account home') from exc
    if home.is_symlink():
        raise SessionError('Native conversation home is a symlink')
    current = home
    for part in relative.parts:
        current /= part
        try:
            if current.is_symlink():
                raise SessionError('Native conversation metadata contains a symlink')
        except OSError as exc:
            raise SessionError('Cannot inspect native conversation metadata') from exc
    return path


def read_json(home, path):
    path = safe_file(home, path)
    try:
        with path.open(encoding='utf-8') as stream:
            return json.load(stream)
    except (OSError, ValueError) as exc:
        raise SessionError('Cannot read native conversation metadata: ' + path.name) from exc


def rows(home, path, table, columns):
    path = safe_file(home, path)
    try:
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as connection:
            connection.row_factory = sqlite3.Row
            # Table and column names are internal constants, never external input.
            # Do not load titles, previews, prompts, or conversation contents.
            return [dict(row) for row in connection.execute(
                'SELECT ' + ', '.join(columns) + ' FROM ' + table)]
    except sqlite3.Error as exc:
        raise SessionError('Cannot read native conversation database: ' + path.name) from exc


def _uuid(value):
    try:
        return identifier(value)
    except SessionError:
        return None


def histories(home, vendor):
    """Return eligible main IDs, reading only local metadata, never model APIs."""
    home, vendor = Path(home), provider(vendor)
    found = set()
    if vendor == 'claude':
        base = safe_file(home, home / '.claude/projects')
        for path in base.glob('-workspace/*.jsonl'):
            safe_file(home, path)
            file_id = _uuid(path.stem)
            if not file_id:
                continue
            try:
                with path.open(encoding='utf-8') as stream:
                    for line in stream:
                        entry = json.loads(line)
                        if entry.get('type') not in ('user', 'assistant'):
                            continue
                        if (entry.get('sessionId') == file_id
                                and entry.get('cwd') == WORKSPACE
                                and not entry.get('isSidechain', False)):
                            found.add(file_id)
                            break
            except (OSError, ValueError, AttributeError) as exc:
                raise SessionError('Cannot read Claude conversation metadata') from exc
    elif vendor == 'gemini':
        base = safe_file(home, home / '.gemini/tmp')
        project_hash = hashlib.sha256(WORKSPACE.encode()).hexdigest()
        # Deliberately do not recurse into nested subagent histories.
        for path in base.glob('*/chats/session-*'):
            if path.suffix not in ('.json', '.jsonl'):
                continue
            safe_file(home, path)
            try:
                with path.open(encoding='utf-8') as stream:
                    entry = json.loads(stream.readline()) if path.suffix == '.jsonl' else json.load(stream)
            except (OSError, ValueError) as exc:
                raise SessionError('Cannot read Gemini conversation metadata') from exc
            if not isinstance(entry, dict):
                raise SessionError('Invalid Gemini conversation metadata')
            # Legacy JSON had no kind; nested subagents are excluded by location.
            if (entry.get('kind', 'main') == 'main'
                    and entry.get('projectHash') == project_hash):
                session_id = _uuid(entry.get('sessionId'))
                if session_id:
                    found.add(session_id)
    elif vendor == 'mistral':
        base = safe_file(home, home / '.vibe/logs/session')
        for path in base.glob('session_*/meta.json'):
            entry = read_json(home, path)
            if not isinstance(entry, dict):
                raise SessionError('Invalid Mistral conversation metadata')
            environment = entry.get('environment')
            if (isinstance(environment, dict)
                    and environment.get('working_directory') == WORKSPACE
                    and not entry.get('parent_session_id')
                    and safe_file(home, path.parent / 'messages.jsonl').is_file()):
                found.add(session_identifier(entry.get('session_id'), vendor))
        found.update(_mistral_unified(home, base))
    elif vendor == 'codex':
        path = safe_file(home, home / '.codex/state_5.sqlite')
        if path.exists():
            for entry in rows(home, path, 'threads', ('id', 'source', 'thread_source', 'cwd', 'archived', 'agent_path')):
                if (entry.get('source') == 'cli'
                        and entry.get('thread_source', 'user') == 'user'
                        and entry.get('cwd') == WORKSPACE
                        and not entry.get('archived', False)
                        and not entry.get('agent_path')):
                    session_id = _uuid(entry.get('id'))
                    if session_id:
                        found.add(session_id)
            try:
                with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as connection:
                    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if 'thread_spawn_edges' in tables:
                        found.difference_update(row[0] for row in connection.execute('SELECT child_thread_id FROM thread_spawn_edges'))
            except sqlite3.Error as exc:
                raise SessionError('Cannot check Codex main conversation identity') from exc
    else:
        base = safe_file(home, home / '.gemini/antigravity-cli')
        # Database location can move between native CLI releases; only fixed
        # filenames within this one provider home are considered.
        for path in base.rglob('conversation_summaries.db'):
            for entry in rows(home, path, 'conversation_summaries', ('conversation_id', 'workspace_uris', 'parent_conversation_id', 'nesting_depth')):
                session_id = _uuid(entry.get('conversation_id'))
                workspaces = entry.get('workspace_uris', '')
                if isinstance(workspaces, str):
                    try:
                        workspaces = json.loads(workspaces)
                    except ValueError:
                        workspaces = [workspaces]
                if isinstance(workspaces, dict):
                    workspaces = list(workspaces)
                if (session_id and not entry.get('parent_conversation_id')
                        and not entry.get('nesting_depth', 0)
                        and isinstance(workspaces, list)
                        and any(value in (WORKSPACE, 'file:///workspace') for value in workspaces)):
                    # A summary alone is not the persisted conversation.
                    if safe_file(home, base / 'conversations' / (session_id + '.db')).is_file():
                        found.add(session_id)
    return found


def _load(home, vendor, account_profile, role):
    path = safe_file(home, Path(home) / POINTER)
    if not path.exists():
        return None
    metadata = path.stat()
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600):
        raise SessionError('Saved conversation pointer must be an owned mode-0600 regular file')
    value = read_json(home, path)
    if (not isinstance(value, dict) or value.get('schema') != 1
            or value.get('vendor') != vendor or value.get('account_profile') != account_profile
            or value.get('role') != role):
        raise SessionError('Saved conversation pointer does not match this role and account')
    session_identifier(value.get('session_id'), vendor)
    if not isinstance(value.get('pending'), bool):
        raise SessionError('Invalid saved conversation pointer')
    return value


def _save(home, vendor, account_profile, role, session_id, pending=False):
    home = Path(home)
    path = safe_file(home, home / POINTER)
    # Validate an existing pointer's ownership before replacing it, while allowing
    # the actual native SessionStart hook to update an old ID after /clear.
    if path.exists():
        _load(home, vendor, account_profile, role)
    value = dict(schema=1, vendor=vendor, account_profile=account_profile,
                 role=role, session_id=session_identifier(session_id, vendor), pending=pending)
    fd, temporary = tempfile.mkstemp(prefix='.ac-agents-session-', dir=home)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def capture(home, vendor, account_profile, role, session_id=None):
    """Save an exact live ID, or adopt the sole eligible native main history."""
    home, vendor = Path(home), provider(vendor)
    existing = _load(home, vendor, account_profile, role)
    eligible = histories(home, vendor)
    authoritative = session_id is not None
    if session_id is not None:
        session_id = session_identifier(session_id, vendor)
    elif existing:
        session_id = existing['session_id']
    elif len(eligible) == 1:
        session_id = next(iter(eligible))
    elif len(eligible) > 1:
        raise SessionError('Multiple native conversations exist; an exact active conversation ID is required')
    if session_id is None:
        return None
    if session_id not in eligible:
        if authoritative:
            # A live native identity can represent a new empty conversation after
            # /clear; preserve it instead of accidentally resurrecting an old one.
            _save(home, vendor, account_profile, role, session_id, pending=True)
            return None
        if existing and existing.get('pending'):
            return None  # Exact current native session has not persisted turns.
        raise SessionError('Saved native conversation is missing or does not belong to this workspace')
    _save(home, vendor, account_profile, role, session_id)
    return session_id


def resume_arguments(home, vendor, account_profile, role):
    vendor = provider(vendor)
    session_id = capture(home, vendor, account_profile, role)
    if session_id is None:
        return []
    return [{'claude': '--resume', 'gemini': '--resume',
             'codex': 'resume', 'antigravity': '--conversation', 'mistral': '--resume'}[vendor], session_id]


def _descendants(parent):
    result = {parent}
    parents = {}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                # comm can contain spaces and parentheses; split after its last ).
                fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                parents[int(entry.name)] = int(fields[1])
            except (OSError, ValueError, IndexError):
                continue
    changed = True
    while changed:
        before = len(result)
        result.update(pid for pid, ppid in parents.items() if ppid in result)
        changed = len(result) != before
    return result


def discover_active(home, vendor, native_pid=None):
    """Inspect a native tmux process's own identity, not newest history timestamps."""
    home, vendor = Path(home), provider(vendor)
    if native_pid is None:
        try:
            result = subprocess.run(['tmux', 'display-message', '-p', '-t', 'native:agent', '#{pane_pid}'],
                                    check=True, capture_output=True, text=True, timeout=5)
            native_pid = int(result.stdout.strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
    candidates = set()
    if vendor in ('claude', 'codex', 'mistral'):
        for pid in _descendants(native_pid):
            if vendor == 'claude':
                path = safe_file(home, home / '.claude/sessions' / (str(pid) + '.json'))
                if not path.exists():
                    continue
                entry = read_json(home, path)
                try:
                    start = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]
                except (OSError, IndexError):
                    continue
                if (entry.get('pid') == pid and str(entry.get('procStart')) == start
                        and entry.get('cwd') == WORKSPACE
                        and entry.get('kind') == 'interactive' and entry.get('entrypoint') == 'cli'):
                    candidates.add(identifier(entry.get('sessionId')))
            else:
                try:
                    descriptors = list(Path('/proc', str(pid), 'fd').iterdir())
                except OSError:
                    continue
                for fd in descriptors:
                    try:
                        target = os.readlink(fd)
                    except OSError:
                        continue
                    lock_home = (home / '.vibe/logs/session/active' if vendor == 'mistral'
                                 else home / '.codex/thread-writer-locks')
                    match = re.fullmatch(re.escape(str(lock_home)) + r'/([A-Za-z0-9_-]+)\.lock', target)
                    if match:
                        candidates.add(session_identifier(match.group(1), vendor))
    elif vendor == 'antigravity':
        path = safe_file(home, home / '.gemini/antigravity-cli/cache/last_conversations.json')
        if path.exists():
            value = read_json(home, path)
            if isinstance(value, dict):
                for key in (WORKSPACE, 'file:///workspace'):
                    entry = value.get(key)
                    if isinstance(entry, str):
                        candidates.add(identifier(entry))
                    elif isinstance(entry, dict) and entry.get('conversation_id'):
                        candidates.add(identifier(entry['conversation_id']))
    if vendor == 'codex' and candidates:
        database = safe_file(home, home / '.codex/state_5.sqlite')
        if database.exists():
            known_ids = {entry['id'] for entry in rows(home, database, 'threads', ('id',))}
            candidates.difference_update(known_ids - histories(home, vendor))
    if vendor == 'mistral' and candidates:
        eligible = histories(home, vendor)
        base = safe_file(home, home / '.vibe/logs/session')
        known = {path.parent.name for path in safe_file(home, base / 'unified').glob('*/CURRENT')}
        for path in base.glob('session_*/meta.json'):
            entry = read_json(home, path)
            if isinstance(entry, dict):
                known.add(entry.get('session_id'))
        # Keep a just-created, empty live session authoritative after /clear,
        # while removing persisted subagents and foreign-workspace sessions.
        candidates.difference_update(known - eligible)
    if len(candidates) > 1:
        raise SessionError('Multiple active native main conversations were detected')
    return next(iter(candidates), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('capture-live', 'record-hook'))
    parser.add_argument('vendor')
    parser.add_argument('account_profile')
    parser.add_argument('role')
    args = parser.parse_args()
    home = Path.home()
    try:
        vendor = provider(args.vendor)
        if args.action == 'record-hook':
            payload = json.load(sys.stdin)
            if isinstance(payload, dict) and vendor == 'mistral' and payload.get('parent_session_id'):
                return 0  # A native subagent must never replace its parent's pointer.
            if not isinstance(payload, dict) or payload.get('cwd') != WORKSPACE:
                raise SessionError('Session hook workspace does not match')
            session_id = session_identifier(payload.get('session_id'), vendor)
            _save(home, vendor, args.account_profile, args.role, session_id,
                  pending=session_id not in histories(home, vendor))
        else:
            capture(home, vendor, args.account_profile, args.role, discover_active(home, vendor))
    except (SessionError, ValueError, OSError) as exc:
        print('Native session preservation failed: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
