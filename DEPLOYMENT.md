# User-operated deployment

The operator deploys directly from this repository. Destination access stays on the operator’s machine; this coding session requires no destination SSH access, credentials or model login. Installation performs no OAuth or model inference.

Prerequisites: RHEL-compatible x86_64 Linux with systemd, sudo access, adequate disk (at least 8 GiB free recommended for fresh images/packages), Ansible controller with Python and `ansible-playbook`/`ansible-vault`, SSH for remote deployment, and entitled certified `redhat.rhel_system_roles` 1.120.5. Obtain the collection through your own Automation Hub account. No community collection fallback is used. Artifact versions/checksums are pinned in the role defaults; Node/Python base image digests are pinned. Install approved controller prerequisites yourself; this runner does not install them.

Create a private Vault-password file outside Git, mode 0600. Initialize your own encrypted destination settings:

```sh
python3 src/deploy-environment.py --init-vault --vault-file /private/destination_vault.yml --vault-password-file /private/vpf
python3 src/deploy-environment.py --syntax-check --vault-file /private/destination_vault.yml --vault-password-file /private/vpf
python3 src/deploy-environment.py --vault-file /private/destination_vault.yml --vault-password-file /private/vpf
```

For deployment on this same host, add `--local` to initialization and deployment. This uses Ansible’s local connection, without SSH credentials. Sudo credentials, if required, remain in the operator-owned Vault. For remote deployment, normal SSH host-key checking remains enabled; verify destination trust yourself before deployment. The runtime user must differ from the login/controller user.

The destination Vault contains `connection` (`host`, `user`, optional `port`, `password`, `become_password`), `runtime_user`, and optional boolean `install_google_cloud_sdk`. The initializer defaults SDK installation off. Set it true only when you explicitly approve that selected dependency. Google account permissions, enabled Vertex models, billing and provider subscriptions are your prerequisites; deployment does not modify them.

The standalone playbook builds all four pinned native images in the target runtime user’s store, installs the stock broker/native tools and separate roles, then deploys project control and guides. It does not depend on another developer user’s images, a sibling `vpf`, temporary SSH repair files or this repository’s encrypted development inventory. Immutable local program assets may be retained for dependency ordering while environment profile enablement controls authentication/project use. After native profiles and environment selection are configured, installation
restores missing enabled-profile authentication from the companion encrypted
bootstrap snapshot. It does not perform a new OAuth login, renew revoked tokens
or prove entitlement; no projects or model calls are started.

After deployment, enter the dedicated runtime user shell, read `~/README.TLDR.md`, run `~/team setup --list`, select profiles with `~/team setup`, and perform native logins yourself. No project is started automatically. Mistral standalone profiles are installed; Agents Connector’s Vibe adapter remains future work.

Protected controller diagnostics live under `~/.local/state/assistant-team/deployment-logs/RUN`. Raw output is for local operator review and is never automatically exported. Metadata export is explicit:

```sh
python3 src/deploy-environment.py --run-directory /private/deployment-run --export /private/deployment-metadata.tar.gz
```

Share only the prescribed metadata bundle. It excludes Vaults, target access details, raw Ansible output, account credentials, databases and conversations. After a deployment attempt the runner transfers allowlisted stage/result metadata to runtime `~/environment-logs` when the target and runtime account are reachable. Otherwise the protected controller spool remains available; use `python3 src/deploy-environment.py --vault-file /private/destination_vault.yml --vault-password-file /private/vpf --transfer-run /private/deployment-logs/RUN_ID` to replay that earlier run’s safe metadata once the target is ready (add `--local` for same-host deployment). The target retains 32 deployment runs and runtime events rotate at 1 MiB across four files; the controller retains ten runs. Raw output is excluded from target transfer. `~/team diagnostics --export /private/environment-metadata.tar.gz` exports prescribed target metadata only. Fresh-VM end-to-end installation has not yet been performed by this development session.

## Shared deployment and recovery definitions

The standard VM deployment and recovery playbooks load five active Vault-encrypted
inputs from the sibling private `assistant-team-secrets/vaults/configuration/`
checkout. They are no longer tracked under this application's `vars/` directory.
The standalone runner above still accepts its operator-owned `--vault-file`; its
portable destination schema and local/remote deployment choices are unchanged.

For standard playbooks, explicit configuration-file overrides take precedence over
matching `AC_AGENTS_*_VAULT_FILE` environment paths injected by AAP, followed by the
companion checkout. Use `assistant_secret_config_root` to select another directory.
Missing configuration is an error rather than a fallback to the application repo.

AAP uses one custom configuration-snapshot credential with six encrypted file
inputs: the five configuration definitions plus `vaults/bootstrap-auth_vault.yml`,
alongside existing Machine and Vault credentials. Refresh these snapshots
from the authoritative companion checkout after committing configuration changes:

```sh
export CONTROLLER_HOST=https://controller.example.invalid
export CONTROLLER_OAUTH_TOKEN  # supplied securely by the operator
export CONTROLLER_ORGANIZATION=ORG_ID
ansible-playbook src/sync_secret_configs.yml
```

Set `controller_secret_configs_checkout` for a different checkout location. Pass an
explicit `controller_secret_configs_job_templates` list of template IDs to attach
the snapshot credential while preserving other associations. Synchronization uses
the operator's existing controller authorization, transfers ciphertext only, and
records source revision and checksums for idempotence. The Vault password remains
in its separate AAP credential or the operator's external password file. No new
runtime GitHub token or model request is introduced. Configuration stays protected
inside normal Ansible processing; allowlisted native credential files are restored
only on the intended target under private ownership/modes. Existing companion snapshots are preserved; old
application Git history is not rewritten and still contains its former ciphertext.


## Automatic model authentication restoration

After native profiles, project configuration and Vertex setup, complete VM and
portable connector deployment run `native_auth_vault_restore`. The role consumes
`vaults/bootstrap-auth_vault.yml` through the external-file resolver (AAP injects
`AC_AGENTS_BOOTSTRAP_AUTH_VAULT_FILE`). It restores only missing credentials for
enabled profiles; existing destination credentials remain authoritative. No source
VM, new repository token, project restart or model request is needed.

The destination receives only allowlisted native credential files and required
provider metadata, with private permissions. Safe outcomes are recorded at
`environment-logs/auth-restore/latest.json` below the installation root. Set
`native_auth_vault_restore_enabled: false` for an intentionally unauthenticated
installation; otherwise missing or malformed authentication input is an error.

Credentials must already be usable at the provider. Expired/revoked grants can
still require operator login; restoration never proves model entitlement. After
re-login, refresh the encrypted snapshot and AAP ciphertext copy before deploying
again. See [AUTH_REPLICATION.md](docs/AUTH_REPLICATION.md) for capture/refresh and
[AUTH_TRANSFER.md](docs/AUTH_TRANSFER.md) for the optional host-to-host alternative.
