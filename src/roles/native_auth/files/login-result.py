"""Local credential evidence only: never verifies model entitlement."""
import hashlib
import json
import pathlib
import subprocess


def display(message):
    return "[AC-Agents]: " + message


def require_idle(root):
    root=pathlib.Path(root).resolve()
    for process in pathlib.Path('/proc').glob('[0-9]*'):
        try:
            if process.stat().st_uid!=__import__('os').getuid():continue
            command=(process/'cmdline').read_bytes().split(b'\0')
        except OSError:continue
        if any(argument.startswith(str(root/'.install').encode()+b'/') for argument in command):
            raise ValueError('Exit this profile’s existing native CLI/login sessions first; no process or credentials were changed')


def personal_gemini(root, environment):
    environment = dict(environment)
    for key in ['GEMINI_API_KEY','GOOGLE_API_KEY','GOOGLE_GENAI_USE_VERTEXAI','GOOGLE_CLOUD_PROJECT',
                'GOOGLE_CLOUD_LOCATION','GOOGLE_APPLICATION_CREDENTIALS','GOOGLE_GENAI_USE_GCA']:
        environment.pop(key, None)
    path = pathlib.Path(root)/'.gemini/settings.json'
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    settings = json.loads(path.read_text()) if path.exists() else {}
    settings.setdefault('security', {}).setdefault('auth', {})['selectedType'] = 'oauth-personal'
    settings['security']['auth']['enforcedType'] = 'oauth-personal'
    path.write_text(json.dumps(settings, indent=2)+'\n');path.chmod(0o600)
    environment['GEMINI_FORCE_FILE_STORAGE']='true'
    return environment


def credential_snapshot(root, flavour, provider=None):
    root = pathlib.Path(root)
    if provider == 'vertex':
        relative = '.config/gcloud/application_default_credentials.json'
    else:
        relative = {'claude': '.claude/.credentials.json', 'codex': '.codex/auth.json',
                    'gemini': '.gemini/oauth_creds.json', 'vibe': '.vibe/.env'}[flavour]
    try:
        data = (root / relative).read_bytes()
        if flavour == 'vibe' and provider != 'vertex':
            valid = any(line.strip().startswith(b'MISTRAL_API_KEY=') and
                        line.partition(b'=')[2].strip().strip(b'\"\'')
                        for line in data.splitlines())
        else:
            value = json.loads(data)
            if provider == 'vertex':
                valid = value.get('type') == 'authorized_user' and all(
                    value.get(key) for key in ['client_id', 'client_secret', 'refresh_token'])
            elif flavour == 'claude':
                valid = bool(value.get('claudeAiOauth', {}).get('accessToken'))
            elif flavour == 'codex':
                valid = bool(value.get('tokens', {}).get('access_token'))
            else:
                valid = bool(value.get('refresh_token') or value.get('access_token'))
        return hashlib.sha256(data).hexdigest() if valid else None
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def result(exit_code, before, after, interactive=False):
    # Interactive TUI exit zero may simply mean the user quit before logging in.
    if exit_code != 0 or not after or before == after:
        return 'Failed or cancelled'
    return 'Credentials saved; model access unverified'


def clear_profile(root, flavour, provider=None):
    root=pathlib.Path(root).resolve();account=root.name;home=root.parent
    require_idle(root)
    copies=[];projects=[]
    for project in (home/'projects').glob('*'):
        for role in (project/'profiles').glob('*'):
            cfg_path=role/'profile.json'
            if not cfg_path.is_file():continue
            cfg=json.loads(cfg_path.read_text())
            boundary=cfg.get('account_profile',cfg.get('auth_directory',{'claude':'claude-work','gemini':'gemini-work','codex':'codex-priv'}.get(cfg.get('flavour'))))
            boundary={'codex':'codex-priv','gemini':'gemini-work'}.get(boundary,boundary)
            if boundary!=account:continue
            projects.append((project.name,role.name))
            copies.append(role/'accounts'/account/'home' if cfg.get('account_profile') else role/'home')
    for project,role in projects:
        check=subprocess.run(['podman','inspect','--format','{{.State.Running}}','acp-'+project+'-'+role],capture_output=True,text=True)
        if check.returncode==0 and check.stdout.strip()=='true':
            raise ValueError('Credentials were preserved: stop project first with ~/team stop '+project)
    # Validate every destination before mutation, including parent paths and config/env files.
    files=['.claude/.credentials.json','.codex/auth.json','.gemini/oauth_creds.json',
           '.gemini/google_accounts.json','.gemini/mcp-oauth-tokens.json','.gemini/gemini-credentials.json',
           '.config/gcloud/application_default_credentials.json','.model-verification.json']
    for directory in [root,*copies]:
        for relative in files+['.env','.gemini/.env','.vibe/.env','.claude.json','.claude/.claude.json','.gemini/settings.json']:
            file=directory/relative
            for ancestor in [file,*file.parents]:
                if ancestor==home.parent:break
                if ancestor.is_symlink():raise ValueError('Refusing auth/config symlink during clear; credentials were preserved')
        for relative in ['.claude.json','.claude/.claude.json','.gemini/settings.json']:
            file=directory/relative
            if file.exists() and not isinstance(json.loads(file.read_text()),dict):raise ValueError('Invalid config object; credentials were preserved')
    # No native logout call: that could revoke a remote session shared by another local copy.
    for directory in [root,*copies]:
        for relative in files:(directory/relative).unlink(missing_ok=True)
        for relative in ['.env','.gemini/.env','.vibe/.env']:
            file=directory/relative
            if file.exists():
                lines=file.read_text().splitlines(keepends=True)
                secret_keys={'GEMINI_API_KEY','GOOGLE_API_KEY','MISTRAL_API_KEY','ANTHROPIC_API_KEY','CLAUDE_CODE_OAUTH_TOKEN'}
                kept=[line for line in lines if line.strip().removeprefix('export ').partition('=')[0].strip() not in secret_keys]
                file.write_text(''.join(kept));file.chmod(0o600)
        for relative in ['.claude.json','.claude/.claude.json']:
            file=directory/relative
            if file.exists():
                value=json.loads(file.read_text());value.pop('oauthAccount',None)
                file.write_text(json.dumps(value,indent=2)+'\n');file.chmod(0o600)
        if flavour=='gemini' and provider!='vertex':personal_gemini(directory,{})
    return len(copies)
