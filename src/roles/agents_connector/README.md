# agents_connector

Source-only passive readers are not deployed: four worker identities participate;
summarizer/observer use private lifecycle-only callbacks and raw read-only contexts,
with drafts published to operator-only outputs. No feedback reaches the team.
Host helper files stay in routing, outside worker-mounted helper binaries.
Native acceptance and stopped migration require explicit operator approval.

Install the pinned stock broker, restricted routing and native tmux image extensions.

## Interface

agents_connector_* defaults define pinned distribution and generic profiles; assistant_source_user identifies the credential-free source image store.

## Dependencies and platform

podman_host and agent_images. Resolves its account paths separately.

## Safety, idempotence and check mode

Immutable artifacts/config are managed idempotently; editable prompt seed uses force:false. Existing projects and account credentials are preserved.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.

Prompt rendering accepts new `[Role: Name]` markers and existing `# Role:` headers.
New-format `#` lines are author comments, removed before role extraction is delivered
to native harnesses. Each supported role must appear once; only its own active text
and the shared project goal are rendered. Blank sections have no example fallback.

## Focused image repair

The tmux image extension includes `procps`: Codex's managed app server needs
`ps` even when its CLI version check succeeds. Image verification executes process
inspection in an isolated credential-free container before any selected repair.
Use the `connector_images` tag with `agents_connector_image_flavours: [codex]`
and `agents_connector_image_force: true` to rebuild only Codex through the certified
image module. Other images and running containers remain unchanged.

The optional `connector_codex_repair` tag requires an explicit
`agents_connector_repair_codex_project`. It refuses an active or non-Codex builder;
only a dead native pane's container is replaced. Mounted home, authentication and
workspace files remain in place. The new native session receives no initial task
prompt. Do not use this operation as a general project restart.

Successful repair restores the launch marker used by event wake-up only after
native launch succeeds. To recover missing bookkeeping for an already live Codex
builder, set `agents_connector_repair_codex_restore_marker_only: true` with the
explicit project and run only `connector_codex_repair`. This checks that tmux has
a live native Codex command and touches its marker without rebuilding images,
replacing containers or respawning any pane. Dead or idle-shell panes are rejected.

On SELinux hosts the gateway assigns `system_u:system_r:container_t:s0` only to
each newly created listening socket. Existing policy permits the container client
to connect to that socket; the host gateway process is not relabeled. The code
restores the previous thread-local socket creation context immediately, preserves
private MCS mount/inode labels and role token checks, and fails on labeling errors.
No custom allow rule, SELinux boolean or enforcement exception is installed.
This uses the system libselinux library already available on the supported host.

The project container service requires the gateway. Applying new code to a live
listener requires coordinated activation; do not issue an unplanned gateway
restart that can stop dependent native sessions.

Use the focused `connector_ipc` tag to install only the routing utility and its
path facts. It does not restart units, launch native sessions, rebuild images or
rewrite prompts/authentication. Activation of a currently running gateway remains
a separate coordinated operation.

Codex role launch passes `-c check_for_update_on_startup=false` and fresh generated
TOML includes the corresponding top-level setting. Existing TOML remains
byte-for-byte unchanged. Updates must come through the managed image build; a
read-only container must not try an interactive global npm update. This policy
does not modify sandbox, approval, MCP or authentication settings.

Codex container launches use the installed CLI's `--no-daemon` mode. A role's
container and tmux session already own its lifecycle; a reused shared daemon is
unnecessary here. Startup verification found that direct mode reached the normal
prompt after operator authentication/trust steps where shared-daemon mode still
showed sign-in. This is scoped to containers, not host wrappers, and does not
automatically authenticate or trust hooks/workspaces.

Gemini MCP result compatibility is installed by this role as `bin/mcp-results.py`
and selected only for Gemini's generated MCP command. It preserves stock text
results and adds object structured-content envelopes for JSON arrays/scalars.
The `connector_mcp_results` tag copies this adapter and routing code without
restarting sessions; generated configurations take effect after initialization
and a separately authorized native MCP reconnect.

For existing teams, supply `agents_connector_repair_gemini_project` and
`agents_connector_repair_gemini_role` with the `connector_mcp_results` tag.
This opt-in action repairs only a recognized stock MCP command, saves a private
backup and preserves other native settings. It does not restart the role; the
operator must reconnect MCP explicitly to activate it in an existing process.

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
Installation paths resolve through `install_layout`: `assistant_install_prefix` is the destination parent (default runtime HOME), `assistant_install_root=PARENT/ac-agents`, profiles are in `model-environments` and connector tooling in `agent-connector`. Runtime HOME remains unchanged for Podman/systemd. This source-only layout refuses legacy environments until controlled migration; no current deployment was changed.

Fresh prefix installations resolve private native providers under `model-environments`; private-reader outputs remain outside the team workspace.

## Native Mistral images and hooks

The default image set includes the pinned Mistral Vibe 2.26.0 harness. Its connector
image is named `assistant-connector-mistral`; the credential-free foundation image
retains its existing `assistant-team-vibe` name. The certified Podman module extends
that existing image with tmux and runtime helpers, without changing live containers.
A focused `connector_images` run with `agents_connector_image_flavours: [mistral]`
builds only this adapter. The `connector_mistral` tag installs its standard-library
configuration/hook helper and matching routing utility without restarting services.
Mistral may be selected for the four visible roles using separately enabled
`mistral-work` or `mistral-priv` accounts. Private readers and restricted connectors
remain Claude-only; defaults and account enablement are unchanged. Deployment does
not authenticate accounts or prove model entitlement.
