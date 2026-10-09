"""Transactional project rename; preserve user content and native authentication."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


def identity_helper(framework):
    source=Path(framework.__file__).with_name('project-identity.py')
    spec=importlib.util.spec_from_file_location('rename_project_identity',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def rename_paths(framework,old,new):
    if old==new:raise ValueError('Choose a different project name')
    path,config,_=framework.lifecycle_paths(old)
    destination=framework.project_path(new)
    new_config=framework.paths(framework.ACCOUNT_HOME).project_config(new)
    if destination.exists() or destination.is_symlink() or new_config.exists() or new_config.is_symlink():
        raise ValueError('New project or configuration already exists; old project was not stopped')
    if framework.loaded_project_units(new):
        raise ValueError('New project has loaded systemd instances; old project was not stopped')
    if any(framework.project_container_state(new,role) is not None for role in framework.ROLES):
        raise ValueError('New project has existing containers; old project was not stopped')
    data=json.loads(config.read_text())
    if (not isinstance(data,dict) or set(data)!={'version','project','roles'} or data['version']!=1 or data['project']!=old
        or not isinstance(data['roles'],dict) or set(data['roles'])!=set(framework.ROLES)
        or any(value is not None and not isinstance(value,str) for value in data['roles'].values())):
        raise ValueError('Old project configuration has invalid identity; old project was not stopped')
    for endpoint in [destination/'broker.sock']+[destination/'profiles'/role/'ipc/agent.sock' for role in framework.ROLES]:
        if len(os.fsencode(endpoint))>=108:
            raise ValueError('New project socket path is too long; choose a shorter project name')
    return path,config,destination,new_config


def enable_target(framework,name,mode):
    if mode not in ['enabled','enabled-runtime']:return
    args=['systemctl','--user','enable']
    if mode=='enabled-runtime':args.append('--runtime')
    subprocess.run(args+['assistant-connector@'+name+'.target'],env=framework.user_env(),check=True,
                   stdout=subprocess.DEVNULL)


def rename_project(framework,old,new):
    path,config,destination,new_config=rename_paths(framework,old,new)
    helper=identity_helper(framework)
    rendered=helper.snapshot_rendered(framework,path)
    original=config.read_bytes();config_mode=stat.S_IMODE(config.stat().st_mode)
    target='assistant-connector@'+old+'.target'
    enabled=framework.service_state(target).get('UnitFileState')
    moved_project=False;moved_config=False;new_enable_attempted=False;stash=None;ephemerals=[]
    try:
        framework.quiesce_project(old,path);framework.forget_project_units(old)
        rename_paths(framework,old,new)
        path.rename(destination);moved_project=True
        (destination/config.name).rename(new_config);moved_config=True
        helper.rebase(framework,new,old_name=old)
        # Stash only obsolete process bookkeeping, never native authentication or history.
        candidates=[destination/'broker.sock']
        for role in framework.ROLES:
            candidates.extend([destination/'profiles'/role/'ipc/agent.sock',destination/'profiles'/role/'launched'])
        for candidate in candidates:
            if candidate.is_symlink():raise ValueError('Runtime bookkeeping must not be symlinked')
            if candidate.exists():
                if stash is None:stash=Path(tempfile.mkdtemp(prefix='.rename-state-',dir=destination))
                saved=stash/str(len(ephemerals));candidate.rename(saved);ephemerals.append((candidate,saved))
        new_enable_attempted=enabled in ['enabled','enabled-runtime']
        enable_target(framework,new,enabled)
        if stash is not None:shutil.rmtree(stash);stash=None
    except (Exception,KeyboardInterrupt) as error:
        failures=[]
        if new_enable_attempted:
            args=['systemctl','--user','disable']
            if enabled=='enabled-runtime':args.append('--runtime')
            try:
                subprocess.run(args+['assistant-connector@'+new+'.target'],env=framework.user_env(),check=True,
                               stdout=subprocess.DEVNULL)
                framework.forget_project_units(new)
            except (OSError,ValueError,subprocess.CalledProcessError):failures.append(True)
        for candidate,saved in reversed(ephemerals):
            if saved.exists():
                try:saved.rename(candidate)
                except OSError:failures.append(True)
        if stash is not None:
            try:stash.rmdir()
            except OSError:failures.append(True)
        if moved_config:
            try:
                rollback_config=destination/config.name
                if rollback_config.exists() or rollback_config.is_symlink():raise ValueError('Old config path was recreated during rename')
                new_config.rename(rollback_config)
                with rollback_config.open('wb') as file:
                    file.write(original);os.fchmod(file.fileno(),config_mode)
            except (OSError,ValueError):failures.append(True)
        if moved_project:
            try:
                if path.exists() or path.is_symlink():raise ValueError('Old project path was recreated during rename')
                destination.rename(path);helper.restore_rendered(rendered)
            except (OSError,ValueError):failures.append(True)
        try:enable_target(framework,old,enabled)
        except (OSError,subprocess.CalledProcessError):failures.append(True)
        if failures:
            raise ValueError('Rename failed and rollback was incomplete; inspect retained old/new project paths before retrying') from error
        if not isinstance(error,(OSError,ValueError,subprocess.CalledProcessError)):
            raise ValueError('Rename interrupted or rendering failed; old project identity was restored and remains stopped') from error
        raise
    print('Renamed project '+old+' to '+new+'; it remains stopped. Start with: team start '+new)
