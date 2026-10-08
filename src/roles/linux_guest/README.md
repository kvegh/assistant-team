# linux_guest

Verify the selected guest identity, allocated resources and golden-image cleanup.

## Interface

deployment_vm_name, deployment_vm_vcpus and deployment_vm_memory_mb are provisioned-host metadata.

## Dependencies and platform

The provisioned guest is reachable; gathers its own facts.

## Safety, idempotence and check mode

Read-only verification; requires a live guest.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
