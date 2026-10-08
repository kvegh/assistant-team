#!/usr/bin/env python3
"""Run existing local quality tools without installing dependencies or connecting targets."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tests-only', action='store_true')
    args = parser.parse_args()
    if not args.tests_only and shutil.which('ansible-playbook') is None:
        parser.error('Ansible must already be installed; this command does not install tools.')
    commands = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q']]
    if not args.tests_only:
        if not os.environ.get('ANSIBLE_VAULT_PASSWORD_FILE'):
            parser.error('Set ANSIBLE_VAULT_PASSWORD_FILE to your external Vault password file.')
        commands.append([sys.executable, '-m', 'ansiblelint', '--offline', '--profile', 'production'])
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
