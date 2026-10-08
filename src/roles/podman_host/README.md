# podman_host

Prepare one isolated rootless container runtime account using certified Podman content.

## Interface

containers.runtime_user and provisioning.guest_ssh_user are the shared encrypted account contract; podman_host_minimum_free_bytes controls reserve.

## Dependencies and platform

RHEL9 x86_64, become access and redhat.rhel_system_roles1.120.5. Exports podman_host_runtime_home and podman_host_runtime_uid.

## Safety, idempotence and check mode

Managed packages, files and services are idempotent; check mode on a previously unconfigured host cannot manufacture a user-manager or engine.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
