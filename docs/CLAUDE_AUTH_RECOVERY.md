# Explicit private Claude recovery

`src/recover_claude_auth.yml` restores one explicitly selected, known private
Claude session to the matching installed private account. This is separate from
Codex recovery and leaves that flow unchanged. Use a dedicated AAP job with
inventory group `native_auth_destinations`, endpoint machine access and Vault.
Set `claude_auth_recovery_config_file` to the encrypted definition, such as
`../vars/claude_auth_recovery.vault.yml`. Authentication files never enter Git,
even encrypted; the tracked Vault contains only environment bindings.

Bindings use the `claude_auth_recovery_` prefix: `source_host`, `source_role`,
`source_home`, `source_metadata`, `destination_profiles_root`,
`destination_environment_config`, `runtime_user`, `report_directory` and
`execute`. Source home must be exactly the bound role's
`accounts/claude-priv/home`; source metadata must be explicitly bound to that
home's `.claude.json`. No blind metadata-location fallback occurs.

`execute` defaults to false. Validation checks both endpoints and matching
account/organization metadata without modifying the destination. Explicit true
permits replacement of only the destination's existing
`.claude/.credentials.json`. Destination `.claude/.claude.json` is read and
preserved; source metadata and the archived credential are also preserved.

The source profile must declare Claude/private flavour and account. All account
scope directories and files must be private and owned by the runtime user;
path traversal refuses symlinks. Destination must be a canonical enabled
claude-priv profile. Account UUID and organization UUID must both match the
restored destination account metadata. Claude's opaque credentials are validated
using their native document structure, not interpreted as JWTs. Candidate
refreshToken must exist; an expired access token is permitted so a later native
request can perform its normal refresh. No refresh or model request happens
inside the recovery playbook. Matching metadata is a structural consistency
check, not cryptographic proof of the opaque credential's identity or usability.

Native or container writers touching either account home cause refusal. Keep the
scopes stopped throughout; external operators can still race a new writer after
a check. Protected no_log/diff:false Ansible transport passes only the selected
credential through memory. Private target-local staging and atomic replacement
preserve the existing credential on validation failures; repeating the same
recovery reports unchanged. No whole home, permissions, tools, MCP configuration
or work-account fallback is copied.

The target-local `environment-logs/auth-recovery/claude-priv.json` records safe
profile, source stream `explicit_archived_private_connector`, outcome and
unverified model access. Account identifiers and tokens are excluded. A separate
explicitly authorized bounded native check must establish usable access afterward.

Synthetic tests include real disposable Ansible validation/replacement/rerun,
account mismatch refusal, unchanged source and destination account metadata,
organization mismatch, missing refreshToken, wrong work context, fixed metadata
binding and private-file/link checks. They make no provider requests.

A failed native authentication request can clear both target token strings while
retaining the native OAuth record. Recovery accepts that target-only state when
the document contains only claudeAiOauth and exactly accessToken/refreshToken
(empty strings), expiresAt/refreshTokenExpiresAt (nonnegative integers), scopes
(a list of strings), and subscriptionType/rateLimitTier (strings). All existing
account/context/permission/writer checks still apply. Source candidate checks are
unchanged. Other empty or malformed documents, additional API-key records and
missing fields are refused. Helper refusal diagnostics expose only a fixed
allowlist of static error codes; protected Ansible logging remains enabled.
