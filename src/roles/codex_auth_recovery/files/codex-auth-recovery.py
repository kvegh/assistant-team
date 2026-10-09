#!/usr/bin/env python3
"""Explicit same-account recovery; payload output is protected Ansible transport."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import uuid

spec = importlib.util.spec_from_file_location('transfer', Path(__file__).with_name('native-auth-transfer.py'))
transfer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)
Error = transfer.TransferError


def private_directory(path):
    fd = transfer.directory(path)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Error('directory_not_private')
    finally:
        os.close(fd)


def stopped(home):
    transfer.idle(Path(home).parent, [Path(home).name])
    try:
        result = subprocess.run(['podman', 'ps', '-q'], capture_output=True, text=True, check=True)
        if result.stdout.split():
            containers = json.loads(subprocess.run(['podman', 'inspect'] + result.stdout.split(), capture_output=True, text=True, check=True).stdout)
            for container in containers:
                for mount in container.get('Mounts', []):
                    source = Path(mount.get('Source', '/'))
                    path = Path(home)
                    if source == path or source in path.parents or path in source.parents:
                        raise Error('credential_container_writer_active')
    except Error:
        raise
    except (OSError, subprocess.CalledProcessError, ValueError):
        raise Error('container_writer_state_unavailable') from None


def identity(raw):
    data = transfer.object_json(raw)
    tokens = data.get('tokens', {})
    if data.get('auth_mode') != 'chatgpt' or data.get('OPENAI_API_KEY') or not isinstance(tokens, dict):
        raise Error('unsupported_auth_provider')
    if any(not isinstance(tokens.get(k), str) or not tokens[k] for k in ['account_id', 'access_token', 'refresh_token', 'id_token']):
        raise Error('incomplete_chatgpt_credentials')
    claims = []
    try:
        for key in ['access_token', 'id_token']:
            claim = json.loads(base64.urlsafe_b64decode(tokens[key].split('.')[1] + '==='))
            if not isinstance(claim, dict):
                raise ValueError()
            claims.append(claim)
    except (ValueError, IndexError, TypeError):
        raise Error('invalid_token_claims') from None
    access, ident = claims
    ns = 'https://api.openai.com/auth'
    if any(not isinstance(c.get(ns), dict) or c[ns].get('chatgpt_account_id') != tokens['account_id'] for c in claims) or not access.get('sub') or access.get('sub') != ident.get('sub') or not access.get('iss') or access.get('iss') != ident.get('iss'):
        raise Error('inconsistent_token_identity')
    return data, (tokens['account_id'], access['sub'], access['iss']), access


def capture(role, home, metadata_only=False):
    role, home = Path(role), Path(home)
    if home != role / 'accounts/codex-priv/home':
        raise Error('wrong_source_account_home')
    private_directory(role)
    for path in [role / 'accounts', role / 'accounts/codex-priv', home]:
        private_directory(path)
    private_directory(home / '.codex')
    cfg = transfer.object_json(transfer.read_file(role, 'profile.json'))
    if cfg.get('flavour') != 'codex' or cfg.get('auth_directory') != 'codex-priv' or cfg.get('account_profile') != 'codex-priv':
        raise Error('wrong_source_role_context')
    if 'source_auth_dir' in cfg and Path(cfg['source_auth_dir']).name != 'codex-priv':
        raise Error('wrong_source_role_context')
    stopped(home)
    raw = transfer.read_file(home, '.codex/auth.json')
    _, _, access = identity(raw)
    if not isinstance(access.get('exp'), (float, int)) or access['exp'] <= time.time():
        raise Error('candidate_access_expired')
    stopped(home)
    result = {'version': 1, 'purpose': 'codex_same_account_recovery', 'profile': 'codex-priv', 'source_stream': 'explicit_archived_builder', 'status': 'candidate_valid_unverified'}
    if not metadata_only:
        result['auth_b64'] = base64.b64encode(raw).decode()
    return result


def replace(root, config, payload, validate_only=False):
    if not isinstance(payload, dict) or set(payload) != {'version', 'purpose', 'profile', 'source_stream', 'status', 'auth_b64'} or payload['version'] != 1 or payload['purpose'] != 'codex_same_account_recovery' or payload['profile'] != 'codex-priv' or payload['source_stream'] != 'explicit_archived_builder' or payload['status'] != 'candidate_valid_unverified':
        raise Error('invalid_recovery_manifest')
    if 'codex-priv' not in transfer.enabled(config):
        raise Error('target_account_disabled')
    home = Path(root) / 'codex-priv'
    transfer.installation('codex-priv', home)
    private_directory(home / '.codex')
    stopped(home)
    try:
        raw = base64.b64decode(payload['auth_b64'], validate=True)
    except (ValueError, TypeError):
        raise Error('invalid_recovery_payload') from None
    _, source_id, access = identity(raw)
    if not isinstance(access.get('exp'), (float, int)) or access['exp'] <= time.time():
        raise Error('candidate_access_expired')
    before = transfer.read_file(home, '.codex/auth.json')
    _, target_id, _ = identity(before)
    if source_id != target_id:
        raise Error('account_identity_mismatch')
    changed = before != raw
    if changed and not validate_only:
        fd = transfer.directory(home / '.codex')
        temporary = '.codex-recovery-' + uuid.uuid4().hex
        try:
            out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            with os.fdopen(out, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            stopped(home)
            if transfer.read_file(home, '.codex/auth.json') != before:
                raise Error('destination_changed_during_recovery')
            os.replace(temporary, 'auth.json', src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=fd)
            except FileNotFoundError:
                pass
            os.close(fd)
    return {'version': 1, 'profile': 'codex-priv', 'source_stream': 'explicit_archived_builder', 'status': 'validated_same_account' if validate_only else 'replaced_same_account' if changed else 'unchanged_same_account', 'model_access': 'unverified', 'changed': changed and not validate_only}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['capture', 'replace'])
    parser.add_argument('--source-role')
    parser.add_argument('--source-home')
    parser.add_argument('--profiles-root')
    parser.add_argument('--environment-config')
    parser.add_argument('--metadata-only', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        result = capture(args.source_role, args.source_home, args.metadata_only) if args.action == 'capture' else replace(args.profiles_root, args.environment_config, transfer.object_json(sys.stdin.read(1048577)), args.validate_only)
        print(json.dumps(result))
    except (Error, OSError, ValueError, TypeError):
        # Never echo native documents, identifiers or command output on failure.
        print(json.dumps({'status': 'refused', 'reason': 'recovery_validation_failed'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
