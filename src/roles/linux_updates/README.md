# linux_updates

Register the selected RHEL guest and fully update installed packages.

## Interface

provisioning.rhsm_org and provisioning.rhsm_activation_key come from Vault.

## Dependencies and platform

RHEL9 subscription access; linux_guest verification facts.

## Safety, idempotence and check mode

A handler reboots only after changed packages, before verification. Final update checks require a live package manager.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
