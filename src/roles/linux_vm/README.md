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

### Ordinary upstream-image clients

Normal client deployments use explicit `linux_vm_upstream` inputs
with the existing Generic Linux VM Deployment playbook. It is mutually exclusive
with `linux_vm_recovery` and preserves the existing encrypted guest login. The
mapping requires the selected VM/image/network/destination fields, independently
verified hypervisor SSH keys and machine ID, an exact source-image SHA-256 and
the expected libvirt network bridge. It hard-requires `generic_image: true` and
`update_packages: false`; cloud-init package updates and upgrades are explicitly
disabled. Fresh clone identity, strict SSH on both hops, standalone-image and
no-overwrite checks remain required.

This route leaves ordinary production networking unchanged. It does not call
recovery policy observation, firewall/CaC publication or recovery release. Existing
isolated-recovery inputs, preflight and release remain the default for that route.
Native provenance uses a distinct `generic-upstream` type so a normal client
cannot be silently treated as an isolated-recovery guest. Recovery retirement
and application inventory registration are not added for normal clients.

The normal route is implemented and validated by focused Core 2.20 fixtures.
Source tests do not establish live client deployment or application acceptance.
Keep populated image, network and pin settings in the existing encrypted project
configuration. No new credential source, service or job template is proposed.
