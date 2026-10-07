# assistant-team

Private project for an assistant team. Application requirements are still being defined.

## Security

Repository privacy does not replace encryption. Store all environment-specific
data, including usernames, hostnames, addresses, credentials, and tokens, in
Ansible Vault-encrypted files. Plaintext documentation and examples must use
generic placeholders. Never commit the Vault password file or decrypted output.

## Vault setup

Ansible and Git must already be available. Run commands from this repository.
`ansible.cfg` uses the existing workspace password file at `../../vpf`.
The password file stays outside this repository; do not copy it here.
On another checkout, override the location with `ANSIBLE_VAULT_PASSWORD_FILE`.
Ansible uses a project-specific temporary directory under `/tmp` for local work.

```bash
ansible-vault edit vars/environment.vault.yml
ansible-vault encrypt path/to/environment-specific.yml
ansible-vault view vars/environment.vault.yml
```

The last command displays plaintext locally; do not capture or commit its output.

## Layout

- `vars/environment.vault.yml`: encrypted environment configuration.
- `src/deploy_linux_vm.yml`: calls the provisioning, guest verification, and update roles.
- `src/roles/linux_vm/`: image cloning, cleanup, identity reset, boot, and guest discovery.
- `src/roles/linux_guest/`: guest access, identity, resource, and cleanup verification.
- `src/roles/linux_updates/`: RHEL registration, full updates, reboot, and result publication.
- `AGENTS.md`: project access and reproducible-change requirements.
- `src/configure_assistant_containers.yml`: certified rootless Podman foundation and four native images.
- `src/inspect_container_host.yml`: optional read-only controller preflight.
- `collections/requirements.yml`: pinned certified collection dependency.
- `docs/architecture.md`: accepted application design awaiting implementation.
- `tests/test_deployment.py`: launch-validation tests without VM changes.
- `tests/test_clone_cleanup.py`: checks that cleanup preserves protected accounts.
- `tests/test_identity_reset.py`: identity reset with a missing legacy D-Bus directory.
- `ansible.cfg`: local Vault password-file configuration.
- `design_decisions_history.md`: decisions and implementation commit references.

Add application source in `src/`, tests in `tests/`, and static assets in `assets/`
when implementation begins. No application build, runtime, test, or formatting
toolchain has been selected yet.

## Infrastructure

`src/deploy_linux_vm.yml` adapts the existing golden-image Linux VM setup
playbook for the **Generic Linux VM Deployment** AAP job template. It provisions
one VM, waits for its DHCP lease by MAC address, and verifies authenticated
Ansible access, Linux, the hostname, CPUs, and available memory. It does not install AAP.
Memory verification checks the exact allocation in libvirt and accounts for the
guest kernel's crash-recovery reservation when checking usable RAM. Controller
artifacts report allocated RAM, guest-visible RAM, and the crash reservation separately.

Launch variables are `vm_name`, `vm_vcpus`, `vm_memory_mb`, and `vm_disk_gb`.
Defaults are 2 vCPUs, 4096 MiB RAM, and a 40 GiB disk. The VM name defaults to
the encrypted configuration. Environment settings and guest credentials are
under `provisioning` in `vars/environment.vault.yml`. AAP must supply the Vault
and hypervisor machine credentials; its project needs a GitHub source-control
credential with read access to this private repository over HTTPS.

Provisioning refuses an existing VM or disk and refuses shrinking the golden
image. A failed deployment preserves resources for investigation; it does not
automatically delete or overwrite them. Increase `vm_disk_gb` if the golden
image is larger than the requested disk. Disk resizing changes the virtual disk
capacity; guest partition and filesystem growth are not performed by this playbook.

Before booting, provisioning removes AAP installer artifacts under `/opt/sources`,
the unused AAP service account and its home, associated lingering and sudo entry,
package caches, inherited shell histories, and logs from the cloned disk. The
automation access account is preserved. Configure `provisioning.aap_service_user`
in Vault; cleanup refuses to remove root, the automation account, or an account
with an unexpected home directory. The shared source image is never customized.
Guest verification checks that installer artifacts and the AAP account are absent.

After boot, the job registers RHEL with the existing activation key if needed,
enables BaseOS and AppStream, updates every installed package with DNF, and
reboots if packages changed. It reconnects and requires `dnf --refresh check-update`
to return no pending updates before publishing success. Subscription details are
encrypted under `provisioning.rhsm_org` and `provisioning.rhsm_activation_key`.

If provisioning succeeded but guest configuration failed, rerun the same template
with the `guest_config` job tag and the same VM name. This discovers the existing
guest through libvirt and resumes guest configuration without cloning or replacing
its disk. The template must allow job tags at launch and must not use a hypervisor-only
host limit, because the later play runs against a dynamically added guest.

If offline customization failed before a VM was defined, use the `offline_recovery`
job tag to resume customization and boot from the existing disk without repeating
the copy or cleanup. Recovery refuses to customize a disk associated with a defined
VM. For that identity task alone, `vm_identity_diagnostics: true` reveals its command
result temporarily; other task output and guest credentials remain protected.
The diagnostic default remains off.
For guest resource mismatches, `vm_guest_verification_diagnostics: true` reveals
only the verification assertion and basic OS, hostname, CPU, and memory values.
Guest connection and subscription credentials remain protected.

The golden image supplies the guest access configuration. Provisioning resets
the cloned machine identity and host keys. Logs are protected with `no_log`;
verified VM details are stored in AAP job artifacts. Keep controller access
restricted, and record deployment details in the encrypted configuration file.

## Deployment status

The private repository synchronized successfully to its AAP project using a
repository-scoped GitHub credential. The Generic Linux VM Deployment template
has deployed and verified the first guest with 2 vCPUs, 4 GiB allocated RAM,
and a 40 GiB virtual disk. Installer cleanup, authenticated access, RHEL
registration, the full DNF update, reboot, and the final no-pending-updates check
all succeeded. Local syntax checks and all eight tests pass.

The earlier controller outage was attributed by the user to hypervisor memory
starvation; access recovered without replacing the AAP token. Controller
references, the approved hostname, address, and verified guest details remain in
the encrypted configuration. Application design has not started yet.

## Validation

Check that encrypted configuration decrypts without displaying its contents:

```bash
ansible-vault view vars/environment.vault.yml >/dev/null
git diff --check
ansible-playbook --syntax-check -i 'localhost,' src/deploy_linux_vm.yml
python3 -m unittest discover -s tests -v
```

The tests reject unsafe names, invalid sizing, and multiple hypervisor targets
before remote work, and verify cleanup account guards without deleting files.
Python's standard library runs the suite; Ansible must already
be installed. Use `ansible-lint src/deploy_linux_vm.yml` when a working installation
is available. Local validation does not install additional dependencies.

## Project change workflow

Direct SSH with sudo is authorized for work on the project VM. Every lasting
configuration or design change must also be represented in separate Ansible
roles called by the project playbook, so a fresh deployment reproduces the
result. Update the README and decision history for the final design, commit and
push the automation and README together, and record the implementation commit
reference in the decision history. Interim experiments and retries do not need
individual decision entries. All environment-specific data remains encrypted.

The main conversation focuses on building and design. One reusable background
subagent handles settled decisions sequentially: configuration changes, Ansible
roles, documentation, validation, commits, and pushes. Independent design discussion
can continue while that work runs. A design agreement remains implementation
pending until the subagent reports it implemented and verified; dependent work
waits for that result. Completion notices are brief, and blockers requiring a
decision or approval return to the main conversation. The same security,
monitoring, and approval requirements apply to background work.

## Native assistant container foundation

`src/configure_assistant_containers.yml` calls separate `podman_host` and
`agent_images` roles for the deployed guest. The foundation prepares reusable
rootless Podman images for Claude Code, Codex CLI, Mistral Vibe, and Gemini CLI.
Certified `redhat.rhel_system_roles` 1.120.5 supplies the Podman host role and
`redhat.rhel_system_roles.podman_image` image builds. Obtain this collection from
the existing certified Automation Hub distribution; no community substitution
is configured. `collections/requirements.yml` pins the certified version.
CLI versions and base image digests are pinned in the image role defaults;
upgrades require an explicit version change and rebuild. For a Containerfile or
base change that keeps the same CLI version, set `assistant_rebuild_images: true`
for that deployment. The role preserves existing images on ordinary reruns and
checks free space before new builds. Rootless user lingering keeps the user
manager available for engine cgroups. A service override scoped to that account
delegates CPU, memory, and process controllers so container limits are enforced;
no model agents run as background services. Each image contains the
provider's native harness, rather than a custom replacement for its agent loop.

A dedicated password-locked runtime account, configured in Vault as
`containers.runtime_user`, has no sudo access. Each instance has a separate
workspace and persistent home directory, which includes its native authentication
and session state. Container processes run unprivileged with dropped capabilities,
no new privileges, a read-only image filesystem, resource limits, and only the
instance's two directories mounted. No host engine socket, general home directory,
SSH directory, or sudo access is exposed to agents. The engine's default seccomp
policy and SELinux private mount labels remain enabled. Outbound network access
is available for provider authentication and model calls; this is not a network
allowlist. No inbound ports or host loopback access are configured.

The launcher accepts role instructions and a participant roster supplied by the
operator. The operator roster is a JSON list of objects containing `role`,
`responsibility`, and boolean `worker_visible`. Every working role sees all
collaboration roles whose visibility is true. Observer/evaluator entries must
have visibility false: their identities and responsibilities are omitted from
worker instructions, and the source roster is not mounted into containers.
The roster grants no shared data, credentials, or communication capability.
Keep real role assignments and sensitive instructions in encrypted repository
inputs or protected operator files. No role roster is hardcoded.

Observer/evaluator access and reports will be separate from worker-readable
communications. Working agents receive no evaluation instructions or evaluation
reports. Company/private context and access boundaries remain in force. This
foundation implements instruction visibility only; a central discussion service,
observer runtime, report storage, and automated reassignment are not implemented.

Run these commands as the configured runtime account; use generic names locally:

```bash
assistant-instance init example-one codex --role-file /path/to/role.md --participants-file /path/to/participants.json
assistant-instance run example-one version
assistant-instance run example-one help
assistant-instance run example-one login
assistant-instance run example-one interactive
assistant-instance run example-one prompt 'Summarize the material in this workspace.'
```

Each instance uses a deterministic container name, preventing two concurrent
processes from sharing that instance's writable state. Different instances can
run concurrently. Defaults allow read-only assistant work: Codex uses its native
read-only sandbox, Claude print mode exposes reading/search tools only, Vibe
explicitly selects a custom read-tool agent in both interactive and programmatic
mode, and Gemini uses a read-tool allowlist. Interactive Claude retains its native
approval prompts. Permission bypass flags and arbitrary container flags are not
accepted by the launcher. Role text does not replace permission enforcement.

### Reproduce the foundation

Use Ansible 2.15 or later with the pinned certified collection installed through
an authenticated certified Automation Hub source. The collection has no additional
collection dependencies. Keep Hub endpoints and tokens in protected local
configuration or controller credentials. Configure the SSH connection to preserve
existing crypto policy and verify the guest host key; do not disable host checking.

```bash
ansible-galaxy collection install -r collections/requirements.yml
ansible-playbook --syntax-check -i 'localhost,' src/configure_assistant_containers.yml
ansible-playbook -i 'localhost,' src/configure_assistant_containers.yml
```

The first command assumes the approved certified Hub source is already configured;
its default community source is not a substitute. Set `ANSIBLE_COLLECTIONS_PATH`
when using a task-specific installed collection directory. The playbook loads
connection and runtime account details from Vault and creates its guest inventory
in memory. Local SSH control sockets use `/tmp`, keeping agent-managed home
configuration untouched.

The foundation verifies the native version, offline help, process UID, image
filesystem protections, absence of sudo, and persistence/isolation across two
instances per flavour. Validation containers use no network and no credentials;
temporary validation data is removed after the checks.

### Native role and authentication mechanisms

| Harness | Role instructions | Authentication prepared for operator |
| --- | --- | --- |
| Claude Code | Workspace `CLAUDE.md` | Native `claude auth login`; state in isolated home |
| Codex CLI | Workspace `AGENTS.md` | Native `codex login --device-auth`; isolated `.codex` |
| Mistral Vibe | Custom `.vibe/agents/instance.toml` and prompt | Native startup authentication flow; isolated `.vibe` |
| Gemini CLI | Workspace `GEMINI.md` | Native startup sign-in flow; isolated `.gemini` |

Provider access must be supplied separately for every intended instance. Images
contain no credentials and do not inherit this development session's credentials.
Login commands are operator actions; deployment and smoke tests do not sign in,
accept terms, or make model requests. For Vibe and Gemini, `login` starts the native
CLI authentication flow; exit after completing authentication. Headless methods
and subscription eligibility depend on the provider and account. Supply API
credentials through protected native instance configuration when applicable, never
in image build arguments, plaintext Git files, or command-line literals.

Official references: [Claude CLI](https://code.claude.com/docs/en/cli-reference),
[Codex CLI](https://learn.chatgpt.com/docs/codex/cli),
[Codex instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Vibe agents](https://docs.mistral.ai/vibe/code/cli/agents),
[Vibe installation](https://docs.mistral.ai/vibe/code/cli/install-setup),
[Gemini context](https://geminicli.com/docs/cli/gemini-md/), and
[Gemini authentication](https://geminicli.com/docs/get-started/authentication/).

### Foundation implementation status

All four images are built on the guest: Claude Code 2.1.292, Codex CLI 0.160.1,
Gemini CLI 0.63.0, and Mistral Vibe 2.26.0. Native offline version/help checks and
isolated-instance persistence checks passed. Kernel-enforced CPU, memory, and
process limits, zero effective capabilities, no-new-privileges, and read-only root
mounts also passed live checks. All fifteen local tests pass. Rootless engine verification passed;
ordinary reruns reuse the existing images. Filesystem capacity was sufficient,
so no partition or filesystem expansion was needed. Host trust was established
with the user's explicit approval for this fresh demo guest and subsequent SSH
connections require that recorded key.

Provider authentication and model sessions remain pending operator setup. No
credentials were inherited and no model inference, paid API call, integration,
or external messaging was performed. The existing VM deployment remains verified.
No orchestrator, discussion service, observer, or persistent agent listener is
configured by this foundation.

`src/inspect_container_host.yml` calls a read-only preflight role through AAP.
It publishes the guest's SSH public key, root filesystem capacity, storage layout,
and installed container/system-role packages in protected controller artifacts.
Use this trusted controller result to establish agent-side SSH trust, and check
capacity before builds. The preflight does not update or install packages.

## Next design agreements

[Architecture agreements](docs/architecture.md) record the accepted SQLite
persistence direction, separate summarizer/orchestrator responsibilities, and one
observer producing distinct output and design evaluations. Observer access and
reports remain outside worker-readable communications. These application
components are agreed design work awaiting implementation; the container
foundation does not deploy them. Subscription exhaustion must pause work without
automatically switching to paid API usage.

### Persistent, attachable native sessions

The selected Agents Connector setup below implements continuously running rootless
Podman containers with inside-container tmux for the five visible Claude/Codex/Gemini
profiles. Native authenticated sessions require operator login and launch. The
original foundation launcher remains available for short-lived isolated commands;
Vibe is not included in the selected connector setup.

Existing communication software is preferred over a new message service. Timed
inbox polling is rejected. The selected integration uses stock event-driven wake
and fixed tmux notices, with content delivered through authenticated MCP/hooks.
Generic native inbound transport across all harnesses remains unverified.

## Agents Connector setup

`src/configure_agents_connector.yml` creates the dedicated password-locked,
unprivileged account recorded in Vault and calls the existing `podman_host` role
plus the separate `agents_connector` role. Its home contains the upstream binary,
rough role prompts, isolated native homes/workspaces, private SQLite broker state,
and constrained routing utilities. Upstream release 0.1.0 is checksum pinned.
The existing Claude/Codex/Gemini images are streamed into this account's rootless
store and extended with tmux; Mistral Vibe is excluded from this setup.

```bash
ansible-playbook --syntax-check -i 'localhost,' src/configure_agents_connector.yml
ansible-playbook -i 'localhost,' src/configure_agents_connector.yml
```

Use the same certified collection and protected SSH configuration as the container
foundation. The account and guest details stay encrypted in Vault. The stock broker
and instance-specific IPC gateway run as enabled user services. Five continuously
running rootless containers contain tmux sessions for the visible orchestrator,
builder, investigator, challenger and summarizer profiles. Initially those tmux
panes contain idle shells, not authenticated model sessions. Provider login and
native hook approval remain operator actions.

As the dedicated runtime account, use its home-local utility:

```bash
python3 "$HOME/agents-connector/routing/connector-team.py" check
python3 "$HOME/agents-connector/routing/connector-team.py" login builder
python3 "$HOME/agents-connector/routing/connector-team.py" launch builder
python3 "$HOME/agents-connector/routing/connector-team.py" attach builder
```

Select another visible profile name for its own login, launch and attachment.
Claude uses native authentication, Codex uses device login, and Gemini opens its
native authentication flow. No credentials are inherited. Codex hooks require the
operator's explicit native `/hooks` approval; this setup does not bypass it.
Launcher arguments retain native permission prompts. The builder starts in the
native read-only sandbox; broader write permissions require an intentional later
configuration change. Native workspace instruction files load the rough prompts.
Do not launch a role twice while its session is active; attach instead. An exited
session can be launched again. Containers stay available after a CLI exits.

Only each instance's own home, workspace and filtered IPC directory are writable
mounts; the connector binary is read-only. There are no host engine/tmux sockets,
shared provider credentials, sudo, published ports, or host-loopback access inside
workers. CPU, memory, process, capability and read-only root restrictions remain.
The stock administrative socket and SQLite database are not mounted into workers.
The gateway restricts authentication and message identity to the assigned instance
and rejects administrative operations. Visible workers communicate within one
collaboration broker; this is not a general multitenant service.

Stock urgent messages/questions trigger the broker's busy-aware, debounced tmux
wake. The host adapter routes only fixed wake notices and Enter into the named
container's tmux session. Actual message content arrives through authenticated MCP
and native hook context. There is no timed inbox polling. No wake is sent to a
profile before the operator launches its native session. Stock state/cooldown
handling is retained; this does not implement a guaranteed delivery scheduler.

Observer/evaluator, Private Connector and Corporate Connector prompts are prepared
in separate inactive profiles. They are not registered in the worker broker or
mounted into worker containers. Observer transcript access/private reporting,
connector scoped tools/credentials, actual tool audit adapters, automated routing,
discussion budgets and stop enforcement remain pending. Prompt text alone does not
implement those controls. No external connector actions are performed.

The role includes offline validation of native version/help, real inside-container
tmux, enforced isolation, gateway policy, SQLite messages, all three stock hook
formats, and a fixed-only wake into a harmless test pane. These checks use no
provider login or model inference. For a repeatable operator check before launching
model sessions, run the home-local `routing/validate_connector.py`; it refuses the
wake fixture if that native session is already launched.

Setup is installed and offline verified: all three enabled user services are
active, five tmux containers are running, and native versions match the foundation.
All nineteen local tests pass. Live tests passed for all three stock hook formats,
SQLite persistence, IPC identity/admin restrictions, actual fixed-only urgent
message/question wake, and busy-state wake suppression after cooldown expiry.
Fixture messages are removed after successful validation. Routing-service refresh
does not stop the independent containers. Guest free space remained about 2.4 GiB.
Provider authentication and live native model sessions remain unconfigured.
