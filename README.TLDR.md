# Assistant team: commands

Code is public; encrypted configuration and authentication snapshots remain in
the private `assistant-team-secrets` companion repository.

Release 1.0.0 consolidates the current source; fresh deployment and native team acceptance are verified separately.

Communication stays on agents-connector + tmux; alternatives await review and
decision in [TODO](TODO.md).

Fresh installs use PREFIX/ac-agents. Existing home-level installations require a separately approved migration; see [migration prerequisites](INSTALLATION_MIGRATION.md).
New projects have their own shared workspace, eight role homes/workspaces and
eight containers when started. Claude/Gemini CLI setup defaults are prepared in
those isolated homes; Codex trusts only its three verified generated broker hooks.
Authentication and normal tool approvals remain separate.
Existing explicit distrust is preserved.

Version 1.4.5 removes old deployment/recovery Vault files from branch and tag
history. Configuration stays in the private companion repository. Replace or
scrub older clones before pushing; do not merge their previous history.

## Private passive readers

Team: orchestrator + builder/investigator/challenger. Summarizer/observer
privately read raw communication, never join or answer the team, and produce
operator-only SUMMARY.md/ASSESSMENT.log outside the shared workspace. Event-driven
host dispatch; no timed model polling. Claude profiles supported initially.
Existing sessions remain unchanged. Native reader acceptance must be verified after deployment.
The superseded DECISIONS.log remains empty after its SELinux access failure.

Read the private output:

```sh
tail -f ~/ac-agents/projects/NAME/operator-reports/SUMMARY.md
tail -f ~/ac-agents/projects/NAME/operator-reports/ASSESSMENT.log
```

Run as the runtime user. One environment per user; credentials stay local.

`PROJECT` always means the project name. Each project has one team; its roles are
participants in that team, not separate projects. `ROLE` selects a participant
(such as `orchestrator` or `builder`); `ARCHIVE` selects a retained archive directory.

```sh
~/ac-agents/bin/team --help             # every command, parameters and brief explanation
~/ac-agents/bin/team version            # installed source version/build
~/ac-agents/bin/team setup --list       # enabled / installed / credentials saved (not model verification)
~/ac-agents/bin/team setup             # choose profiles, then optional native login
cd ~/ac-agents/model-environments/PROFILE; ./login     # PROFILE: claude-work/priv, gemini-work/priv,
                         # codex-work/priv, mistral-work/priv (each full name)
./login --clear           # only current profile; exit CLI and stop using projects first
~/ac-agents/bin/team --list            # project names + status; alias: list-projects
~/ac-agents/bin/team create-project example
vi ~/ac-agents/projects/example/project.example.config                      # role -> enabled profile
vi ~/ac-agents/projects/example/assistant-prompt.md          # fill [Project] and [Role: Name]; # lines are comments
~/ac-agents/bin/team start example
~/ac-agents/bin/team attach example orchestrator                 # give task; Ctrl-B D detaches
~/ac-agents/bin/team watch example -f                            # live messages; Ctrl-C viewer only
~/ac-agents/bin/team status example
~/ac-agents/bin/team stop example
~/ac-agents/bin/team restart example
~/ac-agents/bin/team diagnostics --export /private/metadata.tar.gz # safe environment metadata
~/ac-agents/bin/team apply-prompts example                       # effective next launch
```

Stop/start resumes each role's exact saved native conversation for its assigned
account; history, credentials, workspace and database persist. No new task prompt
is submitted. Missing or ambiguous history fails clearly; no newest-session guess.
In-flight tools/process memory are not checkpointed. Expired auth and native
approvals still require attention.

Finish a project with one of these alternatives:
`~/ac-agents/bin/team archive PROJECT` stops it if running and moves its full contents/config to
`~/ac-agents/project-archive/PROJECT-ddmmyyhhmm` (local 24-hour time); `~/ac-agents/bin/team destroy PROJECT` stops it if running and deletes it.
Both remove only its containers; account profiles and other projects stay intact.
Archive refuses same-minute or exact-name collisions before stopping. Rename the
project if an exact-name archive already exists. Named instances are disabled,
reset and forgotten; shared templates remain. Do not run same-project start/edit
operations concurrently.

List status describes services: running, starting, stopping, stopped, failed,
partial (orphan components) or unknown (metadata unavailable); it does not verify model access.

Artifacts: `~/ac-agents/projects/example/workspace` (`/workspace/shared` in containers).
Vertex work profiles require the scoped Cloud SDK (operator-selected during deployment); private Gemini uses scoped Antigravity (`cd ~/ac-agents/model-environments/gemini-priv; ./login`, then `./agy`). Select gemini-priv for native Antigravity; native consent and model entitlement must be verified.
Native SSH/container auth uses local file permissions, not encryption at rest.
Mistral Vibe supports enabled `mistral-work` and `mistral-priv` assignments for
orchestrator, builder, investigator and challenger. Stop before editing the project
role mapping; private readers and restricted connectors require Claude. Login and
model entitlement remain separate checks; no default assignments change.
Login reports failed/cancelled or credentials saved/model access unverified; no automatic inference.
All eight role sessions start only after enabled assignments and saved auth pass; connectors lack service tools, private readers receive event-driven raw discussion. Details: `~/ac-agents/README.md`.

## Disposable deployment test lifecycle

`src/retire_test_linux_vm.yml` performs a read-only preflight by default using its separate encrypted retirement definition. Its dedicated normal AAP template removes the selected second test clone only when explicitly launched with `retire_test_execute: true`. The role verifies exclusive disk ownership, refuses source-image or shared disks, uses graceful shutdown, and checks preservation of all other domains and the golden image. The fresh deployment definition selects the next test clone with an empty recovery address; configuration-only recovery remains available after successful provisioning. No provider credentials are copied or model inference performed by this test.

Existing prompt conversion is opt-in through Ansible; it preserves instructions and makes a protected backup.

Human-readable diagnostics: `tail -f ~/ac-agents/environment-logs/events.log` (safe metadata only).

The disposable fresh deployment passed in one full AAP run at version 0.9.1; newer source changes are outside that snapshot. See [DEPLOYMENT_TEST_RESULTS.md](DEPLOYMENT_TEST_RESULTS.md).

The editable default template for new projects is `~/ac-agents/conf/templates/assistant.prompt.md.template`.
Creation copies its role instructions into the new project; existing project prompts
remain independent. Deployment preserves operator edits and migrates the old home-level
template without overwriting an existing destination. Conflicting paths require operator review.

`~/ac-agents/bin/team unarchive PROJECT-ddmmyyhhmm` copies a retained archive to that dated project name, enables its target, and leaves it stopped. The original archive is always retained.

`~/ac-agents/bin/team rename-project OLD NEW` stops and renames a project/config, preserving content and target enablement. It leaves NEW stopped: `~/ac-agents/bin/team start NEW`. Never run same-project lifecycle commands concurrently.

First run: attach each role, finish native onboarding, then give the task to the
orchestrator. Gemini work uses exact Vertex model IDs (for Gemini 3.1 Pro:
`gemini-3.1-pro-preview`); saved login does not verify model access.

A fresh Antigravity role may require your terms/data-use choice. Deployment and
saved login do not prove model access; native wake acceptance is pending this step.

`team status NAME` includes each role’s account profile (for example `gemini-priv`)
and configured model. These are configuration labels, not verified provider model
versions or entitlement. A missing explicit model is shown as `harness default
(unverified)`. Status does not run inference, inspect credentials or send terminal input.

`team watch NAME` colors sender/recipient role labels on interactive terminals;
message text stays plain, and available question correlation IDs remain visible.
Redirected output, `NO_COLOR` and `TERM=dumb` disable color. Restart only the watch
viewer to pick up formatter updates; the project team can keep running.

`team watch NAME` now prints the last 50 communication entries and exits.
`team watch NAME -20` prints the last 20 and exits. `team watch NAME -f` follows
only new entries; `team watch NAME -20 -f` prints the last 20 then follows.
Options may go before or after the project name: `team watch -200 -f NAME`
and compact `team watch -200f NAME` both show 200 entries then follow.
Counts are 0–10000; either flag order works. This changes the earlier bare-watch
live-follow default. History is chronological by message ID, including asks and
replies once each. Follow subscribes before taking its history snapshot and skips
queued events already included in that snapshot. The existing upstream live
stream can drop notifications for an excessively slow viewer; it is not a durable
subscription. History reads only the project’s message table, with no model calls.

Test-clone retirement now requires an exact authorized name in the encrypted
retirement definition, in addition to exclusive disk ownership and preservation
checks. Fresh deployment clears recovery addressing and discovers the new clone
by its own MAC address; it never reuses the retired guest as a recovery target.
For a concise decision feed, run `tail -f ~/projects/NAME/workspace/DECISIONS.log`.
The summarizer appends timestamped DECIDED, DIRECTION or BLOCKED lines only after
meaningful accepted outcomes, agreed direction changes or blockers requiring
user input. The orchestrator requests these updates at milestones, without timers.
The summarizer is the sole intended writer; proposals, repetitive progress,
credentials, private connector content and hidden-role identities stay out.
This is an agent instruction policy, not a filesystem enforcement of append-only
writes: project workspace collaborators retain their existing write permissions.
Existing user prompts and log content are preserved during deployment. Already
running harness conversations need an explicit instruction refresh to adopt it;
updating files alone does not guarantee they re-read their role instructions.

Codex containers require the dedicated enforcing-SELinux sandbox policy. Native workspace-write confinement remains active; no outside-sandbox approval is needed for ordinary shared-workspace writes.

Bootstrap auth replication: `src/transfer_native_auth.yml` via AAP, metadata-only
by default; missing-only restore after explicit authorization. See
[AUTH_TRANSFER.md](docs/AUTH_TRANSFER.md). Existing credentials and projects stay
unchanged. Fresh deployment restores missing credentials from the encrypted
bootstrap snapshot automatically; no source VM is required.

Auth transfer transport: synthetic local Ansible preflight/copy/rerun verified;
real AAP transfer remains gated on fresh environment readiness.

Mistral auth transfer supports native Vibe metadata and separate work/private
accounts; team roles use the same pinned native Vibe harness.

## Secret snapshot storage

Encrypted model/deployment snapshots may live only in the private companion
assistant-team-secrets repository, not this code repository. Encrypted configuration
files are named `NAME_vault.yml`. The Vault password
and all plaintext credentials stay outside Git. Fresh complete/portable deployments
restore missing enabled-profile credentials from `vaults/bootstrap-auth_vault.yml`;
existing credentials and running projects are preserved. Saved credentials do not
prove usable model access. After re-login, refresh the encrypted snapshot and AAP's
ciphertext copy; deployment does not perform interactive login or model checks.

## Attach readiness

Attach requires a running role and live native tmux pane. If the project has only
been created or is stopped, run `team start PROJECT` before `team attach PROJECT ROLE`.
Failures explain the next command; attach never starts anything implicitly.

Help groups environment/discovery commands and project commands separately,
with entries alphabetized by command name (ignoring leading option hyphens).

## Deployment configuration storage

The five active deployment/recovery Vault files live in the private companion
`assistant-team-secrets/vaults/configuration/`, outside the application repository.
Local playbooks use the sibling checkout or `assistant_secret_config_root`; explicit
file overrides take precedence over AAP-injected configuration file paths. AAP uses
one configuration-snapshot credential plus the existing Vault-password credential.
The same AAP credential includes the encrypted bootstrap-auth snapshot (six files
in total). After changing and committing configuration or auth snapshots, run
`src/sync_secret_configs.yml` from
the code checkout with authorized controller credentials to refresh AAP's ciphertext
snapshots. Synchronization never decrypts the files. See the source repository's
README for deployment commands; the runtime team commands do not manage secrets.

Auth maintenance: after re-login on the configured bootstrap source, launch AAP
**Assistant Team Refresh Model Authentication**. New complete deployments restore
missing auth automatically from the encrypted companion vault; existing credentials
are preserved. Successful restoration does not prove unrevoked model access.

Fresh-install acceptance: AAP job 2104 passed at 1.4.4, including six encrypted-vault
auth restores and model-free installation checks. See DEPLOYMENT_TEST_RESULTS.md.

## Inventory-governed VM deployment and teardown

AAP inventory is the source of truth for VM identity and production protection.
Each managed host has an explicit `assistant_vm_name` binding and belongs to
`assistant_team`; membership in `prod`, including inherited membership, prevents
teardown. Missing, ambiguous or incomplete inventory results fail closed. The
lifecycle jobs read live inventory over verified HTTPS using a dedicated
nonadministrator credential scoped to that inventory. Launch surveys accept only
the target fields; arbitrary extra variables are disabled.

- **Assistant Team Fresh Deployment Test**: enter `deployment_vm_name` and leave
  job tags empty for a complete new installation. Infrastructure and authentication
  still come from encrypted companion snapshots; selecting another name needs no
  Vault edit or snapshot synchronization. Existing inventory/domain/disk names
  are refused. Provisioning registers the discovered guest in inventory before
  configuration; selected configuration-only tags use its inventory address.
- **Assistant Team Disposable Test Retirement**: enter `teardown_vm_name`.
  `retire_test_execute: false` runs safety preflight; `true` shuts down and removes
  only the selected clone and exclusive disk. Production membership is rechecked
  before deletion, and the inventory host is removed only after preservation
  checks succeed. The original installation cannot be deleted by this job.
- **Assistant Team Linux VM Shutdown**: enter `shutdown_vm_name` to request graceful
  shutdown and wait for it, preserving every domain definition and disk.

Use `src/configure_vm_lifecycle.yml` to reproduce the surveys, credential injection
and inventory groups. Supply the dedicated inventory token and trusted CA through
private files, alongside explicit existing AAP object bindings; see its role README.
Mark a verified deployment as production by placing its host in inventory group
`prod`. Production marking is a separate inventory action after acceptance; it
is never inferred from a VM name or stored in libvirt metadata.
