# Native model authentication replication

Status: the operator superseded the outside-all-Git restriction. Encrypted
model-authentication snapshots are now authorized in the private companion
assistant-team-secrets repository only; the application repository still excludes
model credentials. Its initial capture (`9058235`) includes the explicitly chosen
source bootstrap state and the existing deployment definition, encrypted with the
external password file and verified by exact private decryption comparison.

No provider refresh/model probe ran during capture. Expiration/revocation remain
possible, and no automatic restore integration is implied. The reusable exporter
is still an unpublished draft. Its previous outside-Git output guard requires a
reviewed policy update before reuse with the companion repository; do not silently
bypass it. The historical external-vault proposal below remains design context,
not the current storage-location requirement.

## Pushed implementation and resume reference

Native login wrappers, isolated account contexts, Vertex helpers and saved-auth
reporting are already implemented in `src/roles/native_auth`,
`src/roles/vertex_auth`, `src/roles/antigravity_auth` and the project framework.
These implement local login and runtime seeding, not a central secret vault.

The legacy-layout deployed baseline is `11d5723` (0.21.8). Source-only layout
implementation is on `feature/installation-prefix`: `2cf98a7` (0.22.0), with
decision history `83850a6` (0.22.1) and terminology documentation `d7f5e4d`
(0.22.2). It uses `PREFIX/ac-agents/model-environments` and project-local
configuration. It has not been deployed; executable layout migration remains
future work. The independent broker IPC fix is separate from authentication
replication and does not create a vault.

When resuming, recheck the current deployed layout and selected credential
streams, then use the manifest and validation plan below. Do not treat these
commit references or a previous structural audit as proof that saved credentials
remain valid. No private account identifiers or credential contents belong here.

## What belongs in the external vault

Use one Ansible Vault-encrypted `agent-secret-vault.yml`, stored outside every
Git checkout and outside the replaceable installation. Its backups must also stay
outside Git. AAP holds the decryption password and access to the storage location;
the Vault password credential alone does not contain the authentication payload.

Paths below are relative to a selected native credential home. For a fresh
installation this is `PREFIX/ac-agents/model-environments/PROFILE`; existing
deployments retain their old profile location until an explicit migration.

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

Antigravity's native file format was confirmed by local structural inspection.
Successful authentication transfer to a second installation remains unverified;
the native login file does not establish agents-connector adapter support.

## Bootstrap profiles and existing project roles are different sources

The login directories seed project-role homes once. A native harness can later
refresh its role copy independently. An observed archived role credential differed
from its login-directory seed; file equality and timestamps cannot tell which
divergent token stream the provider currently accepts.

For a new environment, capture explicitly selected bootstrap profiles. For an
existing-project migration, also capture each selected role's current credential
home under its logical project/role/profile identity. Never collapse different
copies into one profile entry based on modification time or token expiry.

The manifest should contain:

- A schema version, snapshot revision and capture time.
- Bootstrap entries keyed by account profile, with a fixed relative-file allowlist.
- Optional project-role entries keyed by logical project, role, account profile
  and login generation, with the same provider-specific allowlist.
- Provider configuration and native credential bytes for each selected entry.
- A declared purpose: bootstrap, migration or recovery. Unknown paths/entries fail.

Real project/account identifiers and all secret contents belong only inside the
encrypted manifest. Use synthetic placeholders in documentation and tests.

Codex recommends one auth cache per runner or serialized stream, preserving the
refreshed cache rather than repeatedly overwriting it with an old seed. Copying a
cache is not proof that multiple independently refreshing clones can safely share
one login. [Official OpenAI managed-auth guidance](https://learn.chatgpt.com/docs/auth/ci-cd-auth).

## What stays out

Do not capture whole profile directories. Exclude CLI installations, caches,
temporary files, logs, workspaces, conversations, project databases, SSH keys,
broker tokens, MCP secrets and complete unrelated native settings. These belong
to reproducible Ansible configuration or a separate project backup, not the
model-authentication vault. Do not follow symlinks to collect external secrets.
Project archives retain role authentication too: protect them like credentials,
and keep complete project backups outside Git as well. Their contents are broader
than the authentication-only manifest described here.

Enabled-profile selection and role assignments are environment/project
configuration. Ansible or a separate configuration backup must reproduce them;
restoring credentials must not silently enable a disabled profile or launch it.

## Proposed capture and restore behavior

1. The operator selects bootstrap profiles and any project-role streams to save.
   Require the selected native writers to be stopped for a migration-ready
   snapshot and remain quiescent throughout capture, rather than merely checking
   once. Refuse active writers without automatically stopping unrelated work.
2. Collect only allowlisted material through protected transport, validate it,
   encrypt promptly and atomically update the external vault. Retain a known-good
   previous revision; conflicting updates must not overwrite newer snapshots.
3. Restore the selected entries into a new or empty installation, after its native
   harnesses are installed. Use directories `0700`, files `0600`, correct ownership
   and atomic writes. Regenerate scoped HOME/XDG/provider settings for the new paths.
4. Seed missing credentials only. Existing newer runtime credentials remain intact;
   replacement requires an explicit recovery/migration selection. Leave services
   stopped. Report saved credentials with model access unverified.
5. Persist refreshed state at a later safe capture point. A static encrypted
   snapshot can become stale; native refresh is responsible for renewal. Revocation
   or expiry can still require another interactive login.

Secret-bearing Ansible tasks require `no_log: true` and disabled diff. Logs contain
only action, outcome, revision and correlation metadata. Decrypted temporary files
must be private and cleaned on success or failure. AAP must fetch the encrypted
bundle through an explicit supported transport; do not assume a host-local file
is automatically visible inside its execution environment.
Read Mistral's dotenv entry as data; never source or execute a credential file.
The eventual parser must match the native supported quoting format without shell
expansion and reject unsupported content safely.

## Remaining validation before implementation

Test synthetic round trips for every adapter, schema/path rejection, private file
modes, missing-only restore, snapshot conflicts and secret-free logs. Then test
each provider's actual portability separately with explicit authorization; do not
infer entitlement from the presence of a credential file or switch to a paid API
fallback. Capture/restore automation and central snapshot refresh are future work.
