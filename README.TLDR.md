# Assistant team: commands

Run as the runtime user. One environment per user; credentials stay local.

```sh
~/team --help             # every command, parameters and brief explanation
~/team version            # installed source version/build
~/team setup --list       # enabled / installed / credentials saved (not model verification)
~/team setup             # choose profiles, then optional native login
cd ~/PROFILE; ./login     # PROFILE: claude-work/priv, gemini-work/priv,
                         # codex-work/priv, mistral-work/priv (each full name)
./login --clear           # only current profile; exit CLI and stop using projects first
~/team --list            # project names + status; alias: list-projects
~/team create-project example
vi ~/projects.example.config                      # role -> enabled profile
vi ~/projects/example/assistant-prompt.md          # fill [Project] and [Role: Name]; # lines are comments
~/team start example
~/team attach example orchestrator                 # give task; Ctrl-B D detaches
~/team watch example                               # live messages; Ctrl-C viewer only
~/team status example
~/team stop example
~/team restart example
~/team diagnostics --export /private/metadata.tar.gz # safe environment metadata
~/team apply-prompts example                       # effective next launch
```

Finish a project with one of these alternatives:
`~/team archive NAME` stops it if running and moves its full contents/config to
`~/project-archive/NAME`; `~/team destroy NAME` stops it if running and deletes it.
Both remove only its containers; account profiles and other projects stay intact.
Archive rejects an existing destination. Do not run same-project start/edit operations concurrently.

List status describes services: running, starting, stopping, stopped, failed,
partial (orphan components) or unknown (metadata unavailable); it does not verify model access.

Artifacts: `~/projects/example/workspace` (`/workspace/shared` in containers).
Vertex work profiles require the scoped Cloud SDK (operator-selected during deployment); private Gemini uses scoped Antigravity (`cd ~/gemini-priv; ./login`, then `./agy`). Its team adapter is pending; use Gemini work for project roles.
Native SSH/container auth uses local file permissions, not encryption at rest.
Mistral native login is supported; team adapter is not implemented yet.
Login reports failed/cancelled or credentials saved/model access unverified; no automatic inference.
All eight role sessions start only after enabled assignments and saved auth pass; connectors lack service tools, observer snapshots are manual. Details: `~/README.md`.

## Disposable deployment test lifecycle

`src/retire_test_linux_vm.yml` performs a read-only preflight by default using its separate encrypted retirement definition. Its dedicated normal AAP template removes the selected second test clone only when explicitly launched with `retire_test_execute: true`. The role verifies exclusive disk ownership, refuses source-image or shared disks, uses graceful shutdown, and checks preservation of all other domains and the golden image. The fresh deployment definition selects the next test clone with an empty recovery address; configuration-only recovery remains available after successful provisioning. No provider credentials are copied or model inference performed by this test.

Existing prompt conversion is opt-in through Ansible; it preserves instructions and makes a protected backup.

Human-readable diagnostics: `tail -f ~/environment-logs/events.log` (safe metadata only).

The disposable fresh deployment passed in one full AAP run at version 0.9.1; newer source changes are outside that snapshot. See [DEPLOYMENT_TEST_RESULTS.md](DEPLOYMENT_TEST_RESULTS.md).

The editable default template for new projects is `~/templates/assistant-prompts.md`.
Creation copies its role instructions into the new project; existing project prompts
remain independent. Deployment preserves operator edits and migrates the old home-level
template without overwriting an existing destination. Conflicting paths require operator review.
