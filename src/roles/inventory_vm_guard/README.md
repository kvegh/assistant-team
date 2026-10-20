# inventory_vm_guard

Resolve a requested domain through live AAP inventory before lifecycle actions.

## Inputs

`inventory_vm_guard_name` is the domain name. `inventory_vm_guard_require_existing`
defaults true; false requires the name and explicit domain binding both absent
for a new deployment. `inventory_vm_guard_operation` defaults `retire`; `shutdown`
and `lookup` permit production hosts without permitting their deletion.

A dedicated AAP credential injects `AC_AGENTS_CONTROLLER_HOST`,
`AC_AGENTS_CONTROLLER_TOKEN`, `AC_AGENTS_CONTROLLER_INVENTORY_ID` and optionally
`AC_AGENTS_CONTROLLER_CA_BUNDLE`. The token needs read access to the selected
inventory; deployment registration also needs inventory write access. Controller
TLS verification is mandatory. Inventory bindings are read directly from the
controller rather than launch-time host variables or group overrides. Restrict
launchers to the required survey fields; arbitrary extra variables are not a
supported lifecycle interface.

## Rules and outputs

Exactly one host must explicitly bind `assistant_vm_name` to the requested domain
and belong to `assistant_team`. An inventory display-name alias is permitted only
with that unambiguous binding. Direct or inherited `prod` membership prevents
retirement. Missing, ambiguous, unmanaged or incomplete inventory responses fail
closed. The current implementation supports up to 200 hosts/groups per complete
response and refuses pagination rather than silently ignoring further records.

Protected `__inventory_vm_guard_host` contains the controller host record and
`decoded_variables`; `__inventory_vm_guard_groups` contains inherited group names.
Protected controller connection facts support registration by the deployment role.
Diagnostics expose only generic selection/protection failures, never credentials
or inventory values.
