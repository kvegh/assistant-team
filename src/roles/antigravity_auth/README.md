# antigravity_auth

Install the official pinned Linux x64 Antigravity native CLI into the personal
Gemini profile. No desktop, GNOME Keyring, libsecret or authentication is installed.

## Interface

`antigravity_auth_profile_home` and `antigravity_auth_runtime_user` identify the
existing operator-owned profile. Version, URL and SHA-512 checksum are pinned
role defaults. `native_auth` calls this role and maintains shared scoped launchers.

## Platform and safety

The environment validation supports RHEL-family 9 x86_64. The native CLI uses its
normal SSH/container file-storage fallback. Profile directories are 0700 and
launchers use umask 077; tokens are not encrypted at rest. These permissions do
not prevent root, sudo or another process running as the same account from
accessing files. Authentication belongs to the operator; deployment never logs
in, reads existing authentication or copies it to another account.

## Idempotence and validation

Checksum downloads, archive extraction and metadata converge without deleting
old Gemini settings or credentials. Login and model checks remain explicit
operator actions. Local CLI version/help checks require the installed executable
and therefore a fresh installation is not fully check-mode compatible. Personal
Antigravity is login-ready, but agents-connector's Gemini ACP adapter is not yet
compatible; project role selection rejects it until an adapter is implemented.
