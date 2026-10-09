# Installation layout review

This review covers the source-only `PREFIX/ac-agents` layout change. It does not
certify an installed environment or authorize migration/deployment. Existing
installations keep their paths until an explicit operator migration or redeploy.

The canonical paths are `bin/team`, `agent-connector`, `model-environments`,
`projects/NAME/project.NAME.config`, `projects/NAME/assistant-prompt.md`,
`project-archive`, `environment-logs`, `conf/environment.conf` and
`conf/templates/assistant.prompt.md.template`, all relative to the installation
root. Native mutable provider state remains inside its model/context directory.

The audit follows these boundaries:

- Operator deployment forwards an optional absolute target prefix to both
  provisioning and safe-log transfer. An omitted prefix resolves the target
  runtime account home, including local Ansible deployments and AAP execution.
- Runtime discovery uses the installed script location and one path contract,
  rather than the calling shell's home or working directory. Copied native
  launchers receive their own copy of that contract for authentication-clear and
  diagnostic routing.
- Project configuration moves with the project directory. Archive preserves the
  singular config; restore generates its new project-local filename/identity in
  staging; rename reverses its local filename before rolling the directory back.
  User prompts, conversations, artifacts and credentials are not string-rebased.
- Harness mounts use host paths below the selected installation. Container paths
  such as `/home/agent`, `/workspace/shared` and `/opt/connector/bin` remain their
  fixed internal interfaces; the upstream `agents-connector` binary name remains
  unchanged.
- Project-name validation measures actual UTF-8 socket bytes including the prefix
  and `ac-agents` directory. Short valid names can still fail under a long prefix:
  choose a shorter prefix/name, rather than truncate or redirect a socket.
- The real account's systemd user-unit location and D-Bus runtime directory remain
  system interfaces. User-service paths point into the selected installation.
  Podman's engine storage remains managed by Podman, outside this application
  tree; application build contexts and standalone instance state are root-local.
- Generated installation trees are excluded from Git. Model authentication must
  never enter Git, including encrypted Git files. Historical release notes and
  decision entries retain their historical paths; current usage describes the
  new layout.

Synthetic regression checks cover custom-root discovery, every canonical mutable
path, project-local config creation without legacy side effects, deeper socket
limits, actual copied CLI routing, native mutable-path scoping, auth-clear reaching
only matching project copies, active-copy refusal, lifecycle rollback and archive
retention. No remote connection, native model invocation, dependency installation
or real credential access is part of these checks. Production Ansible lint must
also pass before the source release is completed.
