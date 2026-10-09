# project_framework

Install project-scoped control, strict configs, services and concise operator guides.
`~/ac-agents/bin/team --list` and `~/ac-agents/bin/team list-projects` list initialized project names with read-only runtime status without
opening project data or requiring authentication; account profiles use `~/ac-agents/bin/team setup --list`.

## Interface

`~/ac-agents/bin/team --help` describes all public commands. Unknown commands explicitly report
`Invalid command`; missing project arguments remain distinct. Help needs no auth
and starts no service.

containers.runtime_user is the account; assistant_build_commit optionally overrides source revision metadata.

## Dependencies and platform

agents_connector and native_auth; stock broker is needed when a project is created.

## Safety, idempotence and check mode

Does not enable or restart projects. Editable project definitions/prompts/auth are preserved; reloads service definitions only.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.

New projects receive `[Project]` and `[Role: Name]` sections with inactive `#` example
comments. Authors must add active instructions. Existing project files are never
overwritten; legacy role headers remain supported by the renderer.

`project_framework_migrate_prompt_projects` defaults to an empty list. Set explicit
project names only to migrate legacy prompts to bracket sections. Migration makes
0600 backups and preserves custom instructions and meaningful heading text; it is
idempotent and does not restart or apply prompts to running sessions.

`destroy NAME` and `archive NAME` require only an initialized named project and
its regular home-level config, never saved model authentication. They stop running
named service instances/orphan containers, disable enabled named units, verify
quiescence and remove stopped project containers. Destroy deletes only that
project/config; archive moves the whole directory with config into a private
`~/project-archive/NAME-ddmmyyhhmm` on every invocation (operation-start local
24-hour time, saved as private ISO timestamp metadata), rejecting collisions before
shutdown. Existing exact-name archives also refuse shutdown and recommend
`team rename-project OLD NEW`; existing archives are never renamed or overwritten. Whole-directory
rename preserves SQLite auxiliary files and internal symlinks. Config placement
is rolled back if the archive rename fails. Shared templates, images, provider
homes and other projects are preserved. The four named unit instances have their
failed states reset and must disappear from nonloading `list-units --all` checks
within ten seconds before filesystem changes; lingering references fail safely.
These checks deliberately avoid `show`/`status`, which can reload an instance.
This follows [systemd unit garbage collection](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html#Unit%20Garbage%20Collection).
Do not run concurrent lifecycle/edit
operations against the same project. There is no restore command yet.

Listing status uses service metadata and checks inactive projects for orphan
containers. Query failures produce `unknown` with an actionable bus/access hint
rather than silently becoming `stopped`. `running` is target state, not native
pane health or provider entitlement; listing never activates services.

The installed unarchive helper copies retained archives transactionally and uses the shared identity helper to update structured config and generated role instructions. Shared name validation checks real Unix socket path lengths before restoration.

`~/ac-agents/bin/team rename-project OLD NEW` stops OLD when necessary, removes only its stopped
containers and forgets its old named systemd instances, then renames the project
directory and home assignment config. It updates structured project identity and
generated role instructions, preserving editable prompts, workspace artifacts,
conversation history and native authentication. The new target preserves OLD's
enablement and remains stopped; start it explicitly with `~/ac-agents/bin/team start NEW`.
Existing new paths/configs, containers, loaded instances or excessive Unix socket
path lengths refuse the operation before shutdown. Partial rename failures roll
back directories, config and generated instructions where possible; an incomplete
rollback reports retained paths rather than overwriting them. Do not run lifecycle
commands or edit the same project's config concurrently.


Restore allows relocatable internal relative links. Codex's generated arg0
launch shims and app-server-control state are omitted only from the restored
copy; its release-cache `current` pointer can map from `/home/agent` to a relative
link within its own retained release directory. Arbitrary absolute/external,
dangling, cyclic and special-file links remain rejected. Validate both source
and staging trees; keep the retained archive untouched.

The exact Codex `.codex/app-server-daemon/daemon-updater.sock` is also omitted
from the restored copy when it is a socket; an ordinary file at that path is kept.

Project stop requests explicitly include the target and all three dependent
services and wait for service jobs, native container shutdown and IPC listener
closure. A target becoming inactive alone is insufficient. Start waits for an
in-progress shutdown; restart uses completed stop then start rather than a single
target restart job. Stop preserves configuration, authentication, prompts, stopped
containers and unit enablement. Runtime status uses the dependent-aware summary.

The focused `project_control` tag installs only the operator control file and
required account/path facts. It does not render units, reload systemd, restart
services, rewrite project files or change authentication.
Installation paths resolve through `install_layout`: `assistant_install_prefix` is the destination parent (default runtime HOME), `assistant_install_root=PARENT/ac-agents`, profiles are in `model-environments` and connector tooling in `agent-connector`. Runtime HOME remains unchanged for Podman/systemd. This source-only layout refuses legacy environments until controlled migration; no current deployment was changed.

`project_framework_enabled_profiles` optionally selects initially enabled work/private profiles. A nonempty known unique list creates missing `conf/environment.conf` (0600, force:false by default); all other supported profiles are disabled. Empty means no seed and preserves the existing automatic behavior. Existing operator edits are retained. `project_profile_selection` resolves paths and runs the seed without starting services or authenticating.

`project_framework_reconcile_profiles: true` is an explicit operator opt-in to replace the existing selection with the provided nonempty list. It is false by default and is never inferred from source authentication or enabled automatically. Confirm ownership of current configuration before choosing it; credentials and projects are not copied or restarted by this task.
