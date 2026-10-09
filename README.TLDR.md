# Assistant team: commands

Communication stays on agents-connector + tmux; alternatives await review and
decision in [TODO](TODO.md).

Fresh installs use PREFIX/ac-agents. Existing home-level installations require a separately approved migration; see [migration prerequisites](INSTALLATION_MIGRATION.md).
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
Mistral native login is supported; team adapter is not implemented yet.
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
