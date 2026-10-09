# assistant-team

Current communication development continues with agents-connector and tmux.
The [communication architecture review in TODO](TODO.md) compares this route,
acpx with a replacement coordinator, and their combination; no migration is agreed.

Model-authentication vault work is on hold. See the
[replication plan and pushed-code references](docs/AUTH_REPLICATION.md); no secret
bundle or save/restore automation has been created.

Source-only layout change: these new-prefix instructions describe future fresh installs. The running environment keeps its current home-level commands and paths; do not deploy this layout to it yet. See [migration prerequisites](INSTALLATION_MIGRATION.md).

Permission management is a scoped design proposal, not implemented automation:
[generated policies and private approval notifications](docs/PERMISSION_MANAGEMENT.md).
Current roles retain native approvals; a running process alone does not prove readiness.

For another working session, start with [the reusable session rules](SESSION_RULES.md)
and `AGENTS.md`. The rules collect our collaboration, security, deployment, design,
and versioning decisions without including environment credentials.

Deployment and configuration use Ansible where it provides clear, reliable
behavior, preferring a suitable certified collection without adding unnecessary
architecture. Runtime command and messaging logic remains application code.

Version 0.7.0 applies practical Ansible good practices: documented and typed role
interfaces, role-owned variable names, explicit privilege changes, a reboot handler,
and idempotent role instructions. The complete AAP recovery installation succeeded;
the refactoring also passed the same configuration-only job (1380).
Production-profile Ansible lint and 71 local tests pass. See the
[good-practices review](ANSIBLE_GOOD_PRACTICES.md) for applied changes and gaps. Role READMEs describe
check-mode limits; this is not a claim of universal check-mode support.

The published 0.0.1 tag remains the earlier baseline. Google Cloud SDK 588.0.0
is installed in isolated work profiles. Personal Gemini uses the supported
Antigravity native CLI; installation is not model-access proof. Its native team adapter uses the same scoped broker and tmux wake path.

Private project for an assistant team. Application requirements are still being defined.

## Gemini MCP JSON-text compatibility

Gemini CLI 0.63 promotes JSON in a tool's first text block into `structuredContent`
without checking whether it is an object. The stock connector correctly returns
text-only JSON arrays for inbox/peer queries; Gemini then rejects its own promoted
array as an invalid record. A Gemini-only stdio adapter adds an object envelope for
successful JSON array/scalar text results, preserving the original text, request IDs,
errors and broker semantics. Claude and Codex continue using the unmodified stock
shim directly. Native harnesses and the stock broker executable are unchanged.

Ansible installs the adapter into the existing read-only connector binary mount and
generates Gemini's MCP command at initialization. Its focused Ansible tag includes
all path/account prerequisites and only copies the adapter/routing files. Existing MCP processes need an
explicit controlled reconnect or project restart to pick up configuration; this
source fix does not restart an active team or alter trust/tool approval settings.
No model-based acceptance is implied by the model-free transport tests. For an
existing project, the opt-in `agents_connector_repair_gemini_project` and
`agents_connector_repair_gemini_role` variables select a guarded configuration
repair: only the stock MCP command is wrapped, an owner-only backup is retained,
and all model/auth/hooks/other-server settings are preserved. Unknown commands,
unsafe links and non-Gemini roles are refused; native processes stay running.

## Security

Model authentication data must never enter Git, even encrypted. Keep provider
login tokens, refresh tokens, API keys and native credential files in operator-owned
runtime storage or a separate secret manager outside the repository. Ansible Vault
remains available for deployment configuration, not for these model credentials.

Repository privacy does not replace encryption. Store all environment-specific
data, including usernames, hostnames, addresses, credentials, and tokens, in
Ansible Vault-encrypted files. Plaintext documentation and examples must use
generic placeholders. Never commit the Vault password file or decrypted output.

## Vault setup

Ansible and Git must already be available. Run commands from this repository.
Supply an external password file explicitly using `--vault-password-file` or
`ANSIBLE_VAULT_PASSWORD_FILE`; the checkout does not assume a workspace layout.
The password file stays outside this repository; do not copy it here.
AAP supplies its own attached Vault credential without a checkout password path.
Ansible uses a project-specific temporary directory under `/tmp` for local work.

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=/private/vpf
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
Defaults are 2 vCPUs, 4096 MiB RAM, and a 20 GiB disk. The VM name defaults to
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

The main conversation focuses on building and design. Background
subagents handle settled decisions in parallel when their tasks do not overlap or
endanger one another: configuration changes, Ansible
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

`PROJECT` always means the project name. Each project has one team; its roles are
participants in that team, not separate projects. `ROLE` selects a participant
(such as `orchestrator` or `builder`); `ARCHIVE` selects a retained archive directory.

The selected Agents Connector setup below implements continuously running rootless
Podman containers with inside-container tmux for the five visible Claude/Codex/Gemini
profiles. Native authenticated sessions require operator login and launch. The
original foundation launcher remains available for short-lived isolated commands;
Vibe is not included in the selected connector setup.
Container launch waits up to 15 seconds for the idle tmux session before starting
a native harness. A stopped container or readiness timeout fails clearly without
a model request; existing idle sessions can be restored safely.
The connector image also includes process inspection (`procps`) required by Codex
app-server startup. A focused certified image rebuild and guarded failed-builder
repair can replace a dead Codex container without stopping other project agents.
Successful repair restores event wake-up bookkeeping; a marker-only recovery mode
can restore it for a verified live Codex session without restarting that session;
see the [connector role interface](src/roles/agents_connector/README.md).

Existing communication software is preferred over a new message service. Timed
inbox polling is rejected. The selected integration uses stock event-driven wake
and fixed tmux notices, with content delivered through authenticated MCP/hooks.
Generic native inbound transport across all harnesses remains unverified.

## Current assistant team setup

`src/configure_agents_connector.yml` calls separate host, connector, native
installation, account migration, Vertex authentication and project framework
roles. Run the container foundation first,
then this playbook; it reuses the existing pinned native images. Guest/account
details stay in Vault. The complete operator guide is installed as `~/ac-agents/README.md`
in the dedicated account's home, from
[its template](src/roles/agents_connector/templates/README.md.j2). A condensed
`~/ac-agents/README.TLDR.md` provides the minimum operator commands. Keep both guides
current when behavior changes.

```bash
ansible-playbook --syntax-check -i 'localhost,' src/configure_agents_connector.yml
ansible-playbook -i 'localhost,' src/configure_agents_connector.yml
```

Use the same certified collection and protected SSH configuration as the foundation.
`--tags native_auth,auth_sources` updates native login installations, prompt sources
and home-local controls without restarting the service group.

### Native installations and account login

The dedicated home contains eight isolated account profiles: `claude-work`,
`claude-priv`, `gemini-work`, `gemini-priv`, `codex-work`, `codex-priv`,
`mistral-work` and `mistral-priv`. Each provides `./login` and its
native `./claude`, `./gemini`, `./codex` or `./vibe`. Program artifacts are reused
from the pinned images; duplicated Claude code and Node runtime use hard links.
Vibe uses checksum-pinned Astral Python Build Standalone 3.12.15 to support the
guest's libc. No global CLI, npm, pip, gcloud or libc shim is installed.

```bash
cd ~/ac-agents/model-environments/claude-priv && ./login
cd ~/ac-agents/model-environments/gemini-priv && ./login
cd ~/ac-agents/model-environments/codex-priv && ./login
cd ~/ac-agents/model-environments/mistral-priv && ./login
```

Private Claude uses native OAuth login. Private Gemini selects personal Google
sign-in and removes competing API-key and Vertex environment settings from its
process. Work Claude and work Gemini use Vertex, with guided project, region and
model configuration and profile-local Application Default Credentials. Their
Cloud SDK installation is separately gated; those login flows cannot run until
the required SDK is installed. Codex uses device login and a file credential
store. Mistral opens Vibe's native setup wizard. Work and private labels for
Codex and Mistral select separate accounts; they do not imply Vertex support.
All eight wrappers
scope HOME, provider configuration, credentials, caches, state and temporary files
to their respective directory. Provider authentication is performed by the operator,
never inherited from this development session. Installation does not log in,
accept provider terms or request model output. Choose the intended account;
there is
no automatic paid API fallback. Each login reports failure/cancellation or saved
credentials with model access unverified. Local credentials and a successful
login command do not prove model entitlement; verified access requires a separate
explicit model check. Such checks are not run automatically.

`./login --clear` removes that profile's saved authentication and matching
project-role copies, preserving program files, provider configuration and other
profiles. It refuses to clear an active native session or a running project
using that profile; stop those sessions first. Clearing local files does not
promise provider-wide remote revocation.

On explicit role launch, only missing credential files are seeded into that role's
isolated home. Claude copies only optional OAuth account metadata, not global MCP
or other settings. Existing role credentials retain their own native refresh state.
Work/private account sources are separate. Native hooks, prompts, workspaces and
sessions remain per role. Actual provider login/refresh behavior awaits operator
authentication; initial seeding does not promise automatic cross-role refresh sync.

Official references: [Gemini authentication](https://geminicli.com/docs/get-started/authentication/),
[Codex authentication](https://learn.chatgpt.com/docs/auth),
[Vibe setup](https://docs.mistral.ai/vibe/code/cli/install-setup), and
[portable Python](https://github.com/astral-sh/python-build-standalone/blob/main/docs/running.rst).

### Project-only roles and lifecycle

The redundant original non-project target, three services and eight container
objects are retired. Saved profile homes, authentication state, prompt defaults
and the original SQLite database remain; no actual project state is removed.
Ansible reruns do not recreate or start the original group. Commands without a
project name return a helpful error rather than starting shared default containers.

All eight role containers and native sessions belong to the selected project.
Only five collaboration roles join its worker broker; the observer and private/
corporate connectors remain separately scoped. Observer snapshots/private report
delivery remain manual, and external connector tools remain unconfigured.
The runtime home README starts with a short create/edit/start/attach workflow.
There is no all-projects master target.

### Project framework

New prompt templates use `[Project]` and `[Role: Investigator]` (likewise all eight
roles, including `[Role: Private Connector]`). Lines beginning with `#`, including
example instructions, are comments and are removed before delivery to harnesses.
Write active instructions below them or remove the `# Example:` prefix. Blank role
sections are allowed; examples are never silently activated. Existing `# Role:`
project files remain supported and are not overwritten. The new template/parser
is committed for future deployment; its deployment to the original VM is currently
held at the operator's request.

The separate `project_framework` Ansible role installs project-scoped control and
systemd instance units without restarting existing sessions. As the runtime user:

```bash
~/ac-agents/bin/team setup
~/ac-agents/bin/team setup --list
~/ac-agents/bin/team --help                    # all commands and required parameters
~/ac-agents/bin/team --list                    # project names + runtime status, without auth or DB reads
~/ac-agents/bin/team create-project my-project
${EDITOR:-vi} ~/ac-agents/projects/my-project/project.my-project.config
${EDITOR:-vi} ~/ac-agents/projects/my-project/assistant-prompt.md
# Fill [Project] and [Role: Name] with active instructions; # lines are inactive examples.
~/ac-agents/bin/team start my-project
~/ac-agents/bin/team status my-project
~/ac-agents/bin/team attach my-project orchestrator
~/ac-agents/bin/team watch my-project
~/ac-agents/bin/team stop my-project
~/ac-agents/bin/team restart my-project
```

Current command parameters (invoke `team` through the installation's `bin/team`):

| Command | Meaning |
| --- | --- |
| `create-project PROJECT` | Create one project, its team configuration and database. |
| `--list` / `list-projects` | List projects; no project parameter. |
| `start PROJECT` / `stop PROJECT` / `restart PROJECT` | Control that project's whole team. |
| `status PROJECT` / `watch PROJECT` | Inspect runtime state or follow its messages. |
| `attach PROJECT ROLE` | Attach one role's native session; detach with Ctrl-B D. |
| `archive PROJECT` / `destroy PROJECT` | Retain the stopped project as an archive or delete it. |
| `unarchive ARCHIVE` | Copy a retained archive into its dated project name, leaving it stopped. |
| `rename-project PROJECT NEW_PROJECT` | Rename a project and its identity; leave it stopped. |
| `apply-prompts PROJECT` | Render role instructions for the next native launch. |
| `preflight PROJECT` | Check assignments and saved-auth prerequisites. |
| `launch PROJECT ROLE` / `launch-all PROJECT` | Launch one or all native role sessions after checks. |
| `stop-containers PROJECT` | Stop only that project's role containers. |
| `refresh-observer PROJECT` / `deliver-observer-report PROJECT` | Update its private snapshot or deliver its report. |

Use `--help` for every command, including environment setup and diagnostics.
The shorter verb-only command scheme is a proposal in TODO, not current behavior.

There is one environment per Linux user. `~/ac-agents/conf/environment.conf` records which
of the eight profiles are enabled; setup selects those profiles before offering
native logins. Listing distinguishes enabled, installed and locally saved
credentials, without making model requests. Disabling a profile preserves its
credentials and existing projects, but prevents new starts that require it.

Project listing status describes the target and named components: `running`,
`starting`, `stopping`, `stopped`, `failed`, `partial` or `unknown`. `partial` means
components are active while the target is inactive; `unknown` means a systemd or
Podman query failed and includes a bus/access suggestion. `running` describes the
target, not individual pane health or verified model access. Listing starts no
service and reads no project database, prompt or authentication contents.

Project completion commands are `~/ac-agents/bin/team archive PROJECT` and `~/ac-agents/bin/team destroy PROJECT`.
Both first check the named target, broker, gateway and containers, stop them only
if running, and verify that no project writer remains. Stopped containers are
removed without deleting images or shared model account profiles. A failed stop
leaves project data and configuration in place; an inactive project needs no
native harness or login to complete either operation.

Archive moves the whole project—including SQLite history/WAL/SHM, artifacts,
prompts and role state—to `~/ac-agents/project-archive/PROJECT-ddmmyyhhmm`, with its project-local
`project.PROJECT.config` inside. Every archive uses the operation-start local time
(day, month, two-digit year, 24-hour hour/minute), saved in private timestamp metadata.
Same-minute destination collisions fail before stopping; no archive is overwritten.
An archive matching the current project name exactly also blocks shutdown: use
`~/ac-agents/bin/team rename-project OLD NEW` before retrying (provided by the rename feature). Archive directories are private (0700), the assignment config is 0600,
and internal file modes and symlinks are preserved. Archives can include private
role-local authentication copies and must stay outside Git. Restore is not provided.
Destroy permanently deletes the project directory and its home-level config.
Enabled named service instances are disabled. Only their failed state is reset;
bounded nonloading unit-list checks verify that systemd forgets all four instances
before files are moved/deleted. If a reference prevents collection, files remain.
Shared systemd templates and other instances remain.
Do not start, restart or edit the same project concurrently with either operation.

`~/ac-agents/projects/PROJECT/project.PROJECT.config` is the sole authority for role-to-profile assignments.
Both configuration files use JSON and contain no authentication secrets. Project
assignments must select enabled profiles. Connector roles whose required account
is unavailable need an explicit assignment before startup; they do not silently
switch private and corporate contexts. The observer and two restricted connector
roles currently require Claude. The collaboration roles retain their current native adapter and can select its
enabled work/private profile; changing the role’s vendor adapter is not implemented. Mistral profiles support standalone login and
CLI use; assigning them to team roles is refused until its adapter is implemented.

Creation uses the stock broker to initialize `~/ac-agents/projects/PROJECT/db.sqlite` and its
five-worker registry. Eight profiles have separate native homes, workspaces, IPC
and container names. Native role state is separated by assigned account profile,
so changing accounts does not reuse another profile's credentials. Stop an active
project before changing its assignments, then start it again. The editable
singular `assistant-prompt.md` contains the
project goal and all role prompts; only the goal and the selected role section
are rendered into each container. Existing project state is not overwritten.
Names accept 1–40 lowercase letters/digits, underscores and hyphens, beginning
with a letter/digit; traversal and symlink project paths are rejected.

Start checks saved subscription/OAuth credential format for all required role
account boundaries before starting services, then launches all eight native CLIs
without an initial work prompt. Login directories remain outside projects; only
missing provider credential files are seeded into each role home. Existing role
refresh state is preserved. This preflight cannot establish remote token validity.
Native onboarding, workspace trust and Codex hook approval are not bypassed.
Native Mistral team support is tracked as required future work, including an
upstream agents-connector pull request.

The user target `assistant-connector@PROJECT.target` orders that project's broker,
gateway and native container services. Project targets are not enabled at boot.
Stop/restart affect only that project and preserve its database and role state;
restart launches new CLI sessions, without claiming automatic conversation resume.
Only five collaboration roles join its broker; the observer and connector roles
remain separately scoped. Observer snapshots/private report delivery remain manual,
and external connector tools and automated orchestration remain unconfigured.
Every user-facing lifecycle/viewer/attach command requires a project name.

The home README documents these commands and project-specific prompt/review
operations. Update this layer with `--tags project_framework`. Explicit offline
project validation uses disposable projects and dummy tmux harnesses only; no
provider credentials are fabricated or native models invoked.

### Vertex login prerequisites

Both work Claude and work Gemini use Google Vertex AI. Their profile-local login
helpers configure the project, region and explicit model, then run the Google
Cloud ADC login flow. They preserve that provider configuration when credentials
are cleared. Work role containers receive only their selected profile's ADC and
provider settings. Personal profiles do not inherit Vertex authentication.

The separately gated `vertex_auth` role installs the Cloud SDK only when explicitly
authorized. SDK installation remains pending in the current development setup;
no Vertex login, cloud API enablement or model request is performed automatically.
Cloud billing, model access and quota must already be available to the operator.
Disabled work profiles do not block projects assigned entirely to other enabled,
authenticated profiles. Work projects require the chosen backend to be ready.

### Shared project artifact workspace

Every project has `~/ac-agents/projects/PROJECT/workspace`, mounted at `/workspace/shared`.
All seven working roles can read/write shared artifacts; the observer can only
read them. Their native homes, credentials and role instruction files remain
separate. The full prompt file and private connector contexts are not shared.
Only explicitly authorized project results may be published from connector roles.
Their general native tools remain disabled pending scoped external tools.

Codex uses native workspace-write with on-request approval for project work.
Prompts ask agents to coordinate file/task ownership through the orchestrator and
avoid concurrent edits; no custom locking system is introduced. The separate
project_workspace Ansible role adds missing directories without modifying their
contents. Active containers are preserved and acquire new mounts on a normal
project stop/start. Stopped definitions are rebuilt only when mounts differ,
preserving all bind-mounted data. No images, dependencies or VM resources change.

### Validation and current limits

All eight local installations pass host-native version/help checks. Native
project sessions require operator authentication; installation does not launch
models. Tests cover scoped configuration and login paths, work/private credential
seeding, retained refresh state, hidden prompt extraction and project lifecycle.
Live checks use disposable projects and dummy sessions to validate communication,
read-only observer access and persistent state without provider model requests.
These checks do not establish all providers' account validity or entitlement.

The VM remains at its approved allocation. Idle containers use little memory;
concurrent native/model/build workloads remain unmeasured. Review free storage
before further image builds or substantial workspace growth. No memory or
filesystem expansion was performed.

### Deployment access and diagnostics

The operating workflow separates development from access to authenticated
environments: develop and review repository changes here, then have the operator
deploy to their own destination and perform provider logins there. Deployment
must not require model credentials or give this development agent destination
access. Existing development access is retained; it is not a security boundary
for the current VM.

The portable user-operated deployment path supports the same roles for local and
remote Ansible connections. That path and unified target-side
`~/ac-agents/environment-logs` are being implemented. Diagnostics will cover deployment,
setup, authentication outcomes and service/container lifecycle using protected
operational metadata. They must exclude credentials, conversations, prompts and
raw model output. Failures before a target connection exists require a protected
local fallback, transferred to the target when reachable. Sharing a sanitized
diagnostic export does not grant destination access.

### Release policy and future work

The first release will be `0.0.1` after outstanding implementation, validation,
documentation and reproducibility checks are complete. After that release,
feature commits increment the minor version and reset patch; all other commits,
including documentation commits, increment patch. Installed version and commit
metadata belong in diagnostics. Release automation is still being prepared.

[Future work](TODO.md) distinguishes required later work—custom roles based on
the default templates and Mistral team support—from optional custom account
contexts and multiple environments. Multiple environments are not supported now;
use separate Linux users for isolated environments.

Personal Gemini uses the official pinned Antigravity CLI in `~/ac-agents/model-environments/gemini-priv`:
run `./login`, complete its personal Google browser/code authorization yourself,
then exit the CLI to see the saved-auth result. The detector recognizes the native
nested OAuth token file. An interrupted TUI reports saved/unverified only when new
valid credential evidence was written; unchanged existing credentials are explained
without demanding another login. Neither condition proves remote model access.
`./agy` launches the native CLI;
`./login --clear` removes this profile's local authentication. The work profile
continues to use Gemini CLI through Vertex. No old account data is migrated.

Antigravity chooses native file token storage in SSH/container environments;
GNOME packages are not required. Directories are 0700 and launcher umask is 077.
These are local file permissions, not encryption at rest, and do not protect
against root, sudo or other processes running as the runtime user. Deployment
never signs in or reads/copies existing credentials. Saved authentication does
not prove model access. No client-ID bypass or automatic paid API fallback is
configured. Assign `gemini-priv` to the challenger in `projects.PROJECT.config` to use
Antigravity 1.3.1. Its existing pinned executable is mounted read-only inside the
Gemini connector image; the native MCP server lives in `.gemini/config/mcp_config.json`.
A small lifecycle adapter translates native `PreInvocation` and `Stop` events into
scoped broker state and addressed context. Partial stops remain busy. Role launch
seeds only a missing private native token; existing role refresh state wins. Work
ADC, Vertex settings and provider API keys are not used by this launch. Native
approval remains enabled, and no credits/paid fallback setting is imported.

Login wrapper status, outcome and error messages use the `[AC-Agents]:` prefix; native vendor output keeps its original format.

Login results include provider-specific next steps. Failed personal Gemini access directs the supported Antigravity migration; failed Vertex setup identifies scoped SDK/configuration prerequisites. Saved credentials remain explicitly unverified for model access.

## Deploy independently

Follow [DEPLOYMENT.md](DEPLOYMENT.md) to initialize your own encrypted destination settings and run the complete role chain on this same host or a remote host. Destination access stays with the operator; no coding-agent access or model login is needed. Controller connection-failure metadata can be replayed to the target later. The normal AAP fresh installation completed after a configuration-only recovery; the separate portable local/SSH runner has not been exercised against another fresh target.

Use `python3 src/bump-version.py --help` for the version maintenance helper. Formal releases require pushing the annotated version tag and publishing the matching GitHub release; branch version increments alone are not published releases.

Vibe browser sign-in uses a scoped manual browser handoff on headless hosts so the native authorization polling continues. Open the native displayed URL manually; the wrapper neither handles codes nor bypasses provider authorization. Existing failed sessions must be exited before retrying.

## Fresh cloned VM storage

New Linux VM provisioning defaults to a 20 GiB cloned disk, with the desired size recorded in encrypted deployment settings. After guest setup, `linux_root_growth` expands the direct last GPT root partition and XFS filesystem to use the clone's available capacity. It saves a protected partition-table backup before growth and validates the partition start, type and identity. Reruns are idempotent; unsupported filesystem/mapping layouts fail before mutation.

The current running VM had already been expanded to a 50 GiB virtual disk and roughly 49 GiB root filesystem, with about 41 GiB free at verification. It is preserved without shrinking or another reboot. The default for future clones is 20 GiB. No separate additional-disk resize command is provided. Protected backup files remain on the existing guest; future automation backups are private under `/var/lib/assistant-team/storage-backups`. A partition-table backup is not a data backup, and XFS growth cannot be reversed by shrinking.

The root-growth role passed an unchanged rerun on the expanded guest and ran during the fresh 20 GiB AAP deployment.

## Work Vertex login

The approved local Google Cloud CLI 588.0.0 is installed in both work profiles with separate Cloud SDK configuration/ADC paths and shared immutable program files. Run `cd ~/ac-agents/model-environments/claude-work; ./login` or `cd ~/ac-agents/model-environments/gemini-work; ./login` to enter your own project, region and enabled model ID, then complete native ADC authentication. No login, API enablement, billing change or model call ran during installation. Gemini's native selected/enforced auth type becomes Vertex after completed ADC login, preserving unrelated hooks/settings.

The immutable versioned SDK archive is checksum-pinned. Its payload was verified identical to Google's rolling archive that matches the published checksum, avoiding use of one archive's checksum for a differently packaged tarball. SDK verification checks the installed release exactly and removes the owned staging download. Independent deployments install this selected dependency only when their encrypted operator configuration enables it.

## AAP-only fresh deployment validation

`src/deploy_complete_linux_vm.yml` provisions an isolated VM from its own Vault-encrypted definition, fully updates it, grows the cloned root filesystem and installs the entire environment through normal AAP jobs. The committed test definition is separate from the existing deployment. Use a dedicated job template with the hypervisor inventory, machine and Vault credentials, and the pinned certified collection available in its execution environment. Do not retain obsolete disk-size overrides.

After provisioning succeeds, recovery must skip the `provision` tag: record the discovered guest address in the encrypted `recovery.guest_ip` field and rerun with `guest_config`. This protects the existing disk and domain. Installation validation uses disposable dummy harnesses; it neither copies provider credentials nor invokes models. The fresh AAP deployment originally completed through configuration recovery job 1376. A later clean end-to-end run, job 1394, completed in one pass at version 0.9.1 with no recovery or retry; no provider credentials or model calls were used. See [DEPLOYMENT_TEST_RESULTS.md](DEPLOYMENT_TEST_RESULTS.md) for the tested snapshot, safety checks and limits. AAP project revision metadata is recorded when available.

Vertex Claude model selection expects a complete enabled Vertex model ID, such as `claude-opus-5`, rather than `Opus` or `Opus-5`. The example is not an access check: availability depends on the operator-selected Google project and location. Invalid input now explains the format before retrying.

Configuration-only AAP recovery retains separate encrypted SSH and sudo credentials; it does not assume that their passwords match.

Fresh native installations install the launcher dependency before checking CLI versions. Recovery rechecks every context, including contexts with installation metadata from an interrupted run, without authenticating or invoking models.

Deployment input tests execute the VM role with isolated fixture data; they do not require the development Vault or its password file.

## Repeatable quality checks

Use the already-installed Python 3.12, Ansible and ansible-lint with the pinned
certified collection available and an external Vault password file:

```sh
export ANSIBLE_VAULT_PASSWORD_FILE=/private/vpf
python3.12 src/check-quality.py
```

The command runs tests and production-profile offline lint, preserves failure
exit codes, and installs nothing. `--tests-only` omits lint; VM input tests still
require an installed Ansible executable. The local pre-commit configuration uses
this same command if the operator already has pre-commit; pre-commit was not
installed automatically. A manually dispatched GitHub workflow targets a trusted
self-hosted runner labelled `assistant-team-quality`, provisioned with the same
tools, certified collections and external Vault access. No runner is registered
or cloud secret configured by this change; CI execution remains pending operator
runner setup. Its checkout action is pinned and does not retain a Git credential.

### Optional local APME evaluation

[APME evaluation](docs/APME_EVALUATION.md) records the completed full-codebase
Native/OPA/Ansible scan and optional dependency-check coverage. Certified content
was provisioned from its verified original artifact. Findings require contextual
review; unavailable or unauditable checks are not passing results. Read-only scans
are authorized, and relevant fixes may follow assessment. Production lint remains
the established gate; no automatic source remediation or AI request was made.
The subsequent [Ansible readability review](ANSIBLE_GOOD_PRACTICES.md) preserves
command behavior while clarifying shell parameters and internal result names.

## Disposable deployment test lifecycle

`src/retire_test_linux_vm.yml` performs a read-only preflight by default using its separate encrypted retirement definition. Its dedicated normal AAP template removes the selected second test clone only when explicitly launched with `retire_test_execute: true`. The role verifies exclusive disk ownership, refuses source-image or shared disks, uses graceful shutdown, and checks preservation of all other domains and the golden image. The fresh deployment definition selects the next test clone with an empty recovery address; configuration-only recovery remains available after successful provisioning. No provider credentials are copied or model inference performed by this test.

Existing legacy project prompts can be converted explicitly with the project-framework
role variable `project_framework_migrate_prompt_projects`, a list of project names.
Migration retains active goal and role instructions, converts meaningful Markdown
heading text to active plain text, and comments out the known rough-template guidance.
It writes a protected backup beside the project prompt before atomic replacement.
The default empty list leaves every existing project unchanged; no sessions restart.

Human-readable runtime diagnostics are in `~/ac-agents/environment-logs/events.log`, alongside
`events.jsonl`. Follow them with `tail -f ~/ac-agents/environment-logs/events.log`. Both use
matching event IDs, protected permissions, and a 1 MiB rotation with three backups.
Failure guidance is fixed safe text, not raw native output; use the user journal
for detailed service diagnostics. Deployment transfers also provide protected
`deployment-<run-id>.log` alongside JSON, retaining up to 32 runs. Diagnostic exports
remain validated JSON-only; arbitrary text files are never exported.

The editable default template for new projects is `~/ac-agents/conf/templates/assistant.prompt.md.template`.
Creation copies its role instructions into the new project; existing project prompts
remain independent. Deployment preserves operator edits and migrates the old home-level
template without overwriting an existing destination. Conflicting paths require operator review.

### Restore a retained archive

Run `~/ac-agents/bin/team unarchive example-0910260800` using the archive directory name.
This copies its complete project state to the same dated project name and keeps
the original archive unchanged. The exact target is enabled but left stopped;
start it explicitly when ready. Structured configuration and generated role
instructions use the new identity; user prompts, artifacts, provider state and
conversation history are preserved. Broker sessions use the new instance name at
startup; stored agent identities and container-internal MCP paths remain valid.
Legacy plain archives gain their recorded archive timestamp, or directory mtime
when no metadata exists. Existing destinations, unsafe links, malformed archives,
and existing instances/containers refuse restoration before publication. Failed
restores roll back new files and enablement. Long dated names are checked against
the actual Unix socket path limit; use a shorter project base before archiving if
needed. No model calls or automatic service startup occur during restoration.

Before archiving a restored dated project again, use `rename-project` to choose a new logical name: the retained archive already has its exact current name.

`~/ac-agents/bin/team rename-project OLD NEW` stops OLD when necessary, removes only its stopped
containers and forgets its old named systemd instances, then renames the project
directory and home assignment config. It updates structured project identity and
generated role instructions, preserving editable prompts, workspace artifacts,
conversation history and native authentication. The new target preserves OLD's
enablement and remains stopped; start it explicitly with `~/ac-agents/bin/team start NEW`.
Existing new paths/configs, containers, loaded instances or excessive Unix socket
path lengths refuse the operation before shutdown. Partial rename failures roll
back directories, config and generated instructions where possible; an incomplete
rollback reports retained paths rather than overwriting them. Do not run lifecycle
commands or edit the same project's config concurrently.

Project rename also rolls back unexpected rendering failures and terminal interruption; the restored old project remains stopped.


Unarchive preserves existing relative links only when their targets stay inside
the retained project. It rejects other external, dangling or cyclic links. In
Codex native homes only, the regenerated `.codex/tmp/arg0` and
`.codex/app-server-control` scopes are omitted from the restored copy; the
archive remains unchanged. An exact daemon `current` pointer under `/home/agent`
is rewritten to a relative link only when it maps to the same native home's
retained release-cache directory. The staging tree is checked before publication
or target enablement. Credentials and other native state are preserved.

The exact Codex `.codex/app-server-daemon/daemon-updater.sock` is also omitted
from the restored copy when it is a socket; an ordinary file at that path is kept.

Gateway listeners on SELinux hosts use an explicitly permitted container socket
context at socket creation. The host process keeps its own context, the previous
thread default is restored before asynchronous work, and private per-role mount
labels and token checks remain in force. This resolves Unix `connectto` denials
that inode relabeling alone cannot fix. A gateway restart may stop dependent
containers; coordinate activation with the operator rather than restarting a
live team merely to apply the change.

`team stop NAME` blocks until the named target, broker, gateway, container service,
containers and IPC listeners have stopped. It preserves enablement and project
data. A pending shutdown is completed before `team start NAME` submits a start;
`team restart NAME` performs a complete stop followed by start. Commands have a
bounded wait and fail clearly if shutdown cannot be verified. This avoids a fast
stop/start canceling remaining shutdown jobs. `team status NAME` includes dependent
service state in its project summary.

Codex CLI updates are centrally managed through pinned Ansible installations and
image rebuilds. Generated role configs and managed launch commands disable the
startup update check using `check_for_update_on_startup=false`; this avoids an
interactive npm update attempt inside a read-only container. Existing operator
TOML is preserved, and the command override applies without rewriting it. Native
host wrappers use the same policy to preserve their managed installation version.
See the [official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

Authentication troubleshooting: saved credentials or a successful `codex login
status` do not prove the provider accepts a session's actual requests. A sign-in
screen or HTTP 401 needs operator authentication/access investigation; re-login
may be necessary, and controls must not be bypassed. Native first-run onboarding
(such as theme or workspace trust) is separate from provider login and from tool
approvals. Inspect the affected tmux pane locally without exposing credentials.

Codex role containers launch with `--no-daemon`: each container owns the session
lifecycle and does not need a shared background server. This supported CLI mode
was verified during native startup troubleshooting. It does not replace login,
hook trust, sandbox or approval checks. Host native wrappers retain their normal
daemon behavior.

For Gemini work on Vertex, enter the exact provider model ID. The current
Gemini 3.1 Pro identifier is `gemini-3.1-pro-preview`, including the suffix;
`gemini-3.1-pro` is not the published identifier. Confirm model availability for
your project/location in the [official Google model reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-1-pro).
The login prompt checks identifier format, not remote model access. Keep the
selected ID in the local work profile's `.vertex.json`; work role launches copy
that configuration into the selected role home. Provider authentication files
remain outside Git.

Before handing over the first project task, attach each role with
`~/ac-agents/bin/team attach NAME ROLE` and finish its native first-run screens. Review theme,
workspace trust, hook trust or requested tool permissions in that role's CLI.
These steps are separate from provider authentication; saved credentials and
login status do not prove actual provider requests succeed. Once the roles reach
their normal prompts, attach the orchestrator to give the project task. Manual
onboarding does not change the team's tool-approval policy.

The Gemini MCP result adapter uses the shared `container_file_t:s0` file label
so focused updates work in existing read-only container mounts. Gemini reloads
MCP clients from its cached startup configuration: after changing the MCP command,
resume its saved native session before checking the new connection.

Installed acceptance confirmed the native Gemini session can read its inbox, list
participants and reply to its original readiness ask through the adapter. This
followed a controlled saved-session resume and one-time approvals for those exact
broker tools; it does not establish automatic wake-up or unattended permissions.

A bounded installed check also verified automatic idle ask wake-up: the stock
broker notification started a Gemini turn, its exact reply tool was approved
once, and the waiting orchestrator received the correlated response. Earlier
schema-error messages remain historical conversation entries. This test does
not establish unattended approvals, busy-queue recovery or tell-only wake-up.

The remaining installed communication acceptance cases are tracked in TODO: busy
roles, tell-only wake-up, queued recovery and approval-blocked delivery.

Antigravity team integration follows its official [MCP configuration](https://antigravity.google/docs/mcp?tab=cli)
and [native hook contracts](https://antigravity.google/docs/hooks/). It retains the
current broker and tmux architecture; it does not introduce ACP or change native
approval policy. The separate `antigravity_team` role verifies runtime dependencies
without mounting credentials or enabling network access.

Private Antigravity credential seeding rejects symlinked directories and token
files. Directory-descriptor traversal and exclusive publication prevent a prior
role session from redirecting the copy into a shared workspace or outside its
account boundary. Existing regular role credentials remain authoritative.

The native Antigravity integration is deployed and its isolated dependency probe
passes. A fresh role still requires the operator's terms and data-use choice; this
choice is not inferred from saved login tokens or copied onboarding flags. Native
model access and wake/reply acceptance remain pending until that screen is resolved.

`team status NAME` includes each role’s account profile (for example `gemini-priv`)
and configured model. These are configuration labels, not verified provider model
versions or entitlement. A missing explicit model is shown as `harness default
(unverified)`. Status does not run inference, inspect credentials or send terminal input.

`team watch NAME` colors sender/recipient role labels on interactive terminals;
message text stays plain, and available question correlation IDs remain visible.
Redirected output, `NO_COLOR` and `TERM=dumb` disable color. Restart only the watch
viewer to pick up formatter updates; the project team can keep running.

`team watch NAME` now prints the last 50 communication entries and exits.
`team watch NAME -20` prints the last 20 and exits. `team watch NAME -f` follows
only new entries; `team watch NAME -20 -f` prints the last 20 then follows.
Options may go before or after the project name: `team watch -200 -f NAME`
and compact `team watch -200f NAME` both show 200 entries then follow.
Counts are 0–10000; either flag order works. This changes the earlier bare-watch
live-follow default. History is chronological by message ID, including asks and
replies once each. Follow subscribes before taking its history snapshot and skips
queued events already included in that snapshot. The existing upstream live
stream can drop notifications for an excessively slow viewer; it is not a durable
subscription. History reads only the project’s message table, with no model calls.

For a concise decision feed, run `tail -f ~/ac-agents/projects/NAME/workspace/DECISIONS.log`.
The summarizer appends timestamped DECIDED, DIRECTION or BLOCKED lines only after
meaningful accepted outcomes, agreed direction changes or blockers requiring
user input. The orchestrator requests these updates at milestones, without timers.
The summarizer is the sole intended writer; proposals, repetitive progress,
credentials, private connector content and hidden-role identities stay out.
This is an agent instruction policy, not a filesystem enforcement of append-only
writes: project workspace collaborators retain their existing write permissions.
Existing user prompts and log content are preserved during deployment. Already
running harness conversations need an explicit instruction refresh to adopt it;
updating files alone does not guarantee they re-read their role instructions.

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
The approved install-prefix layout is currently **source only**. The existing deployment remains on its earlier home-level layout; do not apply these playbooks to it yet. Fresh installs use `PARENT/ac-agents`, with PARENT defaulting to the destination runtime HOME. `--prefix /absolute/parent` selects a destination parent for both local and remote deployment; AAP uses `assistant_install_prefix` or its encrypted definition. See [INSTALLATION_MIGRATION.md](INSTALLATION_MIGRATION.md) before any legacy migration.
