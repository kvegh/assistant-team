# retire_legacy

Retire only the exact original non-project units/containers.

## Interface

containers.runtime_user identifies the owner.

## Dependencies and platform

Rootless runtime account and user manager.

## Safety, idempotence and check mode

Exact original names only; no project-scoped units or bind-mounted data are removed. Checks existing resources before removal.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
