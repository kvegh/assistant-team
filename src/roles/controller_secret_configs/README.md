# Controller encrypted configuration snapshots

Run `src/sync_secret_configs.yml` from a trusted controller/operator host after
committing configuration changes in the sibling secrets repository. The role
uses existing Ansible built-in modules and the documented controller API; it does
not require an additional controller collection or Git credential on job runners.

Supply `CONTROLLER_HOST`, `CONTROLLER_OAUTH_TOKEN` and the numeric
`CONTROLLER_ORGANIZATION` through the operator environment. The source checkout
is `../assistant-team-secrets` by default; override
`controller_secret_configs_checkout` for another location. Only the five active
`vaults/configuration/*_vault.yml` files are read, with `slurp` so Ansible never
automatically decrypts them during synchronization. Whole-file Vault headers are
required. Dirty configuration inputs are refused.

One custom cloud credential type injects five named ciphertext files through
`AC_AGENTS_*_VAULT_FILE` environment variables. The existing separate Vault
credential supplies runtime decryption. No provider authentication snapshot is
loaded by this role. Source revision and a ciphertext-set checksum allow
idempotent refreshes without comparing masked secret API values.

An optional `controller_secret_configs_job_templates` list associates the
snapshot credential with selected existing templates, preserving their other
credentials. The role does not launch jobs, provision hosts or change GitHub
access. Run `src/validate_secret_configs.yml` with the snapshot and Vault
credentials for a localhost-only loading check before running deployment jobs.

Temporary AAP files live only for their job. The private secrets repository is the
source of truth; its updates are not automatically pulled into existing AAP
snapshots. Re-run synchronization after each committed configuration change.
