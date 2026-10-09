#!/usr/bin/env python3
"""Ansible-only guarded repair of one selected project's failed Codex builder."""
import importlib.util
from pathlib import Path

source = Path(__file__).with_name('connector-team.py')
spec = importlib.util.spec_from_file_location('codex_repair_core', source)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
core.repair_failed_codex_builder()
