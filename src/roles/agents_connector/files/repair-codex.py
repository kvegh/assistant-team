#!/usr/bin/env python3
"""Ansible-only guarded repair of one selected project's failed Codex builder."""
import argparse
import importlib.util
from pathlib import Path

source = Path(__file__).with_name('connector-team.py')
spec = importlib.util.spec_from_file_location('codex_repair_core', source)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--restore-marker', action='store_true')
args = parser.parse_args()
if args.restore_marker:
    core.restore_codex_builder_marker()
else:
    core.repair_failed_codex_builder()
