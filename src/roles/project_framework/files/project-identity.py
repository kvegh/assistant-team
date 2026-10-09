"""Rebase generated project identity without rewriting user or provider content."""
import json
import pathlib


def rendered_paths(framework,path):
    paths=[]
    for role in framework.ROLES:
        profile=path/'profiles'/role
        definition=profile/'profile.json'
        if definition.is_symlink() or not definition.is_file():
            raise ValueError('Role metadata must be a regular file')
        value=json.loads(definition.read_text())
        account=value.get('account_profile')
        if account is not None and account not in framework.settings().PROFILES:
            raise ValueError('Unsupported archived role account profile')
        workspace=profile/'accounts'/account/'workspace' if account else profile/'workspace'
        if any(p.is_symlink() for p in [workspace,*workspace.parents] if p==path or path in p.parents):
            raise ValueError('Generated role paths must not traverse symlinks')
        for filename in ['CLAUDE.md','AGENTS.md','GEMINI.md']:
            target=workspace/filename
            if target.is_symlink() or target.exists() and not target.is_file():
                raise ValueError('Generated instruction files must be regular files')
            paths.append(target)
    return paths


def snapshot_rendered(framework,path):
    return [(p,p.read_bytes() if p.exists() else None,p.stat().st_mode & 0o777 if p.exists() else None)
            for p in rendered_paths(framework,path)]


def restore_rendered(records):
    for path,content,mode in records:
        if content is None:path.unlink(missing_ok=True)
        else:path.write_bytes(content);path.chmod(mode)


def rebase(framework,name,old_name=None):
    config=framework.ACCOUNT_HOME/('projects.'+name+'.config')
    if config.is_symlink() or not config.is_file():raise ValueError('Restored configuration must be regular')
    data=json.loads(config.read_text())
    if not isinstance(data,dict) or set(data)!={'version','project','roles'} or data['version']!=1 or data['project'] not in [name,old_name] or not isinstance(data['roles'],dict) or set(data['roles'])!=set(framework.ROLES):
        raise ValueError('Restored project configuration has invalid identity or role assignments')
    if any(v is not None and (not isinstance(v,str) or v not in framework.settings().PROFILES) for v in data['roles'].values()):
        raise ValueError('Unsupported restored role account assignment')
    data['project']=name
    framework.settings().atomic(config,data)
    rendered_paths(framework,framework.project_path(name))
    framework.load(name).apply_prompts()
    # The stock broker stores agent identities and conversation history, not a
    # project session column. Its --session value is supplied by the new systemd
    # instance at startup; native MCP configuration uses stable container paths.
