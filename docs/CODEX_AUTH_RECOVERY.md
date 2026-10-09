# Explicit same-account Codex recovery

Use `src/recover_codex_auth.yml` only when an installed private Codex bootstrap
cache is rejected and a specifically selected, known working archived builder
session belongs to the same account. This is not selection by newest timestamp,
an automatic login refresh, or generic project-to-bootstrap copying.

A dedicated AAP job uses inventory group `native_auth_destinations`, source and
destination machine access, and a Vault credential. Set
`codex_auth_recovery_config_file` to the encrypted binding definition. The provided
`vars/codex_auth_recovery.vault.yml` contains only encrypted environment bindings;
model authentication never enters Git, even encrypted.

| Setting | Meaning |
| --- | --- |
| `codex_auth_recovery_source_host` | Explicit source inventory alias |
| `codex_auth_recovery_source_role` | Archived builder profile directory containing profile.json |
| `codex_auth_recovery_source_home` | Exact role/accounts/codex-priv/home |
| `codex_auth_recovery_destination_profiles_root` | Canonical installed model-environments parent |
| `codex_auth_recovery_destination_environment_config` | Destination environment.conf selection |
| `codex_auth_recovery_runtime_user` | Existing dedicated runtime account on both endpoints |
| `codex_auth_recovery_report_directory` | Private destination-local metadata audit directory |
| `codex_auth_recovery_execute` | False by default: validation only; explicit true allows replacement |

Both endpoints are checked even during validation-only runs. Source metadata must
bind Codex flavour, private auth directory and private account profile. Source
role/account directories and auth file must be private and owned by the runtime
account; traversal never follows symlinks. Destination must be an enabled canonical
private Codex installation with an existing coherent ChatGPT cache. Candidate and
existing target account ID, token subject and issuer must match. The candidate
access token must be unexpired. These structural checks do not establish server
acceptance or model entitlement.

Native writers and running containers mounting either credential scope cause
refusal. Keep both scopes stopped throughout the operation; checks cannot prevent
an unrelated operator from starting a new writer immediately afterward.

Protected `no_log`, `diff: false` Ansible transport carries only `.codex/auth.json`
in memory. The helper creates a private target-local temporary file and atomically
replaces the existing target credential after rechecking its contents and writers.
No whole homes, MCP configuration, roles, permissions or other model files are
copied. Existing source data and the archive remain unchanged. Failed validation
preserves the target; repeating a successful recovery reports unchanged. There is
no target backup containing credentials and no automatic model call.

`environment-logs/auth-recovery/codex-priv.json` records only profile, named source
stream `explicit_archived_builder`, validation/replacement status and unverified
model access. Account identifiers, token values and token digests are excluded.
After an explicitly executed recovery, perform a separately authorized bounded
native access check before claiming success.

Validation includes actual disposable Ansible validation/replacement/rerun and
mismatched-account refusal, source preservation, wrong-context/private-file/link
refusal and container writer checks. Fixtures use synthetic token documents and a
model-free Podman stand-in; they make no provider requests.
