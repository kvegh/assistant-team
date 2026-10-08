# gemini_account

Perform the legacy Gemini directory-name migration without losing saved state.

## Interface

containers.runtime_user identifies the account.

## Dependencies and platform

The dedicated runtime account exists.

## Safety, idempotence and check mode

Only moves an existing legacy directory, refuses destination overlap/active CLI, and preserves credentials. Process-aware migration needs a live run.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
