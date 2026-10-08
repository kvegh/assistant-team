# agents_connector

Install the pinned stock broker, restricted routing and native tmux image extensions.

## Interface

agents_connector_* defaults define pinned distribution and generic profiles; assistant_source_user identifies the credential-free source image store.

## Dependencies and platform

podman_host and agent_images. Resolves its account paths separately.

## Safety, idempotence and check mode

Immutable artifacts/config are managed idempotently; editable prompt seed uses force:false. Existing projects and account credentials are preserved.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
