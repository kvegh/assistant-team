# External encrypted configuration

Load one named configuration with `secret_config_name`, optionally into
`secret_config_namespace` (empty means normal host variables). Supported names
are environment, fresh_test, retire_test, claude_auth_recovery and
codex_auth_recovery.

Resolution is an explicit `secret_config_file`, then the corresponding
`AC_AGENTS_*_VAULT_FILE` injected path, then
`assistant_secret_config_root/NAME_vault.yml`. The root defaults to the sibling
secrets checkout's `vaults/configuration` directory. Missing inputs fail without
falling back to the application repository. Configuration contents are loaded
under `no_log`; an existing Vault password/credential remains required.
