# vertex_auth

Install approved pinned work SDK and isolated Vertex helpers without authentication.

## Interface

vertex_auth_install_sdk defaults false; exact version/checksum are in role defaults.

## Dependencies and platform

Native work profile directories and runtime account already exist.

## Safety, idempotence and check mode

Reuses installed SDK/immutable files; work ADC stays separate. Login and model entitlement are never inferred or invoked by setup.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
