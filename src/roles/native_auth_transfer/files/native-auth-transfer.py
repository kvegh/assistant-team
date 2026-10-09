#!/usr/bin/env python3
"""Selective bootstrap capture/restore; secret payloads must stay under no_log."""
import argparse
import base64
import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

PROFILES = ('claude-work', 'claude-priv', 'gemini-work', 'gemini-priv',
            'codex-work', 'codex-priv', 'mistral-work', 'mistral-priv')
CLAUDE_METADATA = ('oauthAccount', 'hasCompletedOnboarding', 'lastOnboardingVersion', 'lastReleaseNotesSeen')
OAUTH_METADATA = ('accountUuid', 'emailAddress', 'organizationUuid', 'organizationRole', 'workspaceRole', 'displayName')
VERTEX_KEYS = {
    'claude-work': {'CLAUDE_CODE_USE_VERTEX', 'CLOUD_ML_REGION', 'ANTHROPIC_VERTEX_PROJECT_ID',
                    'ANTHROPIC_MODEL', 'ANTHROPIC_DEFAULT_OPUS_MODEL', 'ANTHROPIC_DEFAULT_SONNET_MODEL', 'ANTHROPIC_DEFAULT_HAIKU_MODEL'},
    'gemini-work': {'GOOGLE_GENAI_USE_VERTEXAI', 'GOOGLE_CLOUD_PROJECT', 'GOOGLE_CLOUD_LOCATION', 'GEMINI_MODEL'},
}


class TransferError(ValueError):
    """An allowlisted diagnostic code, never native secret content."""


def provider(profile):
    return 'vertex' if profile in VERTEX_KEYS else 'antigravity' if profile == 'gemini-priv' else profile.split('-')[0]


def credential_path(profile):
    return ('.config/gcloud/application_default_credentials.json' if profile in VERTEX_KEYS else
            '.gemini/antigravity-cli/antigravity-oauth-token' if profile == 'gemini-priv' else
            '.claude/.credentials.json' if profile.startswith('claude-') else
            '.codex/auth.json' if profile.startswith('codex-') else '.vibe/.env')


def directory(path, create=False):
    """Open absolute paths one component at a time, never following links."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise TransferError('unsafe_path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd
    except FileNotFoundError:
        os.close(fd)
        raise TransferError('missing') from None
    except OSError:
        os.close(fd)
        raise TransferError('unsafe_directory') from None


def read_file(root, relative, private=True):
    path = Path(root) / relative
    fd = directory(path.parent)
    try:
        inp = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(inp, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
                raise TransferError('unsafe_source_file')
            if private and before.st_mode & 0o077:
                raise TransferError('source_file_not_private')
            value = stream.read(1048577)
            after = os.fstat(stream.fileno())
        final = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        identity = lambda s: (s.st_ino, s.st_size, s.st_mtime_ns)
        if identity(before) != identity(after) or identity(before) != identity(final):
            raise TransferError('source_changed_during_capture')
        if len(value) > 1048576:
            raise TransferError('source_file_too_large')
        return value
    except FileNotFoundError:
        raise TransferError('missing') from None
    except OSError:
        raise TransferError('unsafe_source_file') from None
    finally:
        os.close(fd)


def object_json(raw):
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError):
        raise TransferError('invalid_native_document') from None
    if not isinstance(result, dict):
        raise TransferError('invalid_native_document')
    return result


def enabled(config):
    path = Path(config)
    data = object_json(read_file(path.parent, path.name, private=False))
    if data.get('version') != 1 or not isinstance(data.get('profiles'), dict) or set(data['profiles']) != set(PROFILES):
        raise TransferError('invalid_environment_selection')
    if any(not isinstance(v, dict) or set(v) != {'enabled'} or type(v['enabled']) is not bool for v in data['profiles'].values()):
        raise TransferError('invalid_environment_selection')
    return [p for p in PROFILES if data['profiles'][p]['enabled']]


def idle(root, profiles):
    """Refuse host-native writers; project-role homes are distinct streams."""
    roots = [str(Path(root) / p) for p in profiles]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            # Container role homes are independent credential streams, not seeds.
            if 'libpod-' in (proc / 'cgroup').read_text():
                continue
            command = (proc / 'cmdline').read_bytes().replace(b'\x00', b' ').decode(errors='replace')
            comm = (proc / 'comm').read_text().strip().lower()
            if not any(x in comm or x in command for x in ['claude', 'codex', 'gemini', 'antigravity', 'vibe', './login', 'gcloud']):
                continue
            cwd = str((proc / 'cwd').resolve())
            # Only HOME/config-directory selectors are inspected; no env dump.
            selectors = []
            for item in (proc / 'environ').read_bytes().split(b'\x00'):
                key, _, value = item.partition(b'=')
                if key in [b'HOME', b'CLAUDE_CONFIG_DIR', b'CODEX_HOME', b'VIBE_HOME', b'GEMINI_CLI_HOME', b'CLOUDSDK_CONFIG']:
                    selectors.append(value.decode(errors='replace'))
            if any(cwd == p or cwd.startswith(p + '/') or p + '/' in command or any(v == p or v.startswith(p + '/') for v in selectors) for p in roots):
                raise TransferError('bootstrap_writer_active')
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            raise TransferError('bootstrap_writer_state_unavailable') from None


def native_credentials(profile, raw):
    kind = provider(profile)
    if kind == 'mistral':
        matches = []
        for line in raw.decode().splitlines():
            match = re.fullmatch(r'\s*(?:export\s+)?MISTRAL_API_KEY\s*=\s*(.*?)\s*', line)
            if match:
                value = match[1]
                if value.startswith('"'):
                    try:
                        value = json.loads(value)
                    except ValueError:
                        raise TransferError('unsupported_mistral_quoting') from None
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9._+/=-]+', value):
                    raise TransferError('invalid_mistral_key_format')
                matches.append(value)
        if len(matches) != 1:
            raise TransferError('missing_or_duplicate_mistral_key')
        return ('MISTRAL_API_KEY=' + json.dumps(matches[0]) + '\n').encode()
    data = object_json(raw)
    if kind == 'vertex':
        valid = data.get('type') == 'authorized_user' and all(isinstance(data.get(k), str) and data[k] for k in ['client_id', 'client_secret', 'refresh_token'])
    elif kind == 'claude':
        token = data.get('claudeAiOauth', {})
        valid = isinstance(token, dict) and any(isinstance(token.get(k), str) and token[k] for k in ['accessToken', 'refreshToken'])
    elif kind == 'codex':
        token = data.get('tokens', {})
        valid = isinstance(token, dict) and any(isinstance(token.get(k), str) and token[k] for k in ['access_token', 'refresh_token']) and not data.get('OPENAI_API_KEY')
    else:
        token = data.get('token', data)
        valid = isinstance(token, dict) and any(isinstance(token.get(k), str) and token[k] for k in ['access_token', 'refresh_token'])
    if not valid:
        raise TransferError('invalid_native_credentials')
    return raw


def installation(profile, root):
    fd = directory(root)
    try:
        metadata = os.fstat(fd)
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            raise TransferError('profile_directory_not_private')
    finally:
        os.close(fd)
    value = object_json(read_file(root, '.native-install.json', private=False))
    if value.get('directory') != profile or value.get('flavour') != profile.split('-')[0]:
        raise TransferError('wrong_installed_profile')
    expected = provider(profile)
    if expected in ['vertex', 'antigravity'] and value.get('provider') != expected:
        raise TransferError('unsupported_installed_provider')
    if expected not in ['vertex', 'antigravity'] and value.get('provider') not in [None, expected]:
        raise TransferError('unsupported_installed_provider')
    return value


def validate_vertex(profile, data):
    if set(data) != VERTEX_KEYS[profile] or any(not isinstance(v, str) or not v for v in data.values()):
        raise TransferError('invalid_vertex_allowlist')
    claude = profile == 'claude-work'
    project = data['ANTHROPIC_VERTEX_PROJECT_ID' if claude else 'GOOGLE_CLOUD_PROJECT']
    location = data['CLOUD_ML_REGION' if claude else 'GOOGLE_CLOUD_LOCATION']
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', project) or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', location):
        raise TransferError('invalid_vertex_configuration')
    if claude:
        models = [data[k] for k in VERTEX_KEYS[profile] if k.startswith('ANTHROPIC_') and k != 'ANTHROPIC_VERTEX_PROJECT_ID']
        valid = data['CLAUDE_CODE_USE_VERTEX'] == '1' and all(re.fullmatch(r'claude-[a-z0-9-]+(?:@[0-9]{8})?', m) for m in models)
    else:
        valid = data['GOOGLE_GENAI_USE_VERTEXAI'] == 'true' and re.fullmatch(r'[A-Za-z0-9_.@-]+', data['GEMINI_MODEL'])
    if not valid:
        raise TransferError('invalid_vertex_configuration')


def companion(profile, root):
    if profile in VERTEX_KEYS:
        raw = read_file(root, '.vertex.json')
        data = object_json(raw)
        validate_vertex(profile, data)
        return [('.vertex.json', raw, sorted(data))]
    if profile == 'claude-priv':
        for relative in ['.claude/.claude.json', '.claude.json']:
            try:
                data = object_json(read_file(root, relative))
                break
            except TransferError as error:
                if str(error) != 'missing':
                    raise
        else:
            return []
        selected = {}
        account = data.get('oauthAccount')
        if account is not None:
            if not isinstance(account, dict):
                raise TransferError('invalid_claude_metadata')
            selected['oauthAccount'] = {k: v for k, v in account.items() if k in OAUTH_METADATA and isinstance(v, str)}
        for key in CLAUDE_METADATA[1:]:
            if key in data and isinstance(data[key], (str, bool)):
                selected[key] = data[key]
        return [('.claude/.claude.json', (json.dumps(selected) + '\n').encode(), sorted(selected))] if selected else []
    return []


def capture(root, config, metadata_only=False):
    selected = enabled(config)
    idle(root, selected)
    entries, report = [], []
    for profile in PROFILES:
        if profile not in selected:
            report.append({'profile': profile, 'status': 'disabled', 'files': []})
            continue
        base = Path(root) / profile
        files = []
        try:
            installation(profile, base)
            path = credential_path(profile)
            if metadata_only:
                # No credential bytes are read by a preflight.
                fd = directory((base / path).parent)
                try:
                    item = os.stat((base / path).name, dir_fd=fd, follow_symlinks=False)
                    if not stat.S_ISREG(item.st_mode):
                        raise TransferError('unsafe_source_file')
                finally:
                    os.close(fd)
                report.append({'profile': profile, 'status': 'present_unverified', 'files': [path]})
                continue
            files.append((path, native_credentials(profile, read_file(base, path)), ['MISTRAL_API_KEY'] if provider(profile) == 'mistral' else []))
            files.extend(companion(profile, base))
            entries.append({'profile': profile, 'provider': provider(profile), 'files': [{'path': p, 'content_b64': base64.b64encode(data).decode(), 'allowlisted_fields': fields} for p, data, fields in files]})
            report.append({'profile': profile, 'status': 'ready', 'files': [p for p, _, _ in files]})
        except FileNotFoundError:
            report.append({'profile': profile, 'status': 'missing', 'files': []})
        except TransferError as error:
            report.append({'profile': profile, 'status': 'missing' if str(error) == 'missing' else 'invalid', 'reason': str(error), 'files': []})
    idle(root, selected)
    return {'version': 1, 'purpose': 'bootstrap', 'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'entries': entries, 'report': report}


def publish(root, relative, raw):
    path = Path(root) / relative
    fd = directory(path.parent, create=True)
    temporary = '.auth-transfer-' + uuid.uuid4().hex
    try:
        try:
            existing = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(existing.st_mode):
                raise TransferError('unsafe_destination_file')
            return False
        except FileNotFoundError:
            pass
        out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(out, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        except FileExistsError:
            raise TransferError('destination_changed_during_restore') from None
        return True
    finally:
        try:
            os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError:
            pass
        os.close(fd)


def restore(root, config, payload):
    if not isinstance(payload, dict) or payload.get('version') != 1 or payload.get('purpose') != 'bootstrap' or not isinstance(payload.get('entries'), list) or not isinstance(payload.get('report', []), list) or len(payload.get('report', [])) > len(PROFILES):
        raise TransferError('invalid_transfer_manifest')
    selected = enabled(config)
    idle(root, selected)
    if len(payload['entries']) > len(PROFILES):
        raise TransferError('invalid_transfer_manifest')
    report = []
    for row in payload.get('report', []):
        if not isinstance(row, dict) or row.get('profile') not in PROFILES or row.get('status') not in ['ready', 'disabled', 'missing', 'invalid']:
            raise TransferError('invalid_report_metadata')
        if row['status'] != 'ready':
            report.append({'profile': row['profile'], 'status': row['status'], 'files': []})
    manifest = []
    seen = set()
    plans = []
    for entry in payload['entries']:
        if not isinstance(entry, dict) or set(entry) != {'profile', 'provider', 'files'} or not isinstance(entry['files'], list) or len(entry['files']) > 2:
            raise TransferError('invalid_transfer_profile')
        profile = entry.get('profile')
        if profile not in PROFILES or profile in seen or entry.get('provider') != provider(profile):
            raise TransferError('invalid_transfer_profile')
        seen.add(profile)
        if profile not in selected:
            report.append({'profile': profile, 'status': 'target_disabled', 'files': []})
            continue
        base = Path(root) / profile
        allowed = {credential_path(profile)} | ({'.vertex.json'} if profile in VERTEX_KEYS else {'.claude/.claude.json'} if profile == 'claude-priv' else set())
        items, paths = [], set()
        for item in entry.get('files', []):
            if not isinstance(item, dict) or set(item) != {'path', 'content_b64', 'allowlisted_fields'} or not isinstance(item['content_b64'], str) or len(item['content_b64']) > 1398104:
                raise TransferError('invalid_transfer_bytes')
            path = item.get('path')
            if path not in allowed or path in paths:
                raise TransferError('invalid_transfer_path')
            paths.add(path)
            try:
                raw = base64.b64decode(item['content_b64'], validate=True)
            except (KeyError, ValueError):
                raise TransferError('invalid_transfer_bytes') from None
            if len(raw) > 1048576:
                raise TransferError('invalid_transfer_bytes')
            fields = []
            if path == credential_path(profile):
                fields = ['MISTRAL_API_KEY'] if provider(profile) == 'mistral' else []
                raw = native_credentials(profile, raw)
            elif path == '.vertex.json':
                value = object_json(raw)
                validate_vertex(profile, value)
                fields = sorted(value)
            elif path == '.claude/.claude.json':
                value = object_json(raw)
                if set(value) - set(CLAUDE_METADATA) or ('oauthAccount' in value and (not isinstance(value['oauthAccount'], dict) or set(value['oauthAccount']) - set(OAUTH_METADATA))):
                    raise TransferError('invalid_claude_metadata')
                if any(not isinstance(v, str) for v in value.get('oauthAccount', {}).values()) or any(type(v) not in (str, bool) for k, v in value.items() if k != 'oauthAccount'):
                    raise TransferError('invalid_claude_metadata')
                fields = sorted(value)
            if not isinstance(item.get('allowlisted_fields'), list) or any(not isinstance(k, str) for k in item['allowlisted_fields']):
                raise TransferError('invalid_manifest_fields')
            if item['allowlisted_fields'] != fields:
                raise TransferError('invalid_manifest_fields')
            items.append((path, raw, fields))
        if credential_path(profile) not in paths or (profile in VERTEX_KEYS and '.vertex.json' not in paths):
            raise TransferError('incomplete_transfer_profile')
        generated = []
        if profile == 'gemini-work':
            generated = [('.gemini/settings.json', b'{"security":{"auth":{"selectedType":"vertex-ai","enforcedType":"vertex-ai"}}}\n', [])]
        elif profile.startswith('codex-'):
            generated = [('.codex/config.toml', b'cli_auth_credentials_store = "file"\ncheck_for_update_on_startup = false\n', [])]
        installation(profile, base)
        # Validate all parents before publishing any secret, including symlinks.
        for path, _, _ in items + generated:
            fd = directory((base / path).parent, create=True)
            try:
                existing = os.stat((base / path).name, dir_fd=fd, follow_symlinks=False)
                if not stat.S_ISREG(existing.st_mode) or existing.st_uid != os.getuid() or existing.st_mode & 0o077:
                    raise TransferError('unsafe_destination_file')
            except FileNotFoundError:
                pass
            finally:
                os.close(fd)
        credential = base / credential_path(profile)
        if credential.exists() or credential.is_symlink():
            if credential.is_symlink() or not credential.is_file():
                raise TransferError('unsafe_destination_file')
            report.append({'profile': profile, 'status': 'skipped_existing', 'files': []})
            continue
        plans.append((profile, base, items, generated))
    # Every manifest and endpoint is validated before publishing any credentials.
    for profile, base, items, generated in plans:
        created = []
        try:
            for path, raw, _ in sorted(items + generated, key=lambda i: i[0] == credential_path(profile)):
                if publish(base, path, raw):
                    created.append(path)
            report.append({'profile': profile, 'status': 'restored', 'files': created, 'model_access': 'unverified'})
            manifest.extend({'profile': profile, 'path': path, 'purpose': 'native_credentials' if path == credential_path(profile) else 'allowlisted_provider_metadata', 'allowlisted_fields': fields} for path, _, fields in items)
        except (TransferError, OSError):
            # Only files created by this transaction are removed; existing state stays.
            for path in reversed(created):
                fd = directory((base / path).parent)
                try:
                    os.unlink((base / path).name, dir_fd=fd)
                finally:
                    os.close(fd)
            raise
    idle(root, selected)
    return {'version': 1, 'purpose': 'bootstrap', 'report': report, 'vault_material_manifest': manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['capture', 'restore'])
    parser.add_argument('--profiles-root', required=True)
    parser.add_argument('--environment-config', required=True)
    parser.add_argument('--metadata-only', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        result = capture(args.profiles_root, args.environment_config, args.metadata_only) if args.action == 'capture' else restore(args.profiles_root, args.environment_config, object_json(sys.stdin.read(16777217)))
        print(json.dumps(result))
        return 0
    except (TransferError, OSError, UnicodeError, TypeError, KeyError):
        print(json.dumps({'error': 'transfer_failed_safely', 'report': []}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
