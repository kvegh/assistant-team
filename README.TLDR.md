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
~/team --list            # initialized project names; alias: list-projects
~/team create-project example
vi ~/projects.example.config                      # role -> enabled profile
vi ~/projects/example/assistant-prompt.md          # goal and role prose
~/team start example
~/team attach example orchestrator                 # give task; Ctrl-B D detaches
~/team watch example                               # live messages; Ctrl-C viewer only
~/team status example
~/team stop example
~/team restart example
~/team diagnostics --export /private/metadata.tar.gz # safe environment metadata
~/team apply-prompts example                       # effective next launch
```

Artifacts: `~/projects/example/workspace` (`/workspace/shared` in containers).
Vertex work profiles require the scoped Cloud SDK (operator-selected during deployment); private Gemini uses scoped Antigravity (`cd ~/gemini-priv; ./login`, then `./agy`). Its team adapter is pending; use Gemini work for project roles.
Native SSH/container auth uses local file permissions, not encryption at rest.
Mistral native login is supported; team adapter is not implemented yet.
Login reports failed/cancelled or credentials saved/model access unverified; no automatic inference.
All eight role sessions start only after enabled assignments and saved auth pass; connectors lack service tools, observer snapshots are manual. Details: `~/README.md`.

## Disposable deployment test lifecycle

`src/retire_test_linux_vm.yml` performs a read-only preflight by default using its separate encrypted retirement definition. Its dedicated normal AAP template removes the selected second test clone only when explicitly launched with `retire_test_execute: true`. The role verifies exclusive disk ownership, refuses source-image or shared disks, uses graceful shutdown, and checks preservation of all other domains and the golden image. The fresh deployment definition selects the next test clone with an empty recovery address; configuration-only recovery remains available after successful provisioning. No provider credentials are copied or model inference performed by this test.
