# container_preflight

Inspect host-key, disk and package metadata through the selected trusted guest connection.

## Interface

The controller inspection play publishes execution_collections.

## Dependencies and platform

Read access to guest metadata; become is provided by its inspection play.

## Safety, idempotence and check mode

Read-only live diagnostics. Protected outputs stay in controller artifacts.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
