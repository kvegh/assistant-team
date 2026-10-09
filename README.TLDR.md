# Assistant team: commands

Source-only layout change: these new-prefix instructions describe future fresh installs. The running environment keeps its current home-level commands and paths; do not deploy this layout to it yet. See [migration prerequisites](INSTALLATION_MIGRATION.md).

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
~/ac-agents/bin/team watch example                               # live messages; Ctrl-C viewer only
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
Vertex work profiles require the scoped Cloud SDK (operator-selected during deployment); private Gemini uses scoped Antigravity (`cd ~/ac-agents/model-environments/gemini-priv; ./login`, then `./agy`). Its team adapter is pending; use Gemini work for project roles.
Native SSH/container auth uses local file permissions, not encryption at rest.
Mistral native login is supported; team adapter is not implemented yet.
Login reports failed/cancelled or credentials saved/model access unverified; no automatic inference.
All eight role sessions start only after enabled assignments and saved auth pass; connectors lack service tools, observer snapshots are manual. Details: `~/ac-agents/README.md`.

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

The approved install-prefix layout is currently **source only**. The existing deployment remains on its earlier home-level layout; do not apply these playbooks to it yet. Fresh installs use `PARENT/ac-agents`, with PARENT defaulting to the destination runtime HOME. `--prefix /absolute/parent` selects a destination parent for both local and remote deployment; AAP uses `assistant_install_prefix` or its encrypted definition. See [INSTALLATION_MIGRATION.md](INSTALLATION_MIGRATION.md) before any legacy migration.
