#!/usr/bin/env python3
"""Verify rootless instance isolation using offline commands only."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

loader = importlib.machinery.SourceFileLoader('assistant_instance', '/usr/local/bin/assistant-instance')
spec = importlib.util.spec_from_loader(loader.name, loader)
launcher = importlib.util.module_from_spec(spec)
loader.exec_module(launcher)
versions = json.loads(Path('/etc/assistant-team/images.json').read_text())


def execute(instance, name, flavour, mode, command=None):
    args = launcher.podman_command(instance, name, flavour, versions[flavour], mode, [], False)
    args = ['--network=none' if item.startswith('--network=') else item for item in args]
    if command is not None:
        image_index = args.index('localhost/assistant-team-' + flavour + ':' + versions[flavour])
        args = args[:image_index + 1] + command
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(flavour + ' offline validation failed: ' + result.stderr[-1600:])
    return result.stdout


with tempfile.TemporaryDirectory(prefix='instance-validation-', dir=Path.home() / '.local/share/assistant-team') as temporary:
    root = Path(temporary)
    role = root / 'role.md'
    role.write_text('Read supplied workspace material and summarize it. Request approval before actions.\n')
    roster = root / 'participants.json'
    roster.write_text(json.dumps([
        {'role': 'collaborator', 'responsibility': 'Review summaries.', 'worker_visible': True},
        {'role': 'observer', 'responsibility': 'Evaluate outcomes.', 'worker_visible': False},
    ]))
    for flavour in versions:
        first = launcher.initialize(root / 'instances', 'validation-' + flavour + '-one', flavour, role, roster)
        second = launcher.initialize(root / 'instances', 'validation-' + flavour + '-two', flavour, role, roster)
        assert 'observer' not in (first / 'role.md').read_text()
        actual = execute(first, 'validation-' + flavour + '-one', flavour, 'version')
        assert versions[flavour] in actual
        execute(first, 'validation-' + flavour + '-one', flavour, 'help')
        execute(first, 'validation-' + flavour + '-one', flavour, 'version', [
            'sh', '-c', 'test "$(id -u)" = 1000 && test ! -w /usr && '
            'test -z "$(command -v sudo)" && '
            'grep -Eq "^[^ ]+ / [^ ]+ ro[ ,]" /proc/mounts && '
            'grep -Eq "^NoNewPrivs:[[:space:]]*1$" /proc/self/status && '
            'grep -Eq "^CapEff:[[:space:]]*0000000000000000$" /proc/self/status && '
            'test "$(cat /sys/fs/cgroup/memory.max)" = 1073741824 && '
            'test "$(cat /sys/fs/cgroup/pids.max)" = 256 && '
            'read quota period < /sys/fs/cgroup/cpu.max && test "$quota" -eq "$period" && '
            'printf validation > /home/agent/validation-state && '
            'printf validation > /workspace/validation-workspace'])
        execute(second, 'validation-' + flavour + '-two', flavour, 'version', [
            'sh', '-c', 'test ! -e /home/agent/validation-state && '
            'test ! -e /workspace/validation-workspace'])
        assert (first / 'home/validation-state').read_text() == 'validation'
        assert not (second / 'home/validation-state').exists()
        print(flavour + ': version/help, unprivileged read-only root, isolated persistent home/workspace verified')
