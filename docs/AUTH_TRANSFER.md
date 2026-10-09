# Selective bootstrap authentication transfer

The operator-authorized deployment test can copy enabled bootstrap model profiles
from an existing installation to a fresh installation. This does not copy project
role credentials, sessions, conversations, tools, workspaces or complete workdirs.
Existing target credentials remain untouched. A saved credential does not prove
model access; bounded provider checks are a separate, explicitly authorized step.

## AAP workflow

Run `src/transfer_native_auth.yml` in a dedicated AAP job template after the fresh
environment deployment succeeds. Both source and destination must exist in the
job inventory and use the existing machine credential and dedicated runtime
account. Add only the destination to the `native_auth_destinations` inventory
group. Do not add the source to that group.

Keep environment-specific bindings in an Ansible Vault file. Select it with
`native_auth_transfer_config_file`; no model credentials belong in that file or
in Git, even encrypted. The file supplies these role variables:

| Variable | Meaning |
| --- | --- |
| `native_auth_transfer_source_host` | Authorized source inventory alias |
| `native_auth_transfer_source_profiles_root` | Absolute bootstrap profile parent on the source |
| `native_auth_transfer_source_environment_config` | Absolute source environment selection file |
| `native_auth_transfer_destination_profiles_root` | Absolute target `model-environments` directory |
| `native_auth_transfer_destination_environment_config` | Absolute target `conf/environment.conf` |
| `native_auth_transfer_runtime_user` | Existing dedicated account on both hosts |
| `native_auth_transfer_execute` | `false` for metadata-only preflight; explicitly `true` to copy |

Legacy source layouts are supported by these explicit bindings. No migration or
implicit path guessing occurs. Destination profiles must already be installed and
selected in their own environment definition; the transfer does not enable them.
Disabled, missing and invalid source profiles are reported separately.

## Exact future-vault material manifest

Paths below are relative to the named bootstrap profile. The private target report
`environment-logs/auth-transfer/latest.json` records restored/skipped/missing
profile states and the exact accepted file/field allowlist. It contains no secret
values, account identifiers, native documents or model entitlement claim. The
`vault_material_manifest` is the inventory of restored inputs that a later,
separately authorized external vault implementation must protect.

| Profile | Relative file | Accepted material |
| --- | --- | --- |
| `claude-priv` | `.claude/.credentials.json` | Complete supported native OAuth credential document |
| `claude-priv` | `.claude/.claude.json` | Only the OAuth account metadata and onboarding fields listed below |
| `claude-work` | `.config/gcloud/application_default_credentials.json` | Complete user ADC credential document |
| `claude-work` | `.vertex.json` | Exact Claude Vertex allowlist below |
| `gemini-work` | `.config/gcloud/application_default_credentials.json` | Complete independent user ADC credential document |
| `gemini-work` | `.vertex.json` | Exact Gemini Vertex allowlist below |
| `gemini-priv` | `.gemini/antigravity-cli/antigravity-oauth-token` | Complete native Antigravity OAuth credential document |
| `codex-priv`, `codex-work` | `.codex/auth.json` | Complete native subscription token document; API-key fallback is rejected |
| `mistral-priv`, `mistral-work` | `.vibe/.env` | Parsed `MISTRAL_API_KEY` only; every other dotenv entry is excluded |

Claude account metadata accepts only `accountUuid`, `emailAddress`,
`organizationUuid`, `organizationRole`, `workspaceRole` and `displayName` within
`oauthAccount`, plus `hasCompletedOnboarding`, `lastOnboardingVersion` and
`lastReleaseNotesSeen`. A legacy source `.claude.json` is read only when the scoped
`.claude/.claude.json` is absent, then written to the scoped canonical location.
Workspace trust, permissions, hooks, MCP settings and arbitrary configuration are
excluded. No Antigravity legal or data-use consent state is copied or accepted.

Claude Vertex fields are `CLAUDE_CODE_USE_VERTEX`, `CLOUD_ML_REGION`,
`ANTHROPIC_VERTEX_PROJECT_ID`, `ANTHROPIC_MODEL`,
`ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL` and
`ANTHROPIC_DEFAULT_HAIKU_MODEL`. Gemini Vertex fields are
`GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
and `GEMINI_MODEL`. The two ADC streams stay separate.

Missing Gemini-work auth selection and Codex file-backed credential-store settings
are generated from fixed reproducible defaults, without copying complete source
settings. Existing settings remain untouched. These defaults are configuration,
not secret vault material.

## Security and limits

The helper rejects unsafe owners, public credential files, symlinks, unknown
profiles, wrong provider installations and non-allowlisted payload fields. It
checks active host-native bootstrap writers before and after capture/restore and
checks source file identity while reading. Run when bootstrap login/refresh
commands are idle, and do not start one during transfer. Running project containers
use separate role credential streams and need not be stopped. This is not a global
credential lease across independent native harnesses.

Ansible runs secret-bearing tasks with `no_log` and `diff: false` for reports.
The capture travels in controller memory and protected module stdin; no persistent
payload staging file, archive or controller artifact is created. Normal temporary
Ansible module transport still applies. Helper-only temporary directories are
removed, and secret-bearing registered facts are discarded even on failure.

Target publication uses private directory traversal and atomic no-overwrite files:
`0700` directories and `0600` files. Every payload/endpoint is preflighted before
secret publication. Each profile publishes companion metadata before its final
credential, and rolls back only its own new files if publication fails. Earlier
successfully restored profiles remain valid if a later profile fails; inspect the
existing target before rerunning. No native session restarts, automatic model
calls, paid fallbacks, source authentication changes or external vault deployment
are part of this playbook.

Validation: synthetic six-provider/context roundtrips, missing-only preservation,
metadata-only preflight, malformed manifests, source/destination link attacks,
provider mismatch, dotenv rejection and per-profile failure rollback. Production
Ansible lint covers the role and playbook. Real transfer and entitlement results
must be documented separately after the fresh AAP deployment is ready.
