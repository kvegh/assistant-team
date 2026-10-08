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
