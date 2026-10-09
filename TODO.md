# Future work

## Exploratory

- Consider developing our own Ansible modules and packaging them as a collection
  when repeated project-specific deployment behavior justifies it.

## Priority after bug fixes and blocking features

- [ ] **Review and decide communication architecture; no migration agreed.**
  Continue developing and verifying the current agents-connector + tmux route
  while evaluating these alternatives:

  | Option | Existing value | Additional work and limitations |
  | --- | --- | --- |
  | Current agents-connector + tmux | Durable project SQLite messages, addressed inboxes, questions/replies, native terminals and existing deployment | Complete onboarding, MCP compatibility, automatic wake/reply verification and approval handling; terminal interaction remains fragile. |
  | acpx + a replacement coordinator | Structured ACP input/output, persistent per-agent sessions, prompt queues and cancellation | Build central messaging, recipient routing, access filtering, private observer delivery, correlation and delivery recovery; acpx session history is not a project message bus. Highest development effort. |
  | agents-connector + acpx | Preserve broker persistence, inbox tools and question/reply correlation; replace terminal nudges with structured agent delivery | Build a host dispatcher with per-role queues, durable cursors/backlog recovery and approval handling. Medium development effort; not a drop-in terminal adapter. |

  **Recommendation:** finish bounded acceptance of the current route first:
  addressed messages and replies, idle/busy recipients, restart recovery and
  project isolation. If delivery remains unreliable, trial the combination with
  two roles before deciding on a broader migration. Prior investment alone does
  not establish reliability; measured behavior should guide the decision.

  Broker findings: one recipient or broadcast; selected multiple recipients need
  separate sends. Its live stream has no durable replay or processing ACK, so a
  dispatcher must recover from SQLite backlog. Keep the raw stream host-only and
  preserve worker filtering and the hidden observer's private route. Connector
  action auditing remains required in every option. Stock wake can be disabled
  without patching the broker; do not run competing terminal and ACP delivery.

  acpx mediates structured tool approvals, but does not supply a complete remote
  approval interface. CLI headless escalation denies/cancels the current request;
  an embedded host callback can connect to an operator decision interface.
  Antigravity fixed-choice questions remain unsupported by acpx and its ACP
  runtime uses separate installation/sign-in. Verify native harness behavior,
  existing subscription/Vertex authentication, session continuity and Podman
  isolation before accepting a migration; never silently switch to paid APIs.
  Workflows are experimental and do not automatically implement our team inboxes.

  References: [acpx sessions](https://acpx.sh/sessions.html),
  [permissions](https://acpx.sh/permissions.html),
  [workflows](https://acpx.sh/flows.html),
  [Antigravity integration](https://github.com/openclaw/acpx/blob/main/agents/Antigravity.md),
  [reviewed broker implementation](https://github.com/Aldenysq/agents-connector/tree/44c195a6ed9e4df608d9fde30e3d8759fc92b900/src).

- [ ] **On hold while completing native introductions:** resolve startup/communication permission blocking with operator-controlled
  per-project/role native policy generated before launch, distinct readiness and
  waiting-approval states, and private out-of-model approval notifications with
  sanitized SQLite correlation. See `docs/PERMISSION_MANAGEMENT.md`. Keep tmux
  attach as the initial explicit decision path; no blind Enter or timeout approval.
  Structured cross-harness approval transport remains a separate design decision.

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

- [ ] **On hold, but priority when resumed:** select the model used by each native harness for the task it receives,
  balancing cost or subscription allowance with outcome quality. Investigate
  supported model-selection controls, task-based recommendations and evaluation
  of actual results. Respect enabled account profiles and available models;
  do not automatically fall back to paid API usage when allowance is exhausted.

## Required later

- [ ] **On hold:** external model-authentication vault and save/restore automation.
  Analysis and the exact provider-file manifest are documented in
  `docs/AUTH_REPLICATION.md`, including pushed-code references for resuming later.
  No secret export or vault has been created. Keep `agent-secret-vault.yml` and
  its backups outside Git, preserve bootstrap and project-role stream identities,
  require consistent capture, and never overwrite refreshed runtime credentials
  with an older seed. Resume only when requested by the user.

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
