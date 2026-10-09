# native_auth_transfer

Transfer operator-authorized bootstrap authentication between two existing
inventory hosts through Ansible's protected command transport. Default execution
is a metadata-only preflight. The role installs no dependencies, invokes no model
and never restarts a project or native harness.

See [the transfer guide](../../../docs/AUTH_TRANSFER.md) for encrypted binding
variables, the exact per-profile material manifest and security/rollback limits.
`src/transfer_native_auth.yml` is the dedicated AAP playbook. Keep source and
destination bootstrap login commands idle during the operation.
