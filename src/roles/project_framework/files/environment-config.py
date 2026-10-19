"""One non-secret environment per Linux user; project assignment is authoritative."""
import importlib.util
import json
import os
import pathlib
import re
import subprocess

ROLES = ['orchestrator','builder','investigator','challenger','summarizer','observer','private-connector','corporate-connector']
PROFILES = {vendor+'-'+context: {'vendor': vendor, 'context': context,
    'auth': 'vertex' if vendor in ['claude','gemini'] and context == 'work' else 'account'}
    for vendor in ['claude','gemini','codex','mistral'] for context in ['work','priv']}
DEFAULTS = dict(zip(ROLES, ['claude-work','codex-priv','claude-work','gemini-work','claude-work','claude-work','claude-priv','claude-work']))


def paths(root):
    source=pathlib.Path(__file__).resolve().with_name('install-paths.py')
    if not source.exists():source=pathlib.Path(__file__).resolve().parents[3]/'lib/install-paths.py'
    spec=importlib.util.spec_from_file_location('installation_paths',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.Paths(root)


def atomic(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    temporary = path.with_name(path.name+'.tmp-'+str(os.getpid()))
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w') as file:
            json.dump(data, file, indent=2);file.write('\n');file.flush();os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def environment(home):
    path = paths(home).environment
    if not path.exists():
        atomic(path, {'version': 1, 'profiles': {name: {'enabled': (paths(home).model(name)/'.native-install.json').is_file()} for name in PROFILES}})
    data = json.loads(path.read_text())
    if set(data) != {'version','profiles'} or data['version'] != 1 or set(data['profiles']) != set(PROFILES):
        raise ValueError('conf/environment.conf must contain version 1 and the eight supported profiles')
    if any(set(value) != {'enabled'} or type(value['enabled']) is not bool for value in data['profiles'].values()):
        raise ValueError('Each environment profile must contain only a boolean enabled field')
    return data


def project_name_validator():
    source=pathlib.Path(__file__).resolve().with_name('project-names.py')
    if not source.exists():source=pathlib.Path(__file__).resolve().parents[3]/'lib/project-names.py'
    spec=importlib.util.spec_from_file_location('project_names',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.validate


def project(home, name, create=False):
    project_name_validator()(name,home)
    path = paths(home).project_config(name)
    env = environment(home)
    if not path.exists():
        enabled = [p for p in PROFILES if env['profiles'][p]['enabled']]
        roles = {}
        for role, default in DEFAULTS.items():
            choices = [p for p in enabled if PROFILES[p]['vendor'] == PROFILES[default]['vendor']]
            roles[role] = default if default in enabled else (None if role.endswith('-connector') else next(iter(choices), None))
        # Preserve a legacy prompt's explicit account decision once, without retaining a second authority.
        prompt = pathlib.Path(home)/'projects'/name/'assistant-prompt.md'
        if prompt.exists():
            text = prompt.read_text(); current = None; output = []
            for line in text.splitlines(keepends=True):
                header = re.fullmatch(r'# Role: ([a-z-]+)\s*',line.strip())
                if header:current=header.group(1)
                match = re.fullmatch(r'Account:\s*(priv|work)\s*',line.strip())
                if match and current in DEFAULTS:
                    roles[current]=PROFILES[DEFAULTS[current]]['vendor']+'-'+match.group(1)
                    continue
                output.append(line)
            if ''.join(output)!=text:prompt.write_text(''.join(output))
        atomic(path, {'version': 1, 'project': name, 'roles': roles})
    data = json.loads(path.read_text())
    if set(data) != {'version','project','roles'} or data['version'] != 1 or data['project'] != name or set(data['roles']) != set(ROLES):
        raise ValueError('Project config requires version 1, matching project name and all eight roles')
    for role, profile in data['roles'].items():
        if profile is not None and profile not in PROFILES:raise ValueError('Unsupported profile assigned to '+role)
    return data


def assignments(home, name):
    env = environment(home);data = project(home,name)
    errors = []
    for role, profile in data['roles'].items():
        if profile is None:errors.append(role+': select an enabled profile')
        elif not env['profiles'][profile]['enabled']:errors.append(role+': '+profile+' is disabled')
        elif role in ['summarizer','observer','private-connector','corporate-connector'] and PROFILES[profile]['vendor']!='claude':errors.append(role+': current restricted role requires Claude')
        elif PROFILES[profile]['vendor'] not in [PROFILES[DEFAULTS[role]]['vendor'],'mistral']:errors.append(role+': current role adapter requires '+PROFILES[DEFAULTS[role]]['vendor']+' or Mistral; choose its enabled work/priv profile')
    if errors:raise ValueError('Edit projects/'+name+'/project.'+name+'.config: '+'; '.join(errors))
    return data['roles']


def saved(home, profile):
    root = paths(home).model(profile)
    helper = root/'.login-result.py'
    if not helper.is_file():return False
    spec = importlib.util.spec_from_file_location('login_evidence',helper)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    definition=PROFILES[profile]
    metadata=root/'.native-install.json'
    provider=json.loads(metadata.read_text()).get('provider',definition['auth']) if metadata.is_file() else definition['auth']
    return bool(module.credential_snapshot(root,'vibe' if definition['vendor']=='mistral' else definition['vendor'],provider))


def setup(home, listing=False):
    env = environment(home)
    if listing:
        for name, definition in PROFILES.items():
            installed=(paths(home).model(name)/'.native-install.json').is_file()
            print(name+' | '+definition['vendor']+' | '+definition['auth']+' | '+('enabled' if env['profiles'][name]['enabled'] else 'disabled')+' | '+('installed' if installed else 'not installed')+' | '+('credentials saved; model access unverified' if saved(home,name) else 'credentials not confirmed'))
        return
    print('Select enabled profiles. Disabled credentials and running projects are preserved.')
    for name in PROFILES:
        current=env['profiles'][name]['enabled']
        answer=input(name+' enable? ['+('Y/n' if current else 'y/N')+'] ').strip().lower()
        if answer not in ['', 'y','yes','n','no']:raise ValueError('Answer yes or no; configuration was not changed')
        if answer:env['profiles'][name]['enabled']=answer in ['y','yes']
    atomic(paths(home).environment,env)
    for name in PROFILES:
        if not env['profiles'][name]['enabled']:continue
        if input('Run native login for '+name+' now? [y/N] ').strip().lower() in ['y','yes']:
            subprocess.run([str(paths(home).model(name)/'login')],check=False)
