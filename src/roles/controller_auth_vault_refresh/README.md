# AAP authentication snapshot maintenance configuration

Creates/reconciles the dedicated maintenance credential type, its protected input
credential and the `Assistant Team Refresh Model Authentication` job template.
It uses Ansible's built-in `uri` module; the certified controller collection is
not a prerequisite. It does not run the refresh job or modify model credentials.

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
- `AC_AGENTS_AUTH_MAINTENANCE_VAULT_PASSWORD_FILE`: absolute Vault-password file path.
- `AC_AGENTS_AUTH_MAINTENANCE_CONTROLLER_TOKEN_FILE`: absolute file containing the
  dedicated snapshot-maintenance token, separate from this setup's authorization.

The credential injects temporary private key/known-host/password files and scoped
environment variables into the refresh job. Store a repository-scoped writable
SSH deploy key and narrowly authorized controller token; this role does not create
accounts, grant permissions, trust new host keys or accept provider terms.

All input reads, API payloads and responses are `no_log` with diff disabled. The
nonsecret material checksum permits idempotent comparison without rewriting masked
secret inputs on every run. A changed input updates the dedicated credential.
Existing job credential associations are preserved; required ones are attached.
The refresh job prohibits simultaneous runs and fact caching. Only resulting
resource IDs are reported publicly. Secret facts are discarded on success/failure.
