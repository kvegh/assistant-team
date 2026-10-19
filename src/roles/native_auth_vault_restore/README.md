# Native authentication restoration

Restores missing native model credentials from the encrypted companion repository's
`bootstrap-auth_vault.yml`, loaded through `secret_config` into a private namespace.
Call after native installations, environment selection and Vertex configuration.
The environment's enabled profiles remain authoritative; the archived environment
selection is not applied. Every enabled destination profile must have a snapshot
credential entry; deployment fails before credential writes if any is absent. Refresh
the snapshot or disable unavailable profiles before retrying. Set `native_auth_vault_restore_enabled: false` for an
intentionally unauthenticated deployment.

The role uses the existing `native_auth_transfer` restore helper with protected
stdin. It preserves existing credential streams, validates the complete allowlist
before writes, refuses unsafe paths or active bootstrap writers, and never copies
project sessions, hooks, approval policy or arbitrary account directories. It needs
no source host. Paths default to the resolved `install_layout` roots and can be
overridden with the role's profiles, environment-config and report-directory inputs.

`native_auth_vault_restore_payload` defaults to the loaded snapshot's
`native_auth_transfer` mapping. Decrypted facts and temporary helper directories are
cleared on success or failure. Temporary files contain code only; credentials are
written only to their intended native destinations with private permissions. A
sanitized report is saved under `environment-logs/auth-restore/latest.json`.

Restored credentials remain **model access unverified**: expired/revoked grants,
provider refresh behavior and model entitlement cannot be established without an
explicit provider access check. No inference or model request runs automatically.
Check mode loads/validates the input but does not invoke restoration.

For an existing installation, `src/restore_native_auth_vault.yml` targets only the
explicit `native_auth_destinations` inventory group. It loads the encrypted runtime
environment and resolves the destination account's canonical paths. Supply absolute
profiles/environment/report overrides for an intentionally noncanonical existing
installation. It never provisions a VM, selects a replacement host, copies source
account directories, or enables profiles from the archived environment selection.
