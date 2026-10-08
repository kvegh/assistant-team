# linux_vm

Provision a guarded fresh clone on one libvirt hypervisor.

## Interface

provisioning: encrypted image/network/guest bootstrap definition; linux_vm_vcpus, linux_vm_memory_mb and linux_vm_disk_gb are typed defaults. Legacy vm_* resource overrides remain accepted.

## Dependencies and platform

libvirt CLI tools and the selected golden image; guest identity and credentials come from Vault.

## Safety, idempotence and check mode

Input guards can run in check mode. Creation needs live libvirt/DHCP state and is deliberately one-shot; use guest_config recovery, never repeat provisioning.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
