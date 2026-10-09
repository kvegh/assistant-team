# Dedicated Codex sandbox policy

## Codex nested sandbox on SELinux

Codex role containers use a dedicated constrained SELinux domain on supported
RHEL hosts with SELinux enforcing. The separate `codex_sandbox` role loads its
reviewed CIL policy through the certified RHEL system roles collection and
explicitly activates policy changes. Existing standard container domains remain
unchanged. Rootless containers retain a read-only root, dropped capabilities,
no-new-privileges, seccomp and MCS isolation; native workspace-write permissions
and protected workspace paths remain enforced.

The domain preserves relevant original container policy access and adds only
private nested devpts mounting and device/tmpfs filesystem remount permission
needed by the native Bubblewrap sandbox. These SELinux grants are filesystem-type
wide rather than path or remount-direction specific; rootless user/mount
namespaces and locked inherited read-only mounts constrain their effect.
They do not grant host capabilities, disable labeling, or approve execution
outside the native sandbox. A guarded repair can replace only an explicitly
selected Codex builder and resume its verified saved conversation; other roles,
authentication and workspace content are preserved.

Validation ran the actual native sandbox without inference: shared workspace
writes succeeded; writes into the writable outer home and protected `.git`,
`.agents`, `.codex` and `.aws` paths failed, and network socket creation failed.
Outer capabilities stayed zero, no-new-privileges and seccomp stayed enabled,
and the dedicated domain retained nonzero MCS categories.
