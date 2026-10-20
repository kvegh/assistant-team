# linux_vm_retire

Retire one disposable VM selected by a launch-time name, through a normal AAP job.

## Interface and dependencies

The entry-point playbook resolves required `teardown_vm_name` against live AAP
inventory, loads shared encrypted infrastructure settings, and constructs
`linux_vm_retire_definition` and `linux_vm_retire_disk`. No per-target encrypted
file edit is needed. `linux_vm_retire_execute` defaults false for read-only
preflight. Requires existing libvirt CLI tools and the inventory lifecycle
credential described by `inventory_vm_guard`.

## Safety and validation

Requires a unique explicit `assistant_vm_name` binding in the `assistant_team`
inventory group. Direct or inherited `prod` membership refuses deletion. Inventory
protection is checked again after graceful shutdown, immediately before undefine.
The original clone (numeric suffix one) remains ineligible even without a prod
label. Refuses shared, extra, symbolic or source-image disks. Checks every defined
domain's disk references and confirms all other domain names and source-image
file identity remain intact. No wildcard deletion or forced stop. Check mode is
refused because live preflight is mandatory. A completed removal is deliberately
not repeated. After successful removal and preservation checks, only the matched retired VM
inventory host is deleted, allowing its name to be reused. Other inventory hosts,
groups and controller resources are preserved.
