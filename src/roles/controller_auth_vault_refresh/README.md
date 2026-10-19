# AAP authentication snapshot maintenance configuration

Creates/reconciles the dedicated maintenance credential type, its protected input
credential and the `Assistant Team Refresh Model Authentication` job template.
It uses Ansible's built-in `uri` module; the certified controller collection is
not a prerequisite. It does not run the refresh job or modify model credentials. It validates the
maintenance token's `/me/` identity and refuses superusers and system auditors.
Using setup authorization, it grants that identity Admin on the named deployment
and authentication snapshot credential only; no organization/global roles or
unrelated memberships are granted or removed.

Run `src/configure_auth_vault_refresh.yml` with existing controller authorization
in `CONTROLLER_HOST` (HTTPS), `CONTROLLER_OAUTH_TOKEN` and numeric
`CONTROLLER_ORGANIZATION`. Supply numeric existing object IDs explicitly through
`controller_auth_vault_refresh_project`, `controller_auth_vault_refresh_inventory`,
`controller_auth_vault_refresh_execution_environment` and the list
`controller_auth_vault_refresh_credentials` (Machine, Vault and ciphertext snapshot
credentials). No installation-specific IDs are hardcoded.

Operator-owned inputs:

- `AC_AGENTS_AUTH_MAINTENANCE_REPO_URL`: private companion repository SSH URL.
- `AC_AGENTS_AUTH_MAINTENANCE_SSH_KEY_FILE`: absolute private deploy-key file path.
- `AC_AGENTS_AUTH_MAINTENANCE_KNOWN_HOSTS_FILE`: absolute verified host-key file path.
- `AC_AGENTS_AUTH_MAINTENANCE_CONTROLLER_CA_FILE`: absolute trusted controller CA bundle path.
- `AC_AGENTS_AUTH_MAINTENANCE_VAULT_PASSWORD_FILE`: absolute Vault-password file path.
- `AC_AGENTS_AUTH_MAINTENANCE_CONTROLLER_TOKEN_FILE`: absolute file containing the
  dedicated snapshot-maintenance token, separate from this setup's authorization.

The credential injects temporary private key/known-host/password files and scoped
environment variables into the refresh job. Store a repository-scoped writable
SSH deploy key and narrowly authorized controller token; this role does not create
accounts, grant organization/global permissions, trust new host keys or accept
provider terms. The only role association it creates is the specific snapshot
credential's Admin role needed to refresh encrypted inputs.

All input reads, API payloads and responses are `no_log` with diff disabled. The
nonsecret material checksum permits idempotent comparison without rewriting masked
secret inputs on every run. A changed input updates the dedicated credential.
Existing job credential associations are preserved; required ones are attached.
The refresh job prohibits simultaneous runs and fact caching. Only resulting
resource IDs are reported publicly. Secret facts are discarded on success/failure.

The snapshot is resolved by `controller_auth_vault_refresh_snapshot_credential_name`
(default: `Assistant Team deployment and authentication snapshots`) in the selected
organization and must also occur in the explicitly supplied credential ID list.
Supply a dedicated non-superuser, non-system-auditor service-account token whose
existing permissions have been reviewed separately; this role does not perform a
global membership audit or remove existing access. Create/rotate the dedicated
controller account/token and the single-repository writable GitHub deploy key as
operator bootstrap prerequisites. Neither should reuse an operator-wide admin token
or an SSH key with access to unrelated repositories.

Controller TLS verification stays enabled. The maintenance credential injects the
trusted CA into the execution environment; it does not depend on the control
host's system trust. A replacement type preserves in-use schemas, and only the
previous owned maintenance association is detached after replacement.
