#!/usr/bin/env python3
"""After the initial release, bump once for every commit, including docs commits."""
import argparse
import pathlib
import re


def next_version(value,feature=False):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',value):raise ValueError('Invalid central VERSION')
    major,minor,patch=map(int,value.split('.'))
    return f'{major}.{minor+1}.0' if feature else f'{major}.{minor}.{patch+1}'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--feature',action='store_true');args=parser.parse_args()
    path=pathlib.Path(__file__).resolve().parents[1]/'VERSION'
    path.write_text(next_version(path.read_text().strip(),args.feature)+'\n')
