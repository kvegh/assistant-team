# Reusable session rules and project context

Give a new assistant this file and the repository's `AGENTS.md` before work.
These are the user's agreed working rules and design decisions, not a claim that
every planned capability is implemented. Read `README.md`, `README.TLDR.md`,
`VERSION`, `RELEASE_NOTES.md`, `TODO.md`, and `design_decisions_history.md` for
the current implementation and outstanding work. Resolve discrepancies from
verified code, deployment results, and the user's latest instructions; ask about
material uncertainty rather than inventing history.

## Purpose and collaboration

- Build a reproducible environment for teams using the vendors' native agent
  harnesses: Claude Code, Codex CLI, Gemini CLI or its supported successor, and
  eventually Mistral Vibe. The reference to ChatGPT in early discussions means
  Codex CLI here, not programmatic access to the ChatGPT web chat.
- Actively co-design. Consider risk, practicality, simplicity, productivity,
  security, efficiency, and cost. Offer constructive, objective criticism.
  Avoid getting lost in details or adding architecture without a clear benefit.
- Keep answers short and direct. Answer the actual technical question, especially
  distinctions such as an MCP client versus an inbound MCP server.
- When the user reaches for another language, briefly give the natural English
  equivalent in **bold**, then continue the task. Do not add other highlighting
  for the language explanation. A clear task does not need reformulation.
- Use background subagents for settled implementation work: Ansible,
  configuration, documentation, validation, commits, pushes, and deployments.
  Keep the main conversation available for design and steering. Coordinate shared
  files, Git operations, and VM changes to avoid collisions. Run tasks in parallel
  when they do not overlap or endanger one another; serialize only conflicting
  operations, rather than making independent tasks wait.
- Clearly distinguish a proposal, an agreed decision awaiting implementation,
  an implemented change, a deployed change, and a verified result.
- Continue authorized work and routine reversible fixes without repeatedly asking
  permission. Ask before significant new decisions, purchases, accepting legal
  terms, security bypasses, or destructive actions outside the authorized scope.
  Missing tools require installation permission unless already authorized.
- Inspect asynchronous outcomes through completion. Rely on automatic subagent
  completion notifications rather than fixed 20-second polling. Every ten minutes
  during active work, check unfinished agents for stalls, blockers, deferrals or
  a need to resume; preserve explicit holds and completed work. Share meaningful
  results promptly, and check additionally for user status requests or task-specific
  needs. External
  jobs without notifications still require appropriately spaced outcome checks.
  Give meaningful progress updates and respect explicit stop or pause instructions.

## Approved installation layout: source only until explicitly deployed

The canonical fresh-install root is `PREFIX/ac-agents`, with PREFIX defaulting to
the destination runtime user's real HOME. `--prefix` selects an absolute destination
parent; it never defaults to the controller user's HOME. Code is in
`agent-connector`, the entrypoint is `bin/team`, native account profiles are in
`model-environments`, config is `conf/environment.conf`, and the editable default
is `conf/templates/assistant.prompt.md.template`. Project config lives inside its
project directory as `project.NAME.config`. Guides, archives and environment logs
also belong under the installation root. User systemd units and engine-managed
Podman storage retain their standard locations under the real runtime account.

These layout changes are source-only. Existing deployed environments retain their
old paths and commands until a separately authorized controlled migration or fresh
deployment. New-layout playbooks refuse legacy artifacts and another installation
root bound to the same user systemd namespace. See `INSTALLATION_MIGRATION.md`;
no automatic migration command is claimed or approved by this layout decision.

## Access and secrets

- The repository is private. Privacy does not replace encryption.
- Model authentication data must never enter Git, even encrypted. Provider login
  tokens, refresh tokens, API keys and credential files belong in operator-owned
  runtime storage or a separate secret manager outside the repository. This is
  stricter than the Vault allowance for deployment configuration below.
- Never commit environment-specific sensitive data in plaintext: credentials,
  tokens, usernames, hostnames, addresses, cloud project identifiers, or similar
  deployment values. Use Ansible Vault and generic documentation placeholders.
- The existing Vault password file is external to the repository, originally
  supplied in the operator's working directory. Never commit it or decrypted
  files. Pass the path explicitly for local Ansible; AAP uses its Vault credential.
- Never print authentication material, browser authorization codes, login URLs
  containing secrets, or unfiltered environment/configuration dumps.
- Use SSH for agent-side Git operations. Keep HTTPS links in `.gitmodules` for
  GitHub navigation; use equivalent SSH URLs when fetching submodules.
  AAP project synchronization uses HTTPS with a repository-scoped credential.
- Leave the existing repository token's expiry unchanged and update it on demand.
  Record that decision without storing the token in plaintext.
- Direct SSH with sudo was authorized for the original project VM. This does not
  authorize unrelated hosts, copying users' authentication material, or bypassing
  access controls. Prefer MCP where it supports the required operation, and use
  AAP MCP for controller operations; verify the connection before relying on it.
- Normal deployments use AAP job templates. Previous ad hoc permissions were
  specific exceptions for this demo and particular operations, not a standing
  permission for arbitrary future ad hoc jobs.
- The fresh deployment test VM must be configured through Ansible through AAP,
  including its project, credentials, inventory, and job template. Do not repair
  that test by manually configuring it over SSH.
- New sessions must establish their own authorized access. This file contains
  neither access credentials nor a transferable grant to bypass host-key checks.
- Support operator-run deployment and authentication without the assistant
  accessing credentials. Protect authentication directories and use sanitized
  diagnostic exports when troubleshooting. Do not weaken isolation for convenience.

## Reproducible infrastructure and automation

- Use Ansible where it makes sense, with separate roles called by playbooks.
  Use an obviously suitable certified collection, but do not force a collection
  when it complicates the architecture. The Podman foundation uses the certified
  Red Hat collection. Native CLI, login, and broker application logic may remain
  Python, shell, or other suitable code installed by Ansible.
- Every lasting design/configuration change must be reproducible from committed
  automation. Temporary tests and retries do not each require a design entry.
- Support deployment to remote hosts and to the host running Ansible through
  Ansible's normal connection mechanisms; avoid inventing a separate local engine.
- Apply only relevant Red Hat CoP automation good practices. Use ansible-lint and
  meaningful tests. Evaluate APME's read-only policy checks, including its local
  OPA service, without automatic remediation or external AI fallback.
- All APME scans that leave systems and project code unchanged are authorized;
  do not ask again for each validator or scan. Existing dependency-installation,
  credential-protection, and security-control rules still apply. Assess findings
  against this project's actual security, compliance, stability, and supported
  Ansible version. Implement relevant, justified fixes with appropriate validation;
  do not blindly apply upstream automatic remediation or chase false positives.
- Protect diagnostic output by default. Investigate the actual failed task, make
  a focused fix, validate, and rerun the relevant template or recovery stage.
  Do not repeat successful or destructive provisioning unnecessarily.
- Default fresh VM sizing is 2 vCPUs, 4 GiB allocated RAM, and a 20 GiB cloned
  virtual disk. Grow the guest root partition/filesystem to the available size.
  Do not apply a separate additional 10 GiB expansion to every new deployment.
  Do not shrink the already enlarged original VM.
- Account for normal guest memory reservations when verifying usable RAM.
- Remove inherited AAP installer/service-account clutter from the clone while
  preserving the automation access account. Keep the source golden image intact.
- After first boot, fully update installed packages with DNF, reboot when needed,
  reconnect, and verify no pending updates. A policy warning about `state: latest`
  does not override this explicit full-update requirement.
- Preserve failed resources for investigation; refuse accidental replacement of
  existing guests/disks. Use configuration-only recovery where appropriate.
- Deploy logs must also be available on the target machine. Record sanitized
  deployment, login-result, and service/project lifecycle information. Do not log
  credentials or indiscriminately capture private conversations for diagnostics.

## Agent environment, accounts, and lifecycle

- Use Podman containers with native harnesses, rather than replacement agent loops.
  Keep sessions attachable through tmux. Build and run on the project VM.
- One environment per Linux user is supported today. Multiple environments and
  custom account contexts are optional future work, not current requirements.
- Prepare `work` and `priv` profiles for Claude, Gemini, Codex, and Mistral.
  Claude and Gemini work accounts use Google Vertex; personal accounts use their
  supported individual authentication. Codex work is prepared but disabled for
  the current operator. Mistral work is disabled for now.
- Keep each profile's install, HOME, configuration, cache, temporary files, and
  authentication state inside `<installation>/model-environments/PROFILE`. Do not scatter native
  harness configuration into the user's general home.
- Authenticate each profile once through its host-side `./login` wrapper; do not
  require repetitive interactive login inside every role container.
- Provide `./login --clear` to clear that profile's authentication. Report login
  states as confirmed, saved but unconfirmed, or failed, using the implemented
  terminology and the `[AC-Agents]:` prefix. Give next steps for failure or an
  unconfirmed result. Saved credentials alone do not prove model access.
- Do not fall back automatically to paid API access when a subscription allowance
  is exhausted. Wait for allowance renewal or let the user choose another option.
- Track enabled profiles in `<installation>/conf/environment.conf`; the setup command must list
  enabled profiles and guide authentication. Role account choices are explicit
  per project and must match enabled, supported profiles.
- Keep current instructions compatible with the provider's supported clients.
  Personal Gemini migration to Antigravity is a provider compatibility issue;
  neither installation nor an OAuth callback alone proves usable access.
- Model selection per task is priority work after blockers: balance quality and
  cost using supported harness controls. Do not claim this routing exists yet.

## Projects and communication

- Projects live in `<installation>/projects/<name>/`. Project creation prepares the directory,
  its own SQLite database, `assistant-prompt.md`, and a shared `workspace/`.
- Store the project's authoritative configuration in `<installation>/projects/<name>/project.<name>.config`. Project prompts are independently editable and
  contain that project's goal and role prompts in one human-friendly file.
- Start the entire eight-role team together for a project, with its separate
  database and workspace. Allow different projects to run in parallel.
- Use a systemd user target instance per project, rather than one ambiguous shared
  target. Document start, stop, status, session attach, and the user D-Bus fix.
  A shared master target was not selected.
- Use agents-connector for central persisted communication, MCP access, routing,
  and event-driven wake-up. Avoid timed inbox polling or unsafe terminal-input
  injection as the inter-agent design. Idle listeners should not repeatedly invoke
  a model and burn allowance.
- Address messages to one or more supported recipients. Persist communication
  separately per project; the watch command provides operator visibility.
  Do not confuse outbound MCP tools with a native harness accepting inbound MCP.
- The user steers through the orchestrator session and can follow communication
  with the watch command. Keep the command reference in the installation root's
  `README.md` and a maintained, minimal `README.TLDR.md`.
- Record connector actions in the project's SQLite database for correlation,
  using metadata such as the action, time, and result. Do not store all retrieved
  private content merely because an action occurred. This is a design requirement;
  verify current implementation before claiming it is complete.

## Roles and behavior

| Role | Agreed purpose | Default harness/account |
| --- | --- | --- |
| Orchestrator | Decide between a simple task and discussion plus implementation; coordinate handoffs and stop unproductive discussion | Claude work |
| Builder | Implement and debug | Codex private |
| Investigator | Analyze issues, root causes, and fixes | Claude work |
| Challenger | Debate substantial design questions and relevant alternatives | Gemini work |
| Summarizer | Give high-level progress and provide details on request | Claude work |
| Observer/evaluator | Read communication, assess output quality and role suitability, and identify significant design improvements | Claude work |
| Private connector | Retrieve or update private-context data with limited tools | Claude private |
| Corporate connector | Retrieve or update work-context data with limited tools | Claude work |

- These are defaults, not a statement that every account is authenticated or every
  provider can yet be assigned to any role. Check current routing restrictions.
- Participant prompts should explain the visible roles and collaboration protocol.
  The observer/evaluator is an exception: creators should not be told about it.
  Prompt omission is not proof of technical concealment; verify access boundaries
  before claiming other agents cannot discover it.
- The evaluator should assess useful outcomes rather than suggest changes to meet
  a quota. Recommend design changes only when they materially benefit the project.
- It may tell the orchestrator that discussion is becoming unproductive and ask
  it to stop the discussion. The orchestrator controls the participants.
- The observer reads central communication through its supported read-only path.
  Do not claim automatic refresh or report delivery when the implementation still
  uses explicit commands. Likewise distinguish summarizer capability from an
  automatic orchestration policy that has not been verified.
- Connectors are separate private and corporate roles with limited tools; native
  CLI plugins are acceptable, but configuring a role is not proof that its external
  integrations and restrictions are installed and verified.
- Mistral team integration is deferred until a native adapter is implemented.
  Custom roles are required later; offer the current roles as templates.

## Documentation, Git, and releases

- Use "Document" rather than "Record" for documentation-only commit subjects and
  version summaries. Preserve existing Git history.

- For every lasting change, update relevant READMEs, deployed home guides, and
  `design_decisions_history.md`. Record plain-language behavior, rationale, and
  the implementation commit ID; avoid code patches and invented explanations.
- Commit implementation and relevant README changes together. If its commit ID
  is not known yet, add it in a following documentation commit. Push completed
  work to the private repository. Do not leave reproducibility work uncommitted.
- Keep commits focused by fix or feature. After the initial 0.0.1 baseline, every
  commit increments the tracked version: patch for fixes/docs/history, minor with
  patch reset for features. Use the existing version-bump helper.
- Maintain incremental `RELEASE_NOTES.md` with useful detail between a vague
  overview and an implementation dump. Deploy matching version/build metadata.
- A version commit and a published release are different. When deciding to make
  a release, push its Git tag and publish the release on GitHub. Do not describe
  local-only or unpushed work as released.
- Report what changed, meaningful validation, deployment state, and material
  limitations. Do not label installation, process launch, or saved credentials as
  successful end-to-end operation.

## Starting a new session

1. Read this file, `AGENTS.md`, and the current documentation and TODOs.
2. Inspect Git status, branch, current version, and existing background work.
   Preserve pending work and coordinate before editing or deploying.
3. Check authorized tool connections without disclosing credentials. Consult
   encrypted configuration only as needed; never print its contents.
4. Confirm installed versus verified capabilities before recommending a workflow.
5. Continue the user's task. Reuse the agreed rules; ask only about genuinely
   missing information or a new significant decision.

This file supports consistent future sessions. Rebuilding the software environment
requires the repository's playbooks and operator-owned encrypted configuration;
this rules file alone is not a deployment bundle or authentication backup.

## Operator command usability

- Provide complete `~/team --help` with supported commands, parameters and brief explanations. Help and project listing must not require authentication or start services.
- Unknown commands must explicitly say `Invalid command`; distinguish them from valid commands with missing parameters. Do not silently invent aliases such as `create` for `create-project`.

## Editable project prompt templates

- New templates use `[Project]` and `[Role: Investigator]` style sections for all supported roles, with human display names such as `Private Connector`.
- Lines starting with `#` are comments in the new format. All starter examples and human guidance are commented and excluded from harness input; users add or uncomment their active instructions. Do not activate examples as a fallback.
- Preserve existing project files and legacy `# Role:` interpretation. Reject duplicate, missing or unknown roles before rendering, and preserve private observer isolation.
