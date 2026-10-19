# Future work

## Team source review — review only, not approved fixes

The team reviewed snapshot `12ac41f` (version `0.28.1`). These are reviewer claims
and questions to reassess against current code, not endorsed defects or permission
to implement changes. The review was limited; it was not a complete security audit.
Some findings concern older designs already changed in integrated source. Verify
current source and deployed behavior separately before deciding on any fix.

| # | Review item | Evidence/status to reassess |
| --- | --- | --- |
| 1 | Explicit permissions for generated broker config and token files | Check creation and existing-file permissions: private files `0600`, private directories `0700`; do not rely only on the caller's umask. |
| 2 | Portable deployment omitted the dedicated Codex sandbox role | Fixed in integrated fresh/portable source; verify role ordering and actual deployment before closing. |
| 3 | Unbounded communication history versus transport limits | Examine history reads against the broker's 1 MiB wire limit and MCP response bounds; decide whether bounded reads/pagination are needed. |
| 4 | No automatic CI triggers | Review secret-free hosted tests separately from privileged, explicitly invoked quality/deployment checks. |
| 5 | Reproducible test dependencies and destructive-operation guards | Review declared test tool versions and meaningful negative tests for destructive guard behavior. |
| 6 | Sandbox repair failure recovery and false-success retry | Reviewer reports a mock-verified failure/retry problem; reproduce against current repair code before treating it as confirmed live behavior. |
| 7 | Missing launched marker can silently drop wake requests | Review marker lifecycle, failure reporting and recovery; registration alone does not prove readiness. |
| 8 | Container SELinux label drift | Check whether reuse validates the expected process domain/MCS and handles drift safely. |
| 9 | Provider configuration merges | Review consistency between managed fields and preserved operator settings across vendors; avoid overwriting unrelated settings. |
| 10 | Existing structuredContent arrays | Review normalization and add a relevant regression if needed; the proposed connection to the live MCP failure remains undecided. |
| 11 | Decision log creation and SELinux | The shared decision-log design was removed in favor of private outputs; verify current SUMMARY.md/assessment creation, labels and native writes rather than reinstating the old workflow. |
| 12 | Unbounded observer history and memory | Reassess against the new passive readers, including raw-history growth, batching and memory behavior; older observer findings are not automatically current. |
| 13 | Private versus shared workspace clarity | Review prompts, paths and operator documentation so agents deliver shared artifacts to the actual shared mount and preserve private context. |

Do not carry rejected allegations into the active defect list: the claimed critical
role-name authentication bypass was rejected by the review evidence, and the
file-descriptor leak claim was refuted. Preserve that disposition if later evidence
is reviewed; neither is a currently accepted bug. Claims labelled H1/H2, cold-wake
latency and any proposed alert threshold remain unresolved and require measured
evidence, not assumptions.

Coverage gaps remain in role idempotency, VM retirement, project lifecycle/framework
behavior and the upstream broker source. Review those limits when deciding whether
further assessment is useful. This backlog deliberately contains no raw discussion,
operator identities, deployment addresses, credentials or private repository data.

## Exploratory

- Consider developing our own Ansible modules and packaging them as a collection
  when repeated project-specific deployment behavior justifies it.

## Release acceptance and remaining follow-up

- [ ] Implement and verify `codex-work`: a work account is now available.
  Complete work-profile authentication, deployment and role assignment support,
  then test bounded model access and project stop/start conversation restoration.
  Reuse existing preparation where suitable and preserve work/private separation.
- [x] Verify fresh-project native onboarding after the setup-preparation fix:
  all eight native terminals reached input prompts on the fresh target, with
  no theme/welcome/workspace-trust/managed-hook setup dialog. Installed file hashes
  matched source; the model-free isolation/lifecycle/streaming suite passed.
- [ ] Resolve the separate private-Claude authentication preflight failure found
  during the native restart check. The copied role cache was token-cleared while
  the bootstrap seed's access token was expired. Do not bypass the guard or assume
  the encrypted backup proves current provider access. Normal tool approvals
  remain distinct from onboarding and authentication.

Status reconciled after the initial fresh-deployment and authenticated team test.
Completed checks describe that test run, not current service health or permanent
provider access. No further model calls, deployment or recommended fixes are
performed by this backlog update.

- [x] Publish the consolidated 1.0.0 source/tag/release and complete a fresh
  deployment through AAP using the new installation layout. Preserve the original
  working environment and keep test-resource retirement explicitly scoped.
- [x] Complete selective authentication transfer and same-account recovery, then
  confirm bounded native model access for the six enabled account profiles.
  Authentication material stays outside the code repository; the later operator
  decision permits ciphertext in the private companion secrets repository.
- [x] Verify genuine orchestrator-to-peer broker replies and isolated private
  summarizer/observer outputs during the acceptance project run.
- [ ] Finish acceptance for `project-autotest-1`: verify a corrected challenger
  role identity and accurate reported names/model identifiers. Builder and
  challenger previously reported their model as unknown; do not invent model
  versions or treat a harness name as a project role. Preserve successful
  round-trip evidence and repeat only checks needed to resolve remaining gaps.
- [ ] Confirm final project stop/archive acceptance and preserve the test evidence.
  Final correction and archiving have not been verified; inspect existing state
  before repeating operations.
- [ ] Recheck current target health and authentication validity before resuming
  live acceptance. Previous successful probes do not establish current validity;
  use bounded, explicitly authorized model checks only where needed.
- [ ] After acceptance, reconcile deployed operator guides and version/build
  metadata with the final accepted source. The fresh runtime baseline and later
  authentication recovery updates are distinct; do not claim a new full
  deployment from a focused authentication job.
- [ ] Finalize and publish the existing CLI naming proposal as a decision document
  only. Preserve compatibility and current commands until a scheme is approved;
  do not implement command renaming as part of this follow-up.
- [ ] Finalize and publish the existing plain-language assessment of all 13 team
  review findings, including benefit, risk, effort and suggested decisions.
  Reassess its 1.0.4 source observations against the current accepted release and
  incorporate actual deployment/test evidence. Keep rejected allegations rejected
  and leave recommendations unimplemented pending the user's decision.

## Priority after bug fixes and blocking features

- [ ] Verify private passive summarizer/observer acceptance on the explicitly
  authorized fresh test deployment: native callback readiness, event batching,
  quota/approval handling, private output append and restart recovery. Existing
  home-level environments remain unchanged pending separately approved migration;
  preserve their history and user prompts, which cannot retroactively forget roles.

- [ ] Extend installed communication acceptance beyond the verified idle ask/reply
  roundtrip: test tell-only wake-up, delivery while a native role is busy, recovery
  of queued messages, and approval-blocked delivery. Verify unattended permission
  handling only after its scoped design is approved; do not infer it from a test
  that explicitly approves one reply.

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

- [ ] Recheck broker-hook connectivity on the fresh deployment. The earlier
  listener-label failure was addressed in the gateway repair series; verify the
  current target before describing it as an active failure or claiming acceptance.

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

- [ ] Plan and execute rotation of all environment secrets, including the broadly
  reused Ansible Vault password supplied through `vpf`, deployment credentials,
  repository/controller tokens and model authentication material. Inventory each
  secret's consumers first, replace credentials and rekey every dependent vault,
  update AAP credentials and other consumers, verify access/deployment, then revoke
  superseded credentials. Coordinate the shared vault-password change across all
  dependent projects; do not rotate this environment in isolation and break other
  consumers. Review narrower vault-password scope to reduce shared dependencies.
  Keep plaintext secrets and the Vault password outside Git. Model snapshots
  may enter only the authorized private companion repository as ciphertext.
  This is planned work, not authorization
  to rotate or revoke credentials now.

- [x] Capture the explicitly requested original bootstrap authentication and
  existing deployment definition into the private companion secrets repository.
  Six enabled profiles supplied nine allowlisted native input files; two disabled
  profiles were excluded. Both vaults use the existing external vpf and passed
  exact private decrypt-and-compare checks. Source state was unchanged; no model
  access or freshness claim is implied. Companion implementation: `9058235`.
- [x] Implement automatic missing-only authentication restore from the encrypted
  companion snapshot after deployment, plus a dedicated AAP refresh job after
  source reauthentication. Preserve source provenance and existing runtime
  credentials; reject incomplete restores or captures that remove stored profiles.
  See `docs/AUTH_REPLICATION.md`. The unrelated generic exporter draft remains
  unpublished and is not required by this implementation.

- [x] Deploy and accept the source-implemented installation layout on an explicitly
  authorized fresh environment. Source now supports `PREFIX/ac-agents`, destination
  home as default parent, canonical paths and project-local singular configuration.
  The existing environment remains unchanged by explicit instruction. Implement
  and test a controlled migration before migrating any existing installation;
  `INSTALLATION_MIGRATION.md` currently documents its design only. Keep any future
  authentication vault outside the installation and application Git; ciphertext
  is allowed only in the authorized private companion repository.

- [ ] Define a reusable post-deployment acceptance suite with documented test cases
  and a command or AAP verification job to run them after installation. Build on
  the existing native-version and disposable-project checks; cover installed CLI
  commands, service/project lifecycle, shared workspace and project isolation,
  and model-free communication checks. Report clear pass/fail results without
  exposing credentials. Keep provider authentication and inference tests separate
  from ordinary deployment checks and require explicit authorization for model calls.

- [x] Implement native Mistral Vibe team adapters with separate `mistral-priv`
  and `mistral-work` accounts, MCP configuration, addressed inbox hooks, container
  images and exact native session restoration. Account enablement and authenticated
  model access remain separate operator checks; work credentials are not inferred
  from a private login.
- [ ] Contribute native Mistral launcher/hook support upstream to agents-connector
  where useful. The local integration registers the real Mistral type through
  the existing broker protocol and does not require an upstream fork.

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

- [x] Implement the native personal Antigravity adapter using scoped MCP routing,
  native lifecycle hooks and the existing tmux wake architecture. Acceptance and
  remaining delivery-state limitations are documented in the release history.
