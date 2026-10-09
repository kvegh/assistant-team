# Future work

## Exploratory

- Consider developing our own Ansible modules and packaging them as a collection
  when repeated project-specific deployment behavior justifies it.

## Priority after bug fixes and blocking features

- [ ] Resolve the live broker-hook connection failure: SELinux currently denies
  a container-domain client connecting to the host gateway's unconfined-domain
  Unix listener. Verify a narrowly scoped existing-policy listener-label solution
  before any production fix; diagnosis is ongoing, not a completed fix.

- [ ] Agree and implement a consistent verb-only CLI scheme: `team create PROJECT`,
  `team list`, `team start/stop/status/watch PROJECT`, `team attach PROJECT ROLE`,
  `team archive PROJECT`, `team unarchive ARCHIVE`, `team rename PROJECT NEW_PROJECT`
  and `team destroy PROJECT`. Keep flags for help/information rather than actions;
  retain `create-project`, `--list` and `list-projects` as compatibility aliases
  during transition. This is a proposal only; current commands remain unchanged.

- [ ] Select the model used by each native harness for the task it receives,
  balancing cost or subscription allowance with outcome quality. Investigate
  supported model-selection controls, task-based recommendations and evaluation
  of actual results. Respect enabled account profiles and available models;
  do not automatically fall back to paid API usage when allowance is exhausted.

## Required later

- [ ] Deploy and accept the source-implemented installation layout on an explicitly
  authorized fresh environment. Source now supports `PREFIX/ac-agents`, destination
  home as default parent, canonical paths and project-local singular configuration.
  The existing environment remains unchanged by explicit instruction. Implement
  and test a controlled migration before migrating any existing installation;
  `INSTALLATION_MIGRATION.md` currently documents its design only. Keep any future
  authentication vault outside the installation and Git.

- [ ] Define a reusable post-deployment acceptance suite with documented test cases
  and a command or AAP verification job to run them after installation. Build on
  the existing native-version and disposable-project checks; cover installed CLI
  commands, service/project lifecycle, shared workspace and project isolation,
  and model-free communication checks. Report clear pass/fail results without
  exposing credentials. Keep provider authentication and inference tests separate
  from ordinary deployment checks and require explicit authorization for model calls.

- [ ] Build native Mistral Vibe support for agents-connector and submit an
  upstream pull request. Implement and verify MCP configuration, native event
  handling and session wake-up so Mistral agents can participate in team roles.

- [ ] Allow users to define additional custom roles for their projects.
  Keep the current roles as the defaults and offer their definitions as templates
  for new roles.

## Optional future features

- [ ] Add custom named account contexts for all supported model harnesses.
  Initially support only `work` and `priv` for Claude, Gemini, Codex and Mistral;
  custom contexts may be added later with isolated configuration and credentials.

- [ ] Support multiple environments within one Linux user's account when needed.
  Give each environment its own configuration, account profiles and projects,
  and isolate its systemd units, container names and communication sockets.
  For now, support one environment per Linux user; do not migrate the current
  directory layout as part of this optional feature request.

- Implement the agents-connector adapter for personal Antigravity, preserving its
  native harness, MCP routing, event-driven wake-up and scoped authentication.
  Installation/login support does not establish team integration.
