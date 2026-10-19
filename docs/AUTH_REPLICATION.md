# Model authentication from the encrypted secrets repository

Fresh complete VM and portable connector deployments restore missing native model
credentials from the private companion repository automatically. Interactive
provider login is needed only when the stored authentication is absent or no
longer usable. Installation performs no OAuth browser flow, token-refresh request,
paid fallback, entitlement check or model inference.

## Deployment flow

1. Install native harnesses and create separate work/private profile homes.
2. Create environment/profile selection and required Vertex settings.
3. Resolve `bootstrap_auth` through `secret_config`: an explicit file override,
   then `AC_AGENTS_BOOTSTRAP_AUTH_VAULT_FILE` supplied by AAP, then the sibling
   `assistant-team-secrets/vaults/bootstrap-auth_vault.yml` checkout.
4. Decrypt through the normal Ansible Vault mechanism and run
   `native_auth_vault_restore` against the selected destination runtime account.
5. Restore only missing allowlisted credentials and required companion metadata
   for enabled profiles. Existing credentials are preserved, including independently
   refreshed project-role caches. No project is created, started or restarted.

Restoration is enabled by default. Set `native_auth_vault_restore_enabled: false`
only for an intentionally unauthenticated deployment. Missing or malformed
required input fails deployment rather than silently reporting authentication
success. The private metadata-only outcome report is
`environment-logs/auth-restore/latest.json` below the installation root.

This route does not contact or require the old source VM. It restores bootstrap
profiles, not running sessions or project backups. A saved credential is reported
with model access unverified; expiration, revocation, subscriptions and provider
permissions still determine whether the native harness can use it.

## AAP ciphertext snapshots

The existing custom configuration-snapshot credential carries six encrypted
inputs: five deployment/recovery definitions and the bootstrap-auth snapshot.
Jobs retain their separate Machine and Vault credentials. The runtime server does
not receive a repository token or clone the secrets repository.

After committing changes to the companion repository, synchronize its ciphertext
into AAP using `src/sync_secret_configs.yml`. Synchronization records the source
revision and checksums without decrypting inputs. AAP uses a snapshot, so a Git
commit alone does not refresh a deployment job's copy. See [DEPLOYMENT.md](../DEPLOYMENT.md)
for the synchronization command and controller settings.

## What the bootstrap vault contains

The private companion repository stores `vaults/bootstrap-auth_vault.yml`, a
whole-file Ansible Vault-encrypted snapshot. No model credential or encrypted
authentication payload belongs in this application repository. The Vault password
and decrypted output stay outside every Git repository. AAP's snapshot credential
contains the ciphertext; its separate Vault credential supplies decryption.
The password credential alone does not contain the authentication payload.

Paths below are relative to a selected native credential home. For a fresh
installation this is `PREFIX/ac-agents/model-environments/PROFILE`; existing
deployments retain their profile location until an explicit migration.

| Profile | Required material | Companion settings |
|---|---|---|
| `claude-priv` | Complete `.claude/.credentials.json` OAuth document | Allowlisted `oauthAccount` metadata and required onboarding flags from `.claude/.claude.json` or `.claude.json`; regenerate other settings |
| `claude-work` | Complete `.config/gcloud/application_default_credentials.json` | `.vertex.json`: project, location and the configured Claude model IDs |
| `gemini-work` | Its own complete `.config/gcloud/application_default_credentials.json` | Its own `.vertex.json`: project, location and model ID; regenerate Vertex authentication settings |
| `gemini-priv` | Complete `.gemini/antigravity-cli/antigravity-oauth-token` document, including its nested `token` object | Regenerate scoped personal Antigravity authentication settings; preserve necessary native metadata inside the token document |
| `codex-priv` | Complete `.codex/auth.json`, including authentication mode, token bundle, account identifier and refresh bookkeeping | Regenerate configuration with file-backed native credential storage |
| `mistral-priv` | Only the `MISTRAL_API_KEY` entry from `.vibe/.env` | Regenerate defaults; retain allowlisted provider/model selection only if customized |
| `codex-work`, `mistral-work` | Same provider-specific formats when authenticated | Disabled/unauthenticated profiles need no invented credentials |

Preserve complete supported native credential documents rather than extract only
the access token. Refresh material and native metadata are needed after that token
expires. Parse and validate the format without logging values; use file content
inside encrypted manifest entries to preserve the native serialization.

Claude's Linux credential location follows `CLAUDE_CONFIG_DIR`.
[Claude authentication documentation](https://code.claude.com/docs/en/authentication).
Google ADC is distinct from the credentials used by ordinary `gcloud auth login`;
the general gcloud login databases are not needed for the current Vertex harnesses.
[Google ADC documentation](https://docs.cloud.google.com/docs/authentication/application-default-credentials).
Codex explicitly supports transferring its file-backed cache to a trusted headless
machine. [Official OpenAI documentation](https://learn.chatgpt.com/docs/auth).
Vibe stores its setup key in `.vibe/.env`; general settings belong in `config.toml`.
[Mistral authentication documentation](https://docs.mistral.ai/vibe/code/cli/api-keys-profiles).


## Refresh after authentication changes

A static vault snapshot can become stale. If a native credential is revoked or
interactive authorization is required, first run the affected profile's `./login`
and complete the provider flow as the operator. A refresh job cannot complete
that authorization on the operator's behalf.

The separate `src/refresh_native_auth_vault.yml` playbook, exposed as AAP's
**Assistant Team Refresh Model Authentication** job template, captures selected
bootstrap credentials from the authorized source installation, validates only allowlisted material,
encrypts the updated snapshot, commits/pushes the companion repository and refreshes
AAP's ciphertext credential. It must refuse an incomplete capture rather than
silently replace previously stored authentication with a missing source entry.
Its maintenance credential uses a repository-scoped writable SSH deploy key,
verified host keys, the Vault password and a dedicated controller token. Provision
the template reproducibly with `src/configure_auth_vault_refresh.yml`; its role
README lists private input file paths and required existing AAP object IDs.
No operator-wide controller token is copied into the deployment target.

Run refresh when source bootstrap login/refresh writers are idle. Do not use it
to collapse project-role refresh streams into bootstrap profiles.

The snapshot contains the profiles actually captured; disabled or unauthenticated
profiles need no invented credentials. Work/private accounts remain separate.
Credentials missing from the snapshot still require operator login and recapture.
Restoring authentication does not silently enable a disabled profile or change
project assignments. Updating the vault does not overwrite existing destination
credentials; use a separately reviewed recovery operation for replacement.

## Bootstrap profiles and project roles are different streams

The model-environment login directories seed project-role homes once. Native
harnesses can later refresh their role copies independently. File timestamps or
token expiration alone cannot establish which divergent stream a provider accepts.
Vault refresh captures the explicitly chosen bootstrap source, not whichever
project-role cache happens to be newest. Project archives may contain role
credentials; keep them private and outside Git.

Codex recommends one auth cache per runner or serialized stream, preserving the
refreshed cache rather than repeatedly overwriting it with an old seed. Copying a
cache does not prove that independent refresh streams are interchangeable.
[Official OpenAI managed-auth guidance](https://learn.chatgpt.com/docs/auth/ci-cd-auth).

## Security boundaries

Capture and restore use a fixed provider-specific allowlist, format validation,
private `0700` directories, `0600` credential files and correct runtime ownership.
Unknown profiles, unsafe paths/symlinks, invalid provider metadata and malformed
native credentials are errors. Secret-bearing Ansible work uses `no_log: true`
and disabled diff; human-readable status contains metadata, never token contents.
Mistral dotenv material is parsed as data, never sourced or executed.

Do not capture complete profile directories, installed CLIs, caches, temporary
files, logs, workspaces, conversations, databases, SSH keys, broker tokens or
unrelated MCP/settings. Reproducible Ansible configuration supplies native hooks,
scoped HOME/XDG paths, trust settings and model-launch configuration; the secret
vault supplies only account authentication and the necessary allowlisted provider
settings. It never accepts legal terms or broadens native tool permissions.

The existing [host-to-host transfer](AUTH_TRANSFER.md) remains a separate optional
operation. It defaults to metadata-only preflight and needs explicit execution to
copy credentials; fresh deployment no longer depends on that transfer.

The maintenance controller token belongs to a dedicated non-administrator account
with Admin access to the deployment/authentication snapshot credential only. Its
GitHub SSH deploy key permits writes to the companion repository only. Repository
host keys are pinned. Maintenance credentials are injected only into the refresh
job; ordinary VM deployments receive ciphertext and the separate Vault credential.
Optional encrypted source connection bindings affect transient inventory only.
