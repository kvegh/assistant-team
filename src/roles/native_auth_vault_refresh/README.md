# Refresh encrypted model authentication

`src/refresh_native_auth_vault.yml` runs on the controller and captures the
existing native-auth allowlist from one explicit inventory host. Configure
`auth_vault_refresh` in the encrypted environment configuration with
`source_host`, `source_profiles_root`, `source_environment_config` and
`runtime_user`. Source profiles must be idle and every enabled profile must have
validly shaped saved authentication. No model inference runs.

Inject the SSH repository URL in `AC_AGENTS_AUTH_REPO_URL`, a dedicated write key
file in `AC_AGENTS_AUTH_REPO_SSH_KEY_FILE`, and pinned SSH known-hosts material in
`AC_AGENTS_AUTH_REPO_KNOWN_HOSTS_FILE`. The SSH host is never discovered or blindly
trusted during this job. `AC_AGENTS_AUTH_VAULT_PASSWORD_FILE` provides the file
used for encryption; the standard Ansible Vault credential decrypts the existing
snapshot. Standard `CONTROLLER_HOST`, `CONTROLLER_OAUTH_TOKEN` and
`CONTROLLER_ORGANIZATION` supply snapshot synchronization access.

The job preserves all other existing vault metadata and replaces only
`native_auth_transfer`. Missing/invalid enabled profiles and removal of any
previously stored profile fail before writing. No persistent plaintext snapshot
is created: capture remains in protected Ansible memory, then enters
`ansible-vault encrypt` through stdin. Only the encrypted vault is committed and
pushed. Unchanged captures, excluding their timestamp, produce no commit. Push
uses normal conflict detection and never forces concurrent changes away.

After publication the controller snapshot is synchronized from the temporary
checkout. An unchanged refresh still runs synchronization to repair an earlier
interrupted snapshot update. Temporary checkout/helper directories and transient
credential facts are removed on success or failure. Saved authentication does
not establish current model entitlement; tokens may expire or be revoked.
