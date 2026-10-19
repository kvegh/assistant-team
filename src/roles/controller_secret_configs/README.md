# Controller encrypted configuration snapshots

Run `src/sync_secret_configs.yml` from a trusted controller/operator host after
committing configuration changes in the sibling secrets repository. The role
uses existing Ansible built-in modules and the documented controller API; it does
not require an additional controller collection or Git credential on job runners.

Supply `CONTROLLER_HOST`, `CONTROLLER_OAUTH_TOKEN` and the numeric
`CONTROLLER_ORGANIZATION` through the operator environment. The source checkout
is `../assistant-team-secrets` by default; override
`controller_secret_configs_checkout` for another location. The five active
`vaults/configuration/*_vault.yml` files and the encrypted model-authentication
snapshot `vaults/bootstrap-auth_vault.yml` are read, with `slurp` so Ansible never
automatically decrypts them during synchronization. Whole-file Vault headers are
required. Dirty configuration inputs are refused.

One custom cloud credential type injects six named ciphertext files through
`AC_AGENTS_*_VAULT_FILE` environment variables. The existing separate Vault
credential supplies runtime decryption. The provider authentication snapshot
remains encrypted during synchronization; restoring its allowlisted files is the
deployment restore role's responsibility. Source revision and a ciphertext-set
checksum allow idempotent refreshes without comparing masked secret API values.

An optional `controller_secret_configs_job_templates` list associates the
snapshot credential with selected existing templates, preserving their other
credentials. During migration, the previous named snapshot credential is detached
only after the new snapshot has been attached to each explicitly selected job
template. Previous credential/type objects are retained. The new six-file type
has a distinct name because AAP disallows editing an in-use credential type.
Set `controller_secret_configs_previous_credential_name` to an empty string to
disable association migration. The role does not launch jobs, provision hosts or change GitHub
access. Run `src/validate_secret_configs.yml` with the snapshot and Vault
credentials for a localhost-only loading check before running deployment jobs.

Temporary AAP files live only for their job. The private secrets repository is the
source of truth; its updates are not automatically pulled into existing AAP
snapshots. Re-run synchronization after each committed configuration change.
