# native_auth

Install eight isolated native work/private profile prefixes and scoped launchers.

## Interface

native_auth_native_auth_dirs is the typed profile catalog; containers.runtime_user and assistant_source_user identify runtime/source accounts.

## Dependencies and platform

Native images and broker image extensions must already exist; no provider authentication is required.

## Safety, idempotence and check mode

Retains completed programs and validates all CLI versions on recovery. Live export/version checks are required. Login is an explicit operator action.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.

Personal Gemini invokes the separate `antigravity_auth` role for the supported
native Antigravity CLI. Vertex Gemini remains unchanged. Operator login is ready
after deployment; personal Antigravity team routing remains explicitly blocked
until its adapter is implemented. See that role README for file-storage limits.

The `native_auth_helpers` tag refreshes login reporting and scoped launchers only,
without reinstalling providers or touching credentials. Antigravity's native nested
OAuth token structure is supported. A TUI interrupt with newly persisted valid
evidence is reported as saved/unverified; cancellation without new evidence stays
failed/cancelled. Unchanged existing evidence is described separately. No outcome
can claim verified model entitlement without an explicit model check.

Managed Codex wrappers pass `-c check_for_update_on_startup=false` for the pinned
Ansible-managed installation. CLI version changes are made through deployment,
not interactive self-update prompts. Login and model permissions are unaffected.
