# linux_vm

Provision a guarded fresh clone on one libvirt hypervisor.

## Interface

provisioning: encrypted image/network/guest bootstrap definition; linux_vm_vcpus, linux_vm_memory_mb and linux_vm_disk_gb are typed defaults. Legacy vm_* resource overrides remain accepted.

For a standalone upstream image, the shared playbook merges explicit nonsecret
`linux_vm_recovery` inputs into the existing encrypted `provisioning` definition.
Guest SSH/bootstrap values come only from that existing file; the override cannot
contain credential fields. Set `generic_image: true` and supply `hypervisor_pin`
and `isolation_policy` in the recovery dictionary.
The pin declares `address`, `user`, `port`, `machine_id` and verified `host_keys`.
The current isolation policy is checked without modifying it. This mode provisions
fresh guest keys/account offline, uses q35/virtio/host-passthrough with one thread
per core, and routes guest SSH through the pinned hypervisor. The caller supplies
the already allocated guest name; this role does not consume another counter.

## Dependencies and platform

libvirt CLI tools and the selected golden image; guest identity and credentials come from Vault.

## Safety, idempotence and check mode

Input guards can run in check mode. Creation needs live libvirt/DHCP state and is deliberately one-shot; use guest_config recovery, never repeat provisioning.

Check mode stops before disk creation after successful input/storage inspection.
An existing domain or disk remains protected. Password/bootstrap files are private
and removed even when customization fails. Native domain descriptions retain only
public provenance, including fresh host keys, source image hash and hypervisor ID.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
