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

The standalone playbook builds all four pinned native images in the target runtime user’s store, installs the stock broker/native tools and separate roles, then deploys project control and guides. It does not depend on another developer user’s images, a sibling `vpf`, temporary SSH repair files or this repository’s encrypted development inventory. Immutable local program assets may be retained for dependency ordering while environment profile enablement controls authentication/project use. No accounts are authenticated during installation.

After deployment, enter the dedicated runtime user shell, read `~/README.TLDR.md`, run `~/team setup --list`, select profiles with `~/team setup`, and perform native logins yourself. No project is started automatically. Mistral standalone profiles are installed; Agents Connector’s Vibe adapter remains future work.

Protected controller diagnostics live under `~/.local/state/assistant-team/deployment-logs/RUN`. Raw output is for local operator review and is never automatically exported. Metadata export is explicit:

```sh
python3 src/deploy-environment.py --run-directory /private/deployment-run --export /private/deployment-metadata.tar.gz
```

Share only the prescribed metadata bundle. It excludes Vaults, target access details, raw Ansible output, account credentials, databases and conversations. After a deployment attempt the runner transfers allowlisted stage/result metadata to runtime `~/environment-logs` when the target and runtime account are reachable. Otherwise the protected controller spool remains available; use `python3 src/deploy-environment.py --vault-file /private/destination_vault.yml --vault-password-file /private/vpf --transfer-run /private/deployment-logs/RUN_ID` to replay that earlier run’s safe metadata once the target is ready (add `--local` for same-host deployment). The target retains 32 deployment runs and runtime events rotate at 1 MiB across four files; the controller retains ten runs. Raw output is excluded from target transfer. `~/team diagnostics --export /private/environment-metadata.tar.gz` exports prescribed target metadata only. Fresh-VM end-to-end installation has not yet been performed by this development session.
