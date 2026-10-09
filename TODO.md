# Future work

## Exploratory

- Consider developing our own Ansible modules and packaging them as a collection
  when repeated project-specific deployment behavior justifies it.

## Priority after bug fixes and blocking features

- [ ] Select the model used by each native harness for the task it receives,
  balancing cost or subscription allowance with outcome quality. Investigate
  supported model-selection controls, task-based recommendations and evaluation
  of actual results. Respect enabled account profiles and available models;
  do not automatically fall back to paid API usage when allowance is exhausted.

## Required later

- [ ] Consolidate the installation layout under `PREFIX/ac-agents`, with
  `--prefix` defaulting to the installing user's home directory. Put the `team`
  executable in `bin/`, connector code in `agent-connector/`, native account
  profiles in `model-environments/`, and projects, project archives and environment
  logs in their own subdirectories. Keep environment configuration at
  `conf/environment.conf`, the default prompt template at
  `conf/templates/assistant.prompt.md.template`, and each project's configuration
  alongside its prompt at `projects/NAME/project.NAME.config` (singular `project`).
  Centralize path definitions and review Ansible, runtime/authentication helpers,
  systemd references, lifecycle commands, tests and operator documentation.
  Provide fresh-install support and a controlled existing-installation migration
  preserving projects, archives and credentials. Keep user units in systemd's
  standard configuration directory and the future authentication vault outside
  the installation and Git. Deferred: do not change the current layout yet.

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
