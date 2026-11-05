# linux_vm_retire

Retire one disposable VM selected by a launch-time name, through a normal AAP job.

## Interface and dependencies

The entry-point playbook resolves required `teardown_vm_name` against live AAP
inventory, loads shared encrypted infrastructure settings, and constructs
`linux_vm_retire_definition` and `linux_vm_retire_disk`. No per-target encrypted
file edit is needed. `linux_vm_retire_execute` defaults false for read-only
preflight. Requires existing libvirt CLI tools and the inventory lifecycle
credential described by `inventory_vm_guard`.

The entry point consumes its existing injected `retire_test` ciphertext, allowing
a selected recovery-host retirement profile while preserving the original fresh
deployment configuration. Canonical version names such as `example-v07` retain
the exact live ownership and production checks. A released recovery guest also
uses the same pinned shared AutoDeploy tasks to clean up exact shared inventory
and policy, in addition to its domain and disk. It needs the existing source API,
Git writer, CaC Vault and source CA credentials already used by guest release.
The shared plan resolves persisted `vm_resource` before deleting anything. After
graceful shutdown, the UUID and clone inode/device must still match that plan.

## Safety and validation

Requires a unique explicit `assistant_vm_name` binding in the `assistant_team`
inventory group. Direct or inherited `prod` membership refuses deletion. Inventory
protection is checked again after graceful shutdown, immediately before undefine.
The original clone (numeric suffix one) remains ineligible even without a prod
label. Refuses shared, extra, symbolic or source-image disks. Checks every defined
domain's disk references and confirms all other domain names and source-image
file identity remain intact. No wildcard deletion or forced stop. Check mode is
refused because live preflight is mandatory. Legacy profiles continue to require
the exact existing domain and inventory row. Generic retirement also removes only
matching static DHCP reservations and this guest's HTTPS/full-release entries,
publishing to the existing three encrypted captures and source inventory before
deleting its Assistant row. Selected host-service grants refuse planning until
supported exact cleanup exists. Dynamic DHCP lease cache is reported and is not
edited.

If publication is interrupted, the surviving canonical/API resource record
allows a safe retry with no connection to the deleted guest. If both ownership
records are gone, only native absence of the domain and both canonical disk paths
permits a no-op. Remaining disks, unknown DHCP ownership or changed policy stop
the job. Other inventory hosts, groups, images and controller resources remain.
