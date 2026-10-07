#!/usr/bin/env python3
"""Launch native harnesses with only instance-local workspace and home mounts."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def valid_name(value):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", value):
        raise argparse.ArgumentTypeError("Use a lowercase name with letters, digits and hyphens.")
    return value


def initialize(root, name, flavour, role_file, participants_file):
    instance = root / name
    if instance.exists():
        raise ValueError("Instance already exists; choose another name.")
    role = role_file.read_text()
    if not role.strip():
        raise ValueError("Role instructions must not be empty.")
    participants = json.loads(participants_file.read_text())
    if not isinstance(participants, list) or not participants:
        raise ValueError("Provide a nonempty participant roster.")
    roster = []
    for participant in participants:
        if not isinstance(participant, dict) or set(participant) != {"role", "responsibility", "worker_visible"}:
            raise ValueError("Participants require role, responsibility and worker_visible.")
        if not all(isinstance(participant[key], str) and participant[key].strip() for key in ["role", "responsibility"]):
            raise ValueError("Participant roles and responsibilities must be nonempty text.")
        if not isinstance(participant["worker_visible"], bool):
            raise ValueError("worker_visible must be true or false.")
        if participant["worker_visible"]:
            roster.append("- " + participant["role"] + ": " + participant["responsibility"])
    if not roster:
        raise ValueError("Provide at least one worker-visible collaborator.")
    role += "\n\n## Other participants\n" + "\n".join(roster)
    role += "\nThis roster describes responsibilities only. It grants no access to other participants, their data or credentials. Communication tools are not configured.\n"
    instance.mkdir(mode=0o700, parents=True)
    home = instance / "home"
    workspace = instance / "workspace"
    home.mkdir(mode=0o700)
    workspace.mkdir(mode=0o700)
    (instance / "instance.json").write_text(json.dumps({"flavour": flavour}) + "\n")
    (instance / "role.md").write_text(role)
    if flavour == "claude":
        (workspace / "CLAUDE.md").write_text(role)
    elif flavour == "codex":
        (workspace / "AGENTS.md").write_text(role)
    elif flavour == "gemini":
        (workspace / "GEMINI.md").write_text(role)
        gemini = home / ".gemini"
        gemini.mkdir()
        (gemini / "settings.json").write_text(json.dumps({"tools": {"core": ["read_file", "list_directory", "glob", "search_file_content"]}}) + "\n")
    else:
        vibe = home / ".vibe"
        (vibe / "agents").mkdir(parents=True)
        (vibe / "prompts").mkdir()
        (vibe / "prompts" / "instance.md").write_text(role)
        (vibe / "agents" / "instance.toml").write_text(
            'agent_type = "agent"\n'
            'display_name = "Instance role"\n'
            'description = "Operator-defined assistant role."\n'
            'system_prompt_id = "instance"\n'
            'enabled_tools = ["grep", "read_file"]\n'
            '[tools.grep]\npermission = "always"\n'
            '[tools.read_file]\npermission = "always"\n'
        )
        (vibe / "AGENTS.md").write_text(role)
    return instance


def command_for(flavour, mode, arguments):
    # No user-supplied engine flags or permission bypasses are accepted.
    if mode == "help":
        return [flavour if flavour != "claude" else "claude", "--help"]
    if mode == "version":
        return [flavour, "--version"]
    if mode == "login":
        return {"claude": ["claude", "auth", "login"],
                "codex": ["codex", "login", "--device-auth"],
                "vibe": ["vibe", "--agent", "instance"],
                "gemini": ["gemini", "--approval-mode", "default"]}[flavour]
    if mode == "interactive":
        if arguments:
            raise ValueError("Interactive mode does not accept extra flags.")
        return {"claude": ["claude", "--permission-mode", "default"],
                "codex": ["codex", "--sandbox", "read-only", "--ask-for-approval", "untrusted"],
                "vibe": ["vibe", "--agent", "instance"],
                "gemini": ["gemini", "--approval-mode", "default"]}[flavour]
    if not arguments:
        raise ValueError("Provide a prompt for noninteractive mode.")
    prompt = " ".join(arguments)
    if prompt.lstrip().startswith("-"):
        raise ValueError("Prompts must begin with text, not CLI options.")
    return {"claude": ["claude", "--permission-mode", "default", "--tools", "Read,Grep,Glob", "-p", prompt],
            "codex": ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check", prompt],
            "vibe": ["vibe", "--agent", "instance", "--prompt", prompt],
            "gemini": ["gemini", "--approval-mode", "default", "--prompt", prompt]}[flavour]


def podman_command(instance, name, flavour, version, mode, arguments, tty):
    for item in [instance, instance / "home", instance / "workspace"]:
        if item.is_symlink() or not item.is_dir():
            raise ValueError("Instance directories must be real directories.")
    command = ["podman", "run", "--rm", "--name", "assistant-team-" + name,
               "--userns=keep-id:uid=1000,gid=1000", "--user=1000:1000",
               "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
               "--pids-limit=256", "--memory=1g", "--cpus=1", "--network=slirp4netns:allow_host_loopback=false",
               "--tmpfs=/tmp:rw,nosuid,nodev,size=128m", "--tmpfs=/run:rw,nosuid,nodev,size=16m",
               "--volume", str(instance / "home") + ":/home/agent:Z",
               "--volume", str(instance / "workspace") + ":/workspace:Z",
               "--workdir=/workspace", "--env=HOME=/home/agent"]
    if mode in {"interactive", "login"}:
        command.append("-it" if tty else "-i")
    command.append("localhost/assistant-team-" + flavour + ":" + version)
    return command + command_for(flavour, mode, arguments)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init")
    init.add_argument("name", type=valid_name)
    init.add_argument("flavour", choices=["claude", "codex", "vibe", "gemini"])
    init.add_argument("--role-file", type=Path, required=True)
    init.add_argument("--participants-file", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("name", type=valid_name)
    run.add_argument("mode", choices=["interactive", "prompt", "login", "help", "version"])
    run.add_argument("prompt", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as the unprivileged runtime account.")
    root = Path.home() / ".local/share/assistant-team/instances"
    try:
        if args.action == "init":
            initialize(root, args.name, args.flavour, args.role_file, args.participants_file)
            print("Instance initialized; authentication remains operator-controlled.")
            return
        instance = root / args.name
        flavour = json.loads((instance / "instance.json").read_text())["flavour"]
        versions = json.loads(Path("/etc/assistant-team/images.json").read_text())
        if flavour not in versions:
            raise ValueError("Unknown native harness.")
        result = subprocess.run(podman_command(instance, args.name, flavour, versions[flavour],
                                               args.mode, args.prompt, os.isatty(0)))
        raise SystemExit(result.returncode)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
