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

Prompt rendering accepts new `[Role: Name]` markers and existing `# Role:` headers.
New-format `#` lines are author comments, removed before role extraction is delivered
to native harnesses. Each supported role must appear once; only its own active text
and the shared project goal are rendered. Blank sections have no example fallback.

## Focused image repair

The tmux image extension includes `procps`: Codex's managed app server needs
`ps` even when its CLI version check succeeds. Image verification executes process
inspection in an isolated credential-free container before any selected repair.
Use the `connector_images` tag with `agents_connector_image_flavours: [codex]`
and `agents_connector_image_force: true` to rebuild only Codex through the certified
image module. Other images and running containers remain unchanged.

The optional `connector_codex_repair` tag requires an explicit
`agents_connector_repair_codex_project`. It refuses an active or non-Codex builder;
only a dead native pane's container is replaced. Mounted home, authentication and
workspace files remain in place. The new native session receives no initial task
prompt. Do not use this operation as a general project restart.
