# agent_images

Build and smoke-test four pinned native harness images without credentials.

## Interface

agent_images_* defaults contain exact versions, base-image digests and rebuild/reserve controls.

## Dependencies and platform

podman_host runtime outputs and the certified podman_image module.

## Safety, idempotence and check mode

Retains existing images unless rebuild is selected. Building/testing requires a live rootless engine; no model calls.

Failed builds remain failed. Only message, stdout, stderr and return code are
saved in unique `0600` files below the existing private
`environment-logs/image-build` directory (`0700`). Invocation, environment and
credential fields are excluded; build output remains hidden from Controller logs.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.

Installation paths resolve through `install_layout`: `assistant_install_prefix` is the destination parent (default runtime HOME), `assistant_install_root=PARENT/ac-agents`, profiles are in `model-environments` and connector tooling in `agent-connector`. Runtime HOME remains unchanged for Podman/systemd. This source-only layout refuses legacy environments until controlled migration; no current deployment was changed.
