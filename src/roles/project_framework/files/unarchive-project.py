"""Copy a retained project archive to a dated, enabled but stopped project."""
import datetime
import importlib.util
import json
import os
import pathlib
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import urllib.parse


def identity_module():
    spec=importlib.util.spec_from_file_location('project_identity',pathlib.Path(__file__).with_name('project-identity.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def archival_timestamp(framework,archive):
    metadata=archive/framework.ARCHIVE_METADATA
    if metadata.is_symlink():raise ValueError('Archive timestamp must not be a symlink')
    if not metadata.exists():return datetime.datetime.fromtimestamp(archive.stat().st_mtime).astimezone()
    if not metadata.is_file() or metadata.stat().st_size>512:raise ValueError('Archive timestamp metadata is invalid')
    try:
        value=json.loads(metadata.read_text())
        if set(value)!={'version','archived_at','timestamp_basis'} or type(value['version']) is not int or value['version']!=1 or value['timestamp_basis']!='operation_start':
            raise ValueError('Invalid archive timestamp schema')
        when=datetime.datetime.fromisoformat(value['archived_at'])
        if when.tzinfo is None:raise ValueError('Archive timestamp requires timezone')
        return when
    except (ValueError,TypeError,KeyError) as error:raise ValueError('Archive timestamp metadata is invalid') from error


def native_codex_cache_plan(framework,archive):
    ephemeral=set();rewrites={}
    for role in framework.ROLES:
        profile=archive/'profiles'/role;config=profile/'profile.json'
        if config.is_symlink() or not config.is_file():raise ValueError('Archived role config must be a regular file')
        value=json.loads(config.read_text())
        if value.get('flavour')!='codex':continue
        homes=[profile/'home']+[profile/'accounts'/account/'home' for account in ['codex-work','codex-priv']]
        for home in homes:
            if not home.exists():continue
            if home.is_symlink():raise ValueError('Archived native home must not be symlinked')
            ephemeral.update([home/'.codex/tmp/arg0',home/'.codex/app-server-control'])
            updater=home/'.codex/app-server-daemon/daemon-updater.sock'
            if updater.exists() and stat.S_ISSOCK(updater.lstat().st_mode):ephemeral.add(updater)
            current=home/'.codex/packages/app-server-daemon/current'
            if not current.is_symlink():continue
            target=os.readlink(current)
            if not target.startswith('/home/agent/'):continue
            mapped=home/target[len('/home/agent/'):]
            try:resolved=mapped.resolve(strict=True)
            except (OSError,RuntimeError) as error:raise ValueError('Codex daemon cache pointer has no safe retained target') from error
            releases=(home/'.codex/packages/app-server-daemon/releases').resolve()
            if not resolved.is_relative_to(releases) or not resolved.is_relative_to(home.resolve()) or not resolved.is_dir():
                raise ValueError('Codex daemon cache pointer is outside its own retained release cache')
            rewrites[current]=(target,os.path.relpath(resolved,current.parent))
    return ephemeral,rewrites


def validate_archive_tree(archive,ephemeral,rewrites=None):
    """Preserve only relocatable links to existing ordinary in-archive targets."""
    root=archive.resolve();rewrites=rewrites or {}
    for directory,dirs,files in os.walk(archive,followlinks=False):
        dirs[:]=[entry for entry in dirs if pathlib.Path(directory)/entry not in ephemeral]
        for entry in dirs+files:
            path=pathlib.Path(directory)/entry
            if path in ephemeral or path in rewrites:continue
            mode=path.lstat().st_mode
            if stat.S_ISLNK(mode):
                if pathlib.PurePath(os.readlink(path)).is_absolute():
                    raise ValueError('Archive absolute links are not restored; archive was retained')
                try:target=path.resolve(strict=True)
                except (OSError,RuntimeError) as error:
                    raise ValueError('Archive has a dangling or cyclic link; archive was retained') from error
                if not target.is_relative_to(root) or target in ephemeral:
                    raise ValueError('Archive link escapes its retained project or references obsolete runtime state')
                target_mode=target.stat().st_mode
                if not (stat.S_ISREG(target_mode) or stat.S_ISDIR(target_mode)):
                    raise ValueError('Archive link references an unsupported special file')
            elif not (stat.S_ISDIR(mode) or stat.S_ISREG(mode) or stat.S_ISSOCK(mode) and path in ephemeral):
                raise ValueError('Archive contains an unsupported special file')


def restore_plan(framework,archive_name):
    if not isinstance(archive_name,str) or '/' in archive_name or archive_name in ['','.','..']:
        raise ValueError('Use the archive directory name, not a path')
    parent=framework.ACCOUNT_HOME/'project-archive';archive=parent/archive_name
    if framework.ACCOUNT_HOME.is_symlink() or parent.is_symlink() or archive.is_symlink() or not archive.is_dir():
        raise ValueError('Archive must be a directory within the account archive parent')
    configs=list(archive.glob('projects.*.config'))
    if len(configs)!=1 or configs[0].is_symlink() or not configs[0].is_file() or configs[0].stat().st_size>65536:
        raise ValueError('Archive must contain exactly one regular project configuration')
    config=configs[0];match=re.fullmatch(r'projects\.(.+)\.config',config.name)
    old=match.group(1);framework.project_path(old)
    data=json.loads(config.read_text())
    if not isinstance(data,dict) or set(data)!={'version','project','roles'} or data['version']!=1 or data['project']!=old or not isinstance(data['roles'],dict) or set(data['roles'])!=set(framework.ROLES):
        raise ValueError('Archived configuration identity or role assignments are invalid')
    if any(value is not None and (not isinstance(value,str) or value not in framework.settings().PROFILES) for value in data['roles'].values()):
        raise ValueError('Archived role account assignments are unsupported')
    when=archival_timestamp(framework,archive)
    dated=old+'-'+when.strftime('%d%m%y%H%M')
    if archive_name==old:new=dated
    elif re.fullmatch(re.escape(old)+r'-[0-9]{10}',archive_name):
        datetime.datetime.strptime(archive_name[-10:],'%d%m%y%H%M')
        if (archive/framework.ARCHIVE_METADATA).exists() and archive_name!=dated:
            raise ValueError('Archive name and recorded timestamp disagree')
        new=archive_name
    else:raise ValueError('Archive name does not match its embedded project identity')
    destination=framework.project_path(new);new_config=framework.ACCOUNT_HOME/('projects.'+new+'.config')
    if destination.exists() or destination.is_symlink() or new_config.exists() or new_config.is_symlink():
        raise ValueError('Restored project or configuration already exists; archive was retained')
    for required in ['initialized','db.sqlite','assistant-prompt.md']:
        if not (archive/required).is_file() or (archive/required).is_symlink():raise ValueError('Archive lacks required regular project files')
    # Validate a private database snapshot: SQLite may create/update sidecars even
    # for read-only WAL readers, so never open the retained archive database.
    try:
        with tempfile.TemporaryDirectory(prefix='.archive-check-',dir=parent) as temporary:
            database_path=pathlib.Path(temporary)/'db.sqlite'
            for suffix in ['', '-wal', '-shm']:
                source=archive/('db.sqlite'+suffix)
                if source.exists():
                    if source.is_symlink() or not source.is_file():raise ValueError('Archive database sidecars must be regular files')
                    target=pathlib.Path(temporary)/source.name;shutil.copyfile(source,target);target.chmod(0o600)
            database='file:'+urllib.parse.quote(str(database_path))+'?mode=ro'
            with sqlite3.connect(database,uri=True) as db:
                if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Archive database integrity check failed')
                tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'agents','messages','asks','replies'}<=tables:raise ValueError('Archive broker database schema is incomplete')
    except sqlite3.DatabaseError as error:raise ValueError('Archive broker database is invalid; nothing was restored') from error
    ephemeral={archive/'broker.sock'}|{archive/'profiles'/role/'ipc/agent.sock' for role in framework.ROLES}
    native_ephemeral,rewrites=native_codex_cache_plan(framework,archive)
    ephemeral|=native_ephemeral
    validate_archive_tree(archive,ephemeral,rewrites)
    identity_module().rendered_paths(framework,archive)
    if framework.loaded_project_units(new):raise ValueError('Restored name already has loaded systemd instances')
    if any(framework.project_container_state(new,role) is not None for role in framework.ROLES):
        raise ValueError('Restored name already has project containers')
    target=framework.project_units(new)[0]
    state=subprocess.run(['systemctl','--user','is-enabled',target],env=framework.user_env(),capture_output=True,text=True)
    if state.stdout.strip() not in ['disabled','not-found',''] or state.returncode not in [1,4]:
        raise ValueError('Restored target is already enabled or its state cannot be established')
    return archive,config,old,new,destination,new_config,ephemeral,rewrites


def restore(framework,archive_name):
    archive,embedded,old,new,destination,new_config,ephemeral,rewrites=restore_plan(framework,archive_name)
    framework.PROJECTS.mkdir(mode=0o700,exist_ok=True)
    staging=pathlib.Path(tempfile.mkdtemp(prefix='.unarchive-',dir=framework.PROJECTS))
    copied=staging/'project';published=False;config_created=False;enable_attempted=False
    target=framework.project_units(new)[0]
    try:
        def ignore(directory,names):
            return [name for name in names if pathlib.Path(directory)/name in ephemeral]
        shutil.copytree(archive,copied,symlinks=True,ignore=ignore)
        for source,(original,link_target) in rewrites.items():
            link=copied/source.relative_to(archive)
            if not link.is_symlink() or os.readlink(link)!=original:
                raise ValueError('Codex cache pointer changed during restoration; archive was retained')
            link.unlink();link.symlink_to(link_target)
        validate_archive_tree(copied,set())
        copied.chmod(0o700)
        (copied/framework.ARCHIVE_METADATA).unlink(missing_ok=True)
        (copied/embedded.name).unlink()
        for role in framework.ROLES:(copied/'profiles'/role/'launched').unlink(missing_ok=True)
        # Destination metadata is generated structurally, never by replacing
        # substrings in user prompts, workspaces, credentials or conversations.
        data=json.loads(embedded.read_text());data['project']=new
        descriptor=os.open(new_config,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        config_created=True
        with os.fdopen(descriptor,'w') as file:json.dump(data,file,indent=2);file.write('\n')
        if destination.exists() or destination.is_symlink():raise ValueError('Restore destination appeared during copying')
        copied.rename(destination);published=True
        identity_module().rebase(framework,new,old_name=old)
        enable_attempted=True
        subprocess.run(['systemctl','--user','enable',target],env=framework.user_env(),check=True,capture_output=True,text=True)
        enabled=subprocess.run(['systemctl','--user','is-enabled',target],env=framework.user_env(),capture_output=True,text=True)
        if enabled.returncode!=0 or enabled.stdout.strip()!='enabled':raise ValueError('Restored target enablement was not confirmed')
        if framework.loaded_project_units(new):
            state=framework.service_state(target)
            if state['ActiveState'] not in ['inactive']:raise ValueError('Restored target unexpectedly became active')
    except Exception as error:
        rollback=[]
        if enable_attempted:
            result=subprocess.run(['systemctl','--user','disable',target],env=framework.user_env(),capture_output=True,text=True)
            if result.returncode:rollback.append('target enablement')
        for operation,needed in [(lambda:shutil.rmtree(destination),published),(lambda:new_config.unlink(),config_created)]:
            if needed:
                try:operation()
                except OSError:rollback.append('restored files')
        if rollback:raise ValueError('Restore failed and rollback was incomplete; archive is retained; inspect the named destination and target') from error
        raise
    finally:shutil.rmtree(staging)
    print('Restored project '+new+'; target enabled but stopped. Archive retained unchanged: '+archive_name+'.')
    return new
