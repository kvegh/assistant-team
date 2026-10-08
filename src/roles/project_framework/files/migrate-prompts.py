#!/usr/bin/env python3
"""Opt-in legacy prompt migration; preserve active prose and protect backups."""
import argparse
import datetime
import importlib.util
import os
import pathlib
import tempfile


def migrate(path, core):
    path=pathlib.Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Prompt migration requires a regular project prompt file')
    original=path.read_text()
    goal,sections,modern=core.prompt_sections(original)
    if modern:return False
    def body(text, role=None):
        lines=[]
        for line in text.splitlines():
            if role and line.strip()=='# '+role.replace('-',' ').title():continue
            if line.strip()=='Rough initial role prompt; refine through design.':line='# '+line
            elif line.lstrip().startswith('#'):line=line.lstrip().lstrip('#').lstrip()
            lines.append(line)
        return '\n'.join(lines).strip()
    output=['[Project]',body(goal),'']
    for role in core.ALL:
        output.extend(['[Role: '+role.replace('-',' ').title()+']',body(sections[role],role),''])
    converted='\n'.join(output)+'\n'
    new_goal,new_sections,_=core.prompt_sections(converted)
    # Non-heading instructions must remain byte-for-byte in their own section.
    pairs=[(goal,new_goal,None)]+[(sections[role],new_sections[role],role) for role in core.ALL]
    for before,after,role in pairs:
        if core.active_prompt_text(body(before,role))!=core.active_prompt_text(after):
            raise ValueError('Migration would alter active project instructions')
    backup=path.with_name(path.name+'.before-bracket-migration-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    fd=os.open(backup,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as file:file.write(original)
    fd,name=tempfile.mkstemp(prefix='.prompt-migration-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as file:file.write(converted)
        os.chmod(name,0o600)
        os.replace(name,path)
    finally:
        pathlib.Path(name).unlink(missing_ok=True)
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prompt_file',type=pathlib.Path)
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('connector_core',pathlib.Path(__file__).with_name('connector-team.py'))
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    changed=migrate(args.prompt_file,core)
    print('Prompt migration changed='+str(changed).lower()+'; active instructions preserved; no sessions restarted.')
