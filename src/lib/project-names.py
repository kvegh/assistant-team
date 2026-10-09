"""Shared project-name and real Unix socket-path validation."""
import datetime
import pathlib
import re


def validate(name,home=None):
    if not isinstance(name,str) or len(name)>84:
        raise ValueError('Invalid project name: use a 1-40 character base and valid archive timestamp suffixes')
    remaining=name
    while len(remaining)>40:
        match=re.fullmatch(r'(.+)-([0-9]{10})',remaining)
        if not match:raise ValueError('Long project names require archive timestamp suffixes')
        try:datetime.datetime.strptime(match.group(2),'%d%m%y%H%M')
        except ValueError as error:raise ValueError('Invalid archive timestamp suffix') from error
        remaining=match.group(1)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,39}',remaining):
        raise ValueError('Use lowercase letters/digits, underscores or hyphens; start with a letter/digit')
    if home is not None:
        root=pathlib.Path(home)/'projects'/name
        endpoints=[root/'broker.sock',root/'profiles/corporate-connector/ipc/agent.sock']
        if any(len(str(path).encode('utf-8'))>=108 for path in endpoints):
            raise ValueError('Project name makes a Unix socket path too long; use rename-project to choose a shorter base before archiving, or deploy under a shorter home path')
    return name
