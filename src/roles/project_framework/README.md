# project_framework

Install project-scoped control, strict configs, services and concise operator guides.
`~/team --list` and `~/team list-projects` list initialized project names without
opening project data or requiring authentication; account profiles use `~/team setup --list`.

## Interface

`~/team --help` describes all public commands. Unknown commands explicitly report
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
`~/project-archive/NAME`, rejecting collisions before shutdown. Whole-directory
rename preserves SQLite auxiliary files and internal symlinks. Config placement
is rolled back if the archive rename fails. Shared templates, images, provider
homes and other projects are preserved. Do not run concurrent lifecycle/edit
operations against the same project. There is no restore command yet.
