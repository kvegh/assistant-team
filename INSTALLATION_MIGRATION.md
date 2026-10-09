# Installation layout and controlled migration

The new source layout installs under `PREFIX/ac-agents`. `--prefix` names its parent;
when omitted, Ansible resolves the destination runtime user's real home. This source
change has not been deployed to the existing environment. Its current commands,
projects and authentication continue to use the previous layout.

Fresh installation uses the committed playbooks. The new layout is:

```text
PREFIX/ac-agents/
  bin/team
  agent-connector/
  model-environments/<profile>/
  projects/<name>/project.<name>.config
  projects/<name>/assistant-prompt.md
  project-archive/
  environment-logs/
  conf/environment.conf
  conf/templates/assistant.prompt.md.template
  README.md
  README.TLDR.md
```

Systemd user units remain in the real user's standard systemd configuration directory;
Podman's engine-owned storage also remains in its normal location. Units refer to this
installation's paths. The model profiles retain their own HOME, configuration, cache,
installation and credential boundaries. Add the installation's `bin` directory to PATH
if desired, or invoke its complete path; no extra home-directory wrapper is needed.

## Existing installations

There is no unattended migration and no migration command is supplied by this change.
The deployment guard refuses known previous-layout installations before creating a
second environment or replacing their service definitions. Use a fresh destination
user for a fresh installation; existing environments require an explicitly reviewed
migration procedure. Changing `--prefix` is not an authorization to copy credentials.

A future controlled migration should follow this design:

1. Inspect a non-secret manifest of source/destination paths, ownership, supported
   layouts, unit names and collisions. Refuse unsafe links and unsupported layouts.
   Explain all proposed moves before stopping anything.
2. The operator makes a protected backup and retains rollback access. Credentials
   and private project content stay on the operator's machine, outside Git and
   sanitized diagnostics. Encrypt any portable backup that contains secrets.
3. Explicitly stop the selected installation and verify its services and containers
   are quiescent. Preserve unrelated users, installations and systemd units.
4. Stage the complete installation privately. Move model environments without
   exposing authentication; convert environment and project configuration through
   schema-aware operations. Keep project database history and user-authored text
   unchanged. Rebase only generated paths/instructions and remove known transient
   process bookkeeping. Preserve archived originals and their identities.
5. Validate permissions, schema versions, real Unix socket path limits, profile
   isolation and generated unit references without model calls. Publish atomically
   where the filesystem permits. Replace only this installation's unit definitions
   and preserve the operator's previous enablement choices; leave teams stopped.
6. Perform explicit post-migration acceptance checks. Roll back files and exact unit
   definitions on failure. The operator decides when to start teams and when the
   protected old installation can be removed.

Provider authentication compatibility and private-backup retention are operator
choices. Neither a model login nor a credential copy should be triggered implicitly
by deployment or migration. The proposed migration must be implemented and tested
before it can be used; these steps are a design, not executable migration instructions.
