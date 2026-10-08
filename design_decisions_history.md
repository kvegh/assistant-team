# Design decisions history

## Initial project setup

Implementation: `83589382dd6311e87564bdcf5529cf511fca7849`.

The user chose a new private repository rather than adding this project to an
existing private repository. Privacy does not replace encryption: all sensitive
and environment-specific configuration must use Ansible Vault with the existing
workspace password file. The password file remains outside Git. An encrypted
configuration file and documented Vault commands establish this convention.

Ansible's local temporary directory is configured under `/tmp` because the
default home-directory location is read-only in the development environment.
Encryption and decryption were verified without displaying decrypted contents.

Application requirements and tooling remain undecided. Existing golden-image
Linux provisioning is the planned basis for the first VM, with a separate AAP
job template to avoid changing another project's deployment settings. The user
specified two vCPUs and 4 GiB RAM. A 40 GiB disk is an initial implementation
assumption, not an explicit user requirement. Provisioning has not run yet.

## Generic Linux VM provisioning

Implementation: `7d81840541c8066d18bfba0b602957612a733bfc`.

The user requested a reusable job template named Generic Linux VM Deployment.
The existing AAP-specific golden-image playbook was adapted into this private
project with configurable names and resource sizes. It uses the existing image
and encrypted environment configuration rather than the older deployment
playbook's hard-coded guest passwords. The source playbook remains unchanged.

The new playbook refuses existing VMs and disks, rejects shrinking the source
image, resets cloned machine identity and host keys, finds DHCP leases by MAC,
and verifies authenticated guest access and requested resources. Failed runs
preserve resources for investigation rather than automatically deleting them.
Filesystem growth is deliberately left for a later guest configuration step;
the current implementation only expands virtual disk capacity.

Environment settings and inherited guest access credentials are Vault encrypted.
Task logging is protected by default. VM results go into controller job artifacts
and should be persisted only in encrypted repository files.

Validation: Ansible syntax checking, four input-validation tests, Vault decryption
without displaying plaintext, and Git whitespace checking passed. The installed
ansible-lint entry point cannot import Ansible because it uses a different Python
version; no dependencies were installed to repair that environment.

AAP currently has no GitHub source-control credential for private repositories.
Creating the controller project and template, and deploying the VM, remain pending
the user's choice of how to grant the controller private repository access.

## Clean generic VM clones

Implementation: `e9bc9235ad303763977082262d69e3dee346d757`.

The user requested removal of the pre-staged AAP installer and unnecessary clutter.
Read-only image inspection through AAP confirmed roughly 3.8 GiB of installer
content, a dedicated AAP service account with lingering enabled, no DNF cache,
and no installed Ansible or Podman packages or system container storage.
The user explicitly allowed AAP ad hoc commands for this inspection only.

Cleanup runs inside the cloned disk before boot. It removes installer artifacts,
the dedicated AAP account and its home, associated lingering and sudo entry,
package caches, shell histories, and logs. It preserves the automation access
account and leaves the shared golden image untouched. Account validation runs
before deletion; protected-account tests confirm that no deletion is attempted
for root, the automation user, or another UID-zero identity.

Ansible syntax checking, Vault decryption, whitespace checking, and all seven
input-validation and cleanup-guard tests passed. Live deployment remains pending.

## Fully update each guest after boot

Implementation: `adb09a88dbb456ca8664edad694ee5d760bdfd5c`.

The user requested a complete DNF update after the VM starts. Guest configuration
uses the existing encrypted RHEL activation key if registration is needed,
enables BaseOS and AppStream, updates all installed packages, and reboots after
package changes. It reconnects and requires a fresh DNF update check to report
no remaining updates before publishing success, including the running kernel.

The guest configuration stage can be rerun with the same VM name and the
guest_config tag. This rediscovers the existing guest without repeating cloning,
disk resizing, or offline cleanup. The controller template must accept job tags
and avoid a host limit that excludes the dynamically added guest.

Syntax checking and all seven tests passed. Registration, updating, rebooting,
and the final update check still require validation on the deployed VM.

The user approved a GitHub token restricted to this repository. GitHub's
fine-grained token creation requires the user's signed-in browser; the existing
workspace credential has broader access and is not reused for the controller.
The private project sync and VM deployment remain pending a Source Control
credential in AAP with read-only access to this repository.

## Private repository sync and deployment access status

Implementation: `f122084131c012bd325c4e9f7ac889f487f095e9`.

The user supplied the repository-scoped GitHub token, which was stored in AAP's
encrypted credential store without adding it to repository files. The private
controller project synchronized successfully. The user confirmed the proposed
VM hostname; that environment-specific value stays in Vault.

Before deployment, the AAP MCP service rejected its configured bearer token as
invalid or expired. The configured token matches the original connection source,
so a stale local copy was ruled out; the exact reason for rejection is unresolved.
Job-template creation remains unconfirmed and no VM deployment has been launched.
The README and encrypted controller references record this state without exposing
secrets. Authentication must be restored before controller work can continue.

## Keep the current GitHub token lifetime

Related configuration commit: `f122084131c012bd325c4e9f7ac889f487f095e9`.

The user decided to leave the repository-scoped GitHub token and its current
expiration unchanged. Renew or replace it on demand when repository access
requires it, and update the corresponding AAP Source Control credential at that
time. No token rotation or expiration change is being made now. This decision
does not resolve the separate AAP MCP authentication failure.


## Restore controller access and recover the first deployment

The user confirmed that hypervisor memory starvation caused the controller
outage. Controller access recovered without changing the configured AAP token.
The earlier token-expiration explanation was an unconfirmed hypothesis, not the
established cause. The requested generic job template was created with the
existing hypervisor and Vault credentials and the private project.

Implementation: `ff78da81427bcd1cab888854bc40e5f7f7e16abd` and
`e117eefcba386ffbbed73f8398ae11e47fe291ed`.

The first deployment preserved its cloned disk when offline identity reset
failed because the image lacked the legacy D-Bus directory. Recovery now
requires that no VM is defined for that disk, resumes customization without
repeating the copy or cleanup, and creates the missing directory before linking
the machine identity. A regression test verifies reset and repeated execution.
Temporary identity diagnostics remain disabled by default.

## Verify guest resources and resume guest configuration

Implementation: `e27958ce5b6972da979f720cc85e2acade748084`,
`2d8343a319d05b1388e3466bba8d3288a4fcaa3b`, and
`a73848a9acc75f6bfcd4d2a480d99ec6b80b1346`.

Authenticated access succeeded after boot. The initial memory assertion was
too strict for the guest's usable memory; the user accepted the small difference.
Verification now confirms the requested allocation in libvirt and accounts for
kernel crash-recovery reservation when checking guest-visible RAM. Basic
verification diagnostics are optional and disabled by default, and credentials
remain protected. A filesystem inspection failure was corrected by keeping the
comma-separated output columns in one command argument.

Guest configuration was resumed against the existing VM, avoiding a second
clone. Linux identity, requested CPUs and allocation, installer cleanup, and
removal of the unused AAP account passed verification. RHEL registration and the
full DNF update succeeded. The guest rebooted, reconnected, and passed the final
check with no pending package updates. The deployment job completed successfully.
All eight local tests passed. Environment-specific controller and guest details
remain encrypted rather than appearing in this history.

## Reproduce lasting configuration through separate roles

Implementation: `8c0497114b15efbd83b424e0c2675698f59c80e5`.

The user authorized direct SSH access with sudo for work on the project VM.
Every lasting design or configuration change must be documented and represented
in Ansible roles called by the playbook, committed and pushed to this private
repository. The decision history records final decisions rather than individual
interim steps, experiments, or retries. Project instructions preserve this rule
for subsequent work; credentials and environment-specific configuration remain
Vault encrypted.

The existing deployment was reorganized into separate roles for VM provisioning,
guest verification, and RHEL registration and updates. Cleanup templates and
identity-reset files belong to the provisioning role, and the playbook calls the
roles in order. Existing recovery tags and protected logging remain available.
No live VM configuration was changed by this refactoring. Syntax checking, all
eight tests, and guest-configuration task selection passed.

## Delegate settled decisions to a background implementation agent

Implementation: `318ec83a7af06efec1be920da2fc2a24915836d3`.

The user chose one reusable background subagent to keep the main conversation
focused on building and design. Settled decisions are handed off sequentially
for configuration changes, separate Ansible roles, documentation, validation,
commits, and pushes. Sequential handoffs avoid conflicting repository edits and
concurrent VM configuration changes while independent design discussion continues.

A design agreement is explicitly implementation pending until the agent reports
the result implemented and verified. Dependent work waits for that result.
Completion notices remain brief; blockers requiring decisions or approval return
to the main conversation. Background execution retains existing security,
monitoring, validation, and approval requirements. This change documents the
workflow only and does not change the VM or require additional infrastructure.

## Establish trusted container host preflight

Implementation: `f7c3f7ae3b3da40397e2d130e57d9baafb084255`.

The user authorized a rootless Podman foundation with native Claude Code, Codex
CLI, Mistral Vibe, and Gemini CLI harnesses. Content preparation is in progress;
image builds and live validation are not complete. Roles remain configurable,
with participant responsibility metadata but no communication capability or
shared credentials. Provider authentication remains an operator step.

A separate read-only Ansible preflight role obtains the guest SSH public key,
root filesystem capacity, storage layout, and installed packages through the
existing authenticated AAP path. This establishes agent-side host trust without
trusting an unauthenticated key scan, and checks that the filesystem has enough
capacity before container builds. The preflight does not install or update
packages. Environment-specific results stay in protected controller artifacts
and encrypted configuration.

## Build reusable native assistant containers with certified Podman

Implementation: `5fb75abd8650da07e6af68c5f4bebc16c04d1b0e`.

The user chose Podman and native Claude Code, Codex CLI, Mistral Vibe, and Gemini
CLI harnesses, reusable across independently configured roles and instances.
Separate Ansible roles configure the rootless host and build the four images.
Certified Automation Hub content was verified as `redhat.rhel_system_roles`
1.120.5, whose Podman role and image module provide the required supported
operations. The certified archive checksum was verified before local use;
community Podman content was not substituted. CLI versions and base image
digests are pinned, and normal reruns preserve completed image builds.

A dedicated password-locked account has no sudo access. Its user manager delegates
only the CPU, memory, and process controllers needed to enforce container limits.
Instances use an unprivileged process, read-only image filesystem, dropped
capabilities, no new privileges, and separate persistent homes and workspaces.
Only those instance directories are mounted. No engine socket, broad host mount,
shared provider credentials, or agent sudo access is provided. Filesystem capacity
was sufficient, so guest storage was not expanded. The user explicitly allowed
trusting this fresh demo guest for initial SSH access; subsequent connections
require the recorded key, whose public value is retained encrypted.

All four images were built on the guest. Offline native version/help checks,
actual root mount protections, zero effective capabilities, no-new-privileges,
kernel-enforced limits, and persistent state isolation across two instances per
flavour passed. All fifteen local tests and playbook syntax checks passed.
Provider authentication and model-session verification remain operator setup;
no inference, paid API use, external messaging, or session-credential copying
occurred. Runtime account and verified deployment metadata remain Vault encrypted.

## Keep observer roles outside worker-visible collaboration context

Implementation: `5fb75abd8650da07e6af68c5f4bebc16c04d1b0e`.

Working roles know the responsibilities of their collaborating participants,
without gaining access to their data, credentials, or restricted contexts. The
user decided that working agents must not be told about the observer/evaluator.
Operator-provided roster entries therefore carry explicit worker visibility;
hidden entries are excluded from native worker instructions and the source roster
is not mounted. Evaluation instructions and reports remain outside worker-readable
communications. Tests verify that hidden observer metadata is not rendered.
No production roster or provider-role assignment is hardcoded.

## Record the next communication and connector architecture

Design documentation: `5fb75abd8650da07e6af68c5f4bebc16c04d1b0e`.

The accepted next design uses SQLite for central discussions, handoffs, verified
outcomes, and connector execution audit. Summarizing and orchestration remain
separate responsibilities. One observer initially produces distinct output and
design reports, privately evaluating quality and recommending only significant,
evidenced workflow or design improvements. Benefits and complexity or cost must
be considered; retaining the current design is a valid outcome. Recommendations
do not automatically reassign roles or implement changes.

Agent containers and local listeners should remain available without model calls
while idle. Relevant addressed events may invoke native harnesses or resume saved
sessions, subject to verifying each harness's support. Bounded rounds and completion
signals prevent discussion loops. The observer may privately recommend stopping
unproductive discussions; the orchestrator pauses or closes the thread, cancels
queued discussion responses, and gives a truthful stop instruction. Containers and
unrelated implementation work continue. Unfinished questions are retained and
reopening requires an explicit orchestrator or user decision. Exhausted subscription
allowances pause work without automatic paid API fallback.

Two distinct Claude Code connector roles separate private and corporate credentials,
contexts, and scoped tools. General shell and unrelated tools are disabled for these
roles. Reads come first; later writes require approval enforced by the tool layer.
The orchestrator routes routine work, implementation of settled designs, or debate
followed by implementation when ambiguity or tradeoffs warrant discussion.

Every connector action requires an audit of actual tool attempts and results,
including account boundary, task/thread/correlation IDs, typed action, timestamps,
status, error code, item count, and applicable write approval. Retries retain a
logical operation ID. Complete resource content and secrets are excluded by default;
sensitive resource identifiers stay in protected runtime storage. Completing a task
preserves its history rather than deleting it.

These central services, listeners, observer reports, connectors, audit adapters,
and allowance controls are documented design agreements awaiting implementation.
The container foundation does not deploy them.

## Require attachable native sessions and event-driven delivery

Design documentation: `d2c60126cbe38bd4e550c226424271c97d016a0a`.

The user requires native harness sessions in tmux inside continuously running
rootless Podman containers, so the operator can attach. This is a TODO rather
than deployed functionality: current foundation commands remain short-lived.

Prefer existing messaging/listener software over developing a new service. Timed
inbox polling is rejected. Addressed events must reach the existing running
harness through a supported inbound interface; being an MCP tool client alone
does not prove idle-session input support. Validate native capabilities for all
four harnesses before selecting a transport. If tmux wake is used, submit only a
fixed notification and keep message content in authenticated MCP delivery.

No messaging candidate, persistent session deployment, or polling implementation
is selected by this decision. Instance isolation and existing access boundaries
remain requirements.

## Set up Agents Connector with native isolated tmux sessions

Implementation: `c6a79cb6a17c17a2ae8a06db97e0bfd6c81903b5`.

The user selected Agents Connector and authorized a dedicated Linux account with
the setup in its home, using the existing Claude Code, Codex and Gemini images
and omitting Vibe. A separate Ansible role/playbook creates the password-locked
rootless account, installs checksum-pinned upstream release 0.1.0, extends the
existing credential-free images with tmux, and enables broker, gateway and container
availability services. Account/home and guest details remain encrypted in Vault.

The stock launcher assumes shared host paths and tmux. A small lifecycle and wake
adapter preserves isolated home/workspace mounts and runs tmux inside continuously
available containers. The stock broker retains SQLite and native MCP/hook message
delivery. Only fixed event notices enter tmux; message bodies stay in authenticated
IPC. No timed inbox polling or new orchestration platform is introduced.

Stock broker IPC also exposes administrative requests. Its socket and database
therefore remain host-private. Per-instance filtered sockets enforce authentication,
message identity and ask/reply ownership while denying administration. No engine
socket, host tmux socket, sudo, provider-credential sharing or broad host mount is
provided to workers. Routing service refresh is independent of container lifetime.

Rough prompts cover visible orchestrator, Codex builder, Claude investigator, Gemini
challenger and summarizer, plus separate inactive observer/evaluator and private
and corporate connector profiles. Worker instructions list only collaboration
roles. Hidden profiles are not registered or mounted in worker containers. Observer
transcript/private reporting and connector scoped tools/credentials/audit adapters
remain pending; their prompt text does not implement these controls. Automated
orchestration, discussion-stop enforcement and allowance handling remain pending.

All nineteen local tests and Ansible syntax checks passed. Live offline validation
passed native version/help, inside-container tmux, enforced isolation, identity and
administration denial, SQLite persistence, all three stock hook formats, urgent
message/question fixed-only wake and busy suppression after cooldown expiry. Five
containers and all three enabled user services were verified running. Successful
checks remove their synthetic fixture messages. Disk capacity remained sufficient.

Native provider authentication and model sessions are not configured or launched.
Operator login, explicit native session launch and Codex hook approval remain
necessary. The setup performs no paid inference or external connector action.

## Control the connector group through a user target

Implementation: `d8e2e7b05a7c34f6055eb5d281f52c1131a864d7`.

The user chose `assistant-connector.target` for one start/stop/restart control.
Only this target is enabled for the lingering user manager's startup. It requires
the existing broker, gateway and container services, with dependency ordering and
service `PartOf` relationships propagating group stop/restart. Individual services
are disabled for independent boot startup; no synthetic master service is created.

The container service explicitly stops only the five named worker containers and
clears launch markers. Persistent native homes, authentication state, workspaces
and SQLite remain. Starting stopped containers restores tmux shells if needed;
model sessions are not automatically launched or resumed. Routing-service refresh
remains independent of container lifetime. Target stop can return while ordered
child stop jobs finish, so lifecycle verification waits for actual service states.

The opt-in lifecycle check refuses native login/model processes or launched work.
It verified all services inactive and containers stopped, then successful start
and restart with tmux and unchanged SQLite/persistent data. The final Ansible run
passed without configuration changes, and all nineteen local tests passed. Final
inspection confirmed only the target enabled, all four units active and all five
containers running. Authentication and live model sessions remain pending.

## Scope native logins and provide all eight role containers

Implementation: `1e4236ccb521134750b94e40ae6b8235012823e1`.

The user requested actual native CLI installations in five separate home directories:
work and private Claude accounts, Codex, Gemini and Mistral. Each directory has
its own simple login command and contains its installation, configuration,
credentials, caches, sessions and temporary files. The separate native-auth
Ansible role reproduces these installations without global host CLI packages.
A pinned official portable Python runtime makes the Mistral installation
compatible with the guest operating system. Gemini uses its native Google
sign-in flow rather than requiring a cloud SDK.

Explicit role launch copies only missing provider authentication files from the
matching account boundary, preserving independent role configuration and existing
refreshed credentials. Authentication is operator-controlled: automation neither
authenticates nor invokes models, and does not promise automatic token refresh
synchronization between separate native homes.

All eight role containers now remain available with inside-container tmux. Five
collaboration roles use the worker broker; the hidden observer and the private
and corporate connectors remain outside that broker. Connector general tools
are disabled and external connector services remain unconfigured. Mistral is
installed for native use but is not assigned a team role. The existing user target
manages all eight named containers and preserves persistent state.

One editable home prompt file contains all role sections and is preserved on
Ansible reruns. Only the selected section and collaboration roster are rendered
into each native workspace; the full prompt file is never mounted into workers.
The operator control utility supports launch, tmux attach, prompt application
and a live stock-broker event-stream viewer without timed inbox polling.
The observer receives an operator-refreshed read-only transcript snapshot;
private report delivery writes only to the orchestrator workspace. Continuous
evaluation callbacks, automated orchestration and parallel-project creation
remain pending. No create-project command is presented as implemented.

The home operator guide was renamed to README.md at the user's request and
documents actual login, target, role, viewer and prompt commands. All twenty-five
local tests and playbook syntax checks passed. Live offline validation confirmed
eight tmux containers, five scoped native installations, event-stream delivery
and the private observer/report boundary without model calls. A plaintext
repository audit found no environment identifiers or access secrets; native
credentials and operator-edited prompts remain outside Git, and environment
metadata remains Vault-encrypted. VM resources were not changed.

## Create and operate isolated assistant projects

Implementation: `61d1709b0b028db42cede35dfcceeeaa72c128e7`.

The user approved a reusable project framework, with each named project under
the runtime home projects directory. The create-project command invokes the
existing stock broker to create its actual SQLite schema and five-worker registry;
it also prepares eight role homes/workspaces and the singular editable
assistant-prompt.md containing the project goal and all role sections. Creation
does not start containers or models, and existing project contents are preserved.
Conservative project-name validation prevents path traversal and symlink projects.

Each project has a separate database, broker, identity-filtered IPC, native homes,
workspaces and container names. Only the selected role prompt plus goal and
permitted collaboration roster enter each container. Vendor installations and
login directories remain outside projects; only missing matching authentication
files are seeded into role homes. Native refresh state is not overwritten.

Start requires saved subscription/OAuth credential format for Claude work/private,
Codex and Gemini before activating any project service, then launches all eight
native harnesses without initial task prompts. This local check does not verify
remote token validity. Native trust/onboarding and hook approvals remain explicit,
and no paid API fallback or security bypass is introduced. Mistral remains
installed but unassigned to a team role.

Per-project systemd targets order broker, gateway and container services. Stop
and restart affect only the named project's processes, preserving its database,
credentials, workspaces and native session files. Restart starts new CLI sessions;
automatic conversation resume is not claimed. Project targets are not enabled
at boot. Legacy default commands remain available, and project names matching
role names cannot accidentally route a stop to the default group.

The hidden observer and private/corporate connector roles remain outside worker
brokers. Observer transcript refresh/private report delivery remain manual.
Connector general tools remain disabled; external tools, automated orchestration
and continuous evaluation are not implemented by this framework. The home
README and repository documentation describe actual project commands and limits.

Thirty-one local tests, Ansible syntax and the final deployment passed. Live
validation created two disposable stock-schema projects, checked missing-auth
refusal in an isolated home, started eight explicitly dummy harnesses per project,
verified event-stream delivery, project-specific stop/restart and retained SQLite,
and removed only its own fixtures. No provider authentication or model request
was performed; authenticated native-session startup remains to be exercised by
the operator. The original eight containers remained running. An audit of
sixty-three plaintext repository files found no environment identifiers/access
secrets; environment metadata remains Vault-encrypted. VM resources were unchanged.

## Retire the redundant original runtime

Implementation: `f9d0eeb9272c45b0e951059974ba36c3cb94894b`.

The user approved retiring the original non-project group now that the named
project framework provides the intended lifecycle. A separate retirement role
stops/disables/removes only its original non-instance target and three services,
and removes exactly the eight original container definitions. Their bind-mounted
profile homes, authentication state, prompt defaults and SQLite data are retained.
Project instance templates, native installations and actual project data are
untouched. The foundation role no longer recreates or starts the retired group
on subsequent Ansible runs.

Operator commands require a project name and refuse no-project operations with
a helpful message. There is no all-projects master target. The runtime home
README starts with the short create/edit/start/attach workflow and contains only
the current project lifecycle instructions. New projects reuse the retained
profile specifications and editable prompt defaults, not the original database
or native credential homes.

Preflight found only idle shell/tmux processes in the original containers.
Thirty-two local tests, Ansible syntax and retirement deployment passed. Live
checks confirmed original units not found, original container definitions absent,
saved data retained, project creation/prompt routing still functional, and
no-project stop refused. Only the disposable creation-check project was removed;
no real project or provider session was started or changed. The previously
verified project instance templates and lifecycle were preserved. A plaintext
audit of sixty-four repository files found no environment identifiers/access
secrets, and runtime metadata remains Vault-encrypted.

## Share project artifacts while retaining private role context

Implementation: `8ea9a05f5fc7e6359eff3154d26e5057aa22efe7`.

The user requested a shared project workspace. Creation now prepares a project
workspace directory, mounted at /workspace/shared in role containers. All seven
working roles receive read/write artifact access; the observer receives read-only
access. Native homes, credentials, role instructions and full prompt/account
contexts remain separate. Connector tools stay disabled and prompts permit
publication only of explicitly authorized project results. Codex uses its native
workspace-write sandbox with on-request approval, without bypassing approvals.
Agents coordinate file/task ownership through the orchestrator rather than a new
custom locking mechanism.

The separate project_workspace Ansible role adds missing directories without
modifying existing contents. Active containers are preserved; their new mounts
are applied on a normal project stop/start. Only stopped definitions with differing
mounts are rebuilt, retaining all bind-mounted state. The home README and project
documentation explain both host and container paths and this migration behavior.

Thirty-four local tests, playbook syntax and deployment passed. Live disposable
project checks verified all seven writer roles, cross-role artifact reads, observer
read success/write denial, private-context separation, project isolation, event
streaming and persistent database/lifecycle behavior using dummy harnesses only.
Fixtures were removed; no provider authentication or model requests were made.
A plaintext audit of sixty-five repository files found no environment identifiers
or access secrets, and metadata remains Vault-encrypted. No dependencies, images
or VM resources were changed.

Work Claude is intended to use Vertex AI, while the current authentication/preflight
layer supports OAuth files. The guide marks Vertex configuration pending and does
not recommend work OAuth login. Real project startup requires the selected work
backend; the shared-workspace validation does not claim authenticated model startup.

## Isolated work/private native authentication and initial release boundary

The user chose work and private profiles for all four native harness vendors. Each profile keeps its own installation, configuration and authentication state; existing personal data is migrated without importing it into work contexts. Work Claude and Gemini use Vertex ADC, while private Gemini uses Google OAuth and private Claude uses its supported account plan. Native login outcomes distinguish local credential evidence from model entitlement. Explicit local clearing preserves unrelated settings and refuses active use. Personal Gemini restricts its native authentication choice to OAuth so the API-key dialog cannot accept an OAuth verification code. Concurrent profile login refuses existing native sessions rather than stopping user work. Google Cloud SDK installation remains approval-gated; Mistral team integration remains future work. Implementation: `45c8784`.

At the user's explicit request, release `v0.0.1` was tagged and published from existing committed baseline `df70417418b8a2e88658e8772df96a26d0acb293` before these pending changes were committed. Subsequent feature commits increment minor versions, and fixes/documentation commits increment patch versions; release notes record each version. This preserves the published baseline rather than representing uncommitted development VM changes as its content.

## Selectable environment profiles and authoritative project assignments

The user chose one environment per Linux user, with eight available work/private profiles and enablement recorded in a strict non-secret home-level JSON file. Separate home-level project configs own role-to-profile assignments; project prompt files retain only goals and role prose. This avoids conflicting editable account settings and keeps unsupported or disabled assignments actionable before startup. Native state is separated per account and live account replacement is refused, preventing stale credentials from another context. Existing data and disabled profiles are preserved. Current roles retain their native adapter; Mistral team participation remains a required future upstream integration.

The user requested concise home and repository README.TLDR guides alongside the full guide, and protected bounded environment metadata for diagnostics. Metadata excludes authentication values, conversations, prompts, databases and raw CLI output; manual exports contain only prescribed fields/files. Backlog items distinguish required custom roles/Mistral integration from optional custom account contexts and multiple environments. Implementation: `a587343`.

The personal Gemini OAuth input stage was verified without submitting authentication or model input. The user then encountered a provider restriction rejecting this native client for individuals. This is an access limitation, not authorization to alter client identity or switch to paid API authentication. Work Vertex access remains a separate setup path.

## Recognizable login status messages

The user requested the exact `[AC-Agents]:` prefix for wrapper-owned login outcomes, clear confirmations and errors so these messages are distinguishable from native provider output. The native providers retain their own output, and local credential evidence still does not imply model access. Atomic helper updates preserve active login processes and existing credentials. Implementation: `ccf07f2`.

## Actionable login follow-up guidance

The user requested useful next steps after each wrapper login result. Guidance distinguishes local saved evidence from model access and points to provider-specific prerequisites or retirement limitations. It does not launch model checks, switch to paid APIs or erase credentials. Native Vibe authentication storage was checked against the installed source before advising a retry. Implementation: `c880a3d`.

## Operator-owned deployment and primary target diagnostics

The user chose a fresh deployment path that does not grant this coding agent destination access. An operator-owned external Vault provides connection settings; the complete role chain supports both local connections and SSH destinations without developer-specific account/image/Vault dependencies. No provider authentication or inference occurs during installation. Protected target environment logs are primary; controller metadata covers preconnection failures and can be replayed later. Only prescribed, validated metadata is exported, excluding raw output, credentials, prompts and conversations. Fresh-VM end-to-end deployment remains untested; local/SSH fixtures, failure/export tests and syntax checks establish the current validation boundary. The version helper follows feature-minor and fix/documentation-patch increments, while formal releases also require pushed annotated tags and published GitHub notes. Implementation: `decdc5c`.

## Headless Vibe browser authorization

Installed Vibe 2.26.0 stops its authorization worker when a GUI browser cannot open, before native polling begins, while retaining the generated link and later waiting-step text. The user can complete that link in a browser but the stopped worker cannot receive the result. A profile-local supported Python browser handoff reports successful handoff so native polling, expiry and PKCE exchange continue unchanged; it does not read authorization codes or bypass authentication. Native fake-gateway validation confirmed the difference without network/model calls. Session guards recognize rewritten native process titles and preserve active user work. Implementation: `4bd241e`.

## Full root capacity for fresh 20 GiB clones

The user chose 20 GiB as the default cloned disk capacity for future Linux VM provisioning, with automatic growth of the existing direct last GPT root partition and XFS filesystem. The golden image retains a small filesystem, so virtual resizing alone leaves capacity unused. A separate root-growth role provides protected partition-table backups, partition-identity checks and idempotence. The existing VM had already completed an explicitly authorized 50 GiB expansion and is preserved without shrinking or another reboot. No separate additional-disk resize feature is retained. An unchanged guest-role rerun validates current idempotence, while a fresh 20 GiB end-to-end VM deployment remains untested. Implementation: `282f06b`.

## Approved scoped Google Cloud SDK for work Vertex login

The user approved the required SDK dependency. Google Cloud CLI 588.0.0 is installed within the two work profiles, with independent configuration and ADC paths and only immutable program assets reused. Work login guides operator-selected project, location and enabled model IDs without enabling cloud APIs, altering billing or making model requests. The versioned archive pin was corrected by verifying its full payload against the official rolling archive and published digest; different tarball packaging must not share an assumed checksum. Installed release checks and owned archive cleanup make the installation repeatable. Native Gemini selects Vertex only after scoped ADC completion while preserving unrelated settings. User authentication and model entitlement are not inferred from installation. Implementation: `8971d51`.

## Fresh complete installation through normal AAP jobs

The user requested a separate fresh VM as an end-to-end automation test, with all target changes performed by normal AAP job templates rather than ad-hoc commands or manual SSH. A separate encrypted definition protects the existing deployment. The new playbook uses the discovered guest for root growth, complete updates and the full native environment role chain, then exercises disposable dummy-harness project isolation without authentication or model calls. Configuration-only recovery uses a vaulted guest address and skips successful provisioning. Installed metadata can use the AAP project revision. At this commit, syntax is verified and the actual deployment remains pending. Implementation: `7034bc1`.

## Explain full Vertex model identifiers at login

The operator encountered unclear rejection of display names and aliases. Model prompts now show a complete Vertex identifier and explain invalid input while keeping project/location entitlement unverified. This improves guided login without cloud lookups, model calls or changes to existing sessions. Seven scoped regression tests pass. Implementation: `b1f2d02`.

## Explicit Vault password configuration

The checkout-relative password setting resolved to an unrelated missing path under AAP even though its attached Vault credential worked. Tracked configuration now delegates Vault access to explicit operator input or AAP credential injection, avoiding developer workspace assumptions. Syntax and portable deployment tests pass. Implementation: `3ba883f`.

## Prefer suitable Ansible and certified content

The user chose Ansible for clear deployment/configuration tasks and an obviously suitable certified collection when available, while avoiding complexity added merely to force a collection. Runtime CLI/authentication/router application logic remains code installed by Ansible. Deployment-helper review follows blocking fixes. Developing project-specific Ansible modules and packaging a collection is an exploratory future item, not current implementation.

## Fresh native launcher bootstrap and safe recovery

The first normal AAP fresh deployment reached native CLI installation after provisioning, full filesystem growth, updates, image builds and broker installation. Its launcher imported a helper that was installed only after version validation, causing the fresh bootstrap to fail. The helper now precedes launcher invocation, and all contexts are checked on recovery to detect incomplete metadata markers. A behavioral regression reproduces missing-helper failure and successful installation without inference. The discovered endpoint remains encrypted and recovery skips provisioning. Implementation: `9a56278`. Separate sudo recovery credentials were corrected in `178fc83`. The Ansible/certified-content policy and exploratory collection backlog were recorded in `a35bf43`.
