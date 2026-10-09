#!/usr/bin/env python3
"""Explicit private Claude recovery; account metadata is read, never copied."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

spec = importlib.util.spec_from_file_location('codex_recovery_guard', Path(__file__).with_name('codex-auth-recovery.py'))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
transfer = guard.transfer
Error = transfer.TransferError


def identity(home, relative):
    data = transfer.object_json(transfer.read_file(home, relative))
    account = data.get('oauthAccount')
    if not isinstance(account, dict) or any(not isinstance(account.get(k), str) or not account[k] for k in ['accountUuid', 'organizationUuid']):
        raise Error('missing_private_account_metadata')
    return account['accountUuid'], account['organizationUuid']


def credentials(raw, candidate=False):
    transfer.native_credentials('claude-priv', raw)
    data = transfer.object_json(raw)
    token = data.get('claudeAiOauth', {})
    if candidate and (not isinstance(token.get('refreshToken'), str) or not token['refreshToken']):
        raise Error('candidate_refresh_missing')
    return raw


def capture(role, home, metadata):
    role, home, metadata = Path(role), Path(home), Path(metadata)
    if home != role / 'accounts/claude-priv/home' or metadata != home / '.claude.json':
        raise Error('wrong_source_account_binding')
    for path in [role, role / 'accounts', role / 'accounts/claude-priv', home, home / '.claude']:
        guard.private_directory(path)
    cfg = transfer.object_json(transfer.read_file(role, 'profile.json'))
    if cfg.get('flavour') != 'claude' or cfg.get('auth_directory') != 'claude-priv' or cfg.get('account_profile') != 'claude-priv':
        raise Error('wrong_source_role_context')
    if 'source_auth_dir' in cfg and Path(cfg['source_auth_dir']).name != 'claude-priv':
        raise Error('wrong_source_role_context')
    guard.stopped(home)
    account = identity(home, '.claude.json')
    raw = credentials(transfer.read_file(home, '.claude/.credentials.json'), candidate=True)
    guard.stopped(home)
    return {'version': 1, 'purpose': 'claude_same_account_recovery', 'profile': 'claude-priv',
            'source_stream': 'explicit_archived_private_connector', 'account_binding': list(account),
            'auth_b64': base64.b64encode(raw).decode()}


def replace(root, config, payload, validate_only=False):
    if not isinstance(payload, dict) or set(payload) != {'version', 'purpose', 'profile', 'source_stream', 'account_binding', 'auth_b64'} or payload['version'] != 1 or payload['purpose'] != 'claude_same_account_recovery' or payload['profile'] != 'claude-priv' or payload['source_stream'] != 'explicit_archived_private_connector':
        raise Error('invalid_recovery_manifest')
    if 'claude-priv' not in transfer.enabled(config):
        raise Error('target_account_disabled')
    home = Path(root) / 'claude-priv'
    transfer.installation('claude-priv', home)
    guard.private_directory(home / '.claude')
    guard.stopped(home)
    account = identity(home, '.claude/.claude.json')
    if payload['account_binding'] != list(account):
        raise Error('account_identity_mismatch')
    try:
        raw = credentials(base64.b64decode(payload['auth_b64'], validate=True), candidate=True)
    except (ValueError, TypeError):
        raise Error('invalid_recovery_payload') from None
    before = credentials(transfer.read_file(home, '.claude/.credentials.json'))
    changed = before != raw
    if changed and not validate_only:
        fd = transfer.directory(home / '.claude')
        temporary = '.claude-recovery-' + uuid.uuid4().hex
        try:
            out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            with os.fdopen(out, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            guard.stopped(home)
            if transfer.read_file(home, '.claude/.credentials.json') != before or identity(home, '.claude/.claude.json') != account:
                raise Error('destination_changed_during_recovery')
            os.replace(temporary, '.credentials.json', src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=fd)
            except FileNotFoundError:
                pass
            os.close(fd)
    return {'version': 1, 'profile': 'claude-priv', 'source_stream': 'explicit_archived_private_connector',
            'status': 'validated_same_account' if validate_only else 'replaced_same_account' if changed else 'unchanged_same_account',
            'model_access': 'unverified', 'changed': changed and not validate_only}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['capture', 'replace'])
    for option in ['source-role', 'source-home', 'source-metadata', 'profiles-root', 'environment-config']:
        parser.add_argument('--' + option)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        result = capture(args.source_role, args.source_home, args.source_metadata) if args.action == 'capture' else replace(args.profiles_root, args.environment_config, transfer.object_json(sys.stdin.read(1048577)), args.validate_only)
        print(json.dumps(result))
    except (Error, OSError, ValueError, TypeError):
        print(json.dumps({'status': 'refused', 'reason': 'recovery_validation_failed'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
