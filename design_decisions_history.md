# Design decisions history

## Check unfinished background work every ten minutes

Documentation: `54f38c9`.

The user refined notification-driven monitoring with a ten-minute health check for
unfinished agents that may be blocked, deferred, stalled or need resuming. Results
and blockers are still shared promptly when reported. Explicit holds and completed
tasks must remain undisturbed; the old fixed 20-second polling rule stays removed.

## Prefer background completion notifications over fixed polling

Documentation: `305be6a`.

The user removed fixed 20-second subagent polling because completion is already
reported automatically and repeated checks add processing overhead. Background
agents now report by notification; status checks remain available for blockers
or missing notifications. External jobs without notifications still require
appropriately spaced checks and verified outcomes.

## Hold task-specific model selection while retaining its priority

Documentation: `2cf4bcb`.

The user put cost- and quality-based task-specific model selection on hold,
but explicitly retained its priority when resumed. No model-selection behavior
or runtime configuration changed.

## Continue the current communication route while evaluating alternatives

Documentation: `dad244c`.

The user explicitly retained agents-connector with tmux as the active development
route and requested a pending review and decision covering the current design,
acpx with a replacement coordinator, and their combination. TODO contains the
comparison, limitations and recommendation: verify the existing route first and,
if reliability remains inadequate, trial structured delivery with the existing
broker before deciding on migration. This records a review plan, not acceptance
of ACP/acpx or a replacement architecture. No runtime changes or new deployment
automation are introduced by the documentation.

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

## Practical Ansible good practices and verified fresh deployment

The user requested applicable parts of the Red Hat good-practices guide without unnecessary framework complexity. Role-owned variables and typed/documented interfaces now clarify inputs; explicit escalation, a reboot handler, built-in retention and a single role-instruction template improve maintainability and repeatability. Shared encrypted dictionaries and legacy VM resource aliases remain compatible. Full check-mode and zero-change convergence are not claimed where live builds or disposable verification require mutation. Implementation: `c79caea`. Production-profile lint reports no findings and 71 tests pass. Normal AAP configuration recovery job 1376 completed the original fresh bootstrap; job 1380 verified the refactored full role chain, native CLI and SDK versions, full cloned root capacity, and two-project isolation without authentication or inference. The good-practices review records remaining gaps, including controller configuration-as-code and CI, rather than claiming complete compliance.

## Reuse existing quality tools without silent installation

Practical guide adoption now includes one tested quality command shared by local pre-commit configuration and a manually dispatched trusted-runner CI workflow. It runs tests and production-profile lint, preserves failure status, and requires explicit external Vault access without installing dependencies. CI registration and pre-commit installation remain operator choices; no hosted secret or paid platform configuration is introduced. Three behavioral tests cover stopped execution after failure, missing Vault input and test-only execution. Implementation: `9c0f1a3`.

## Reusable rules for future sessions

The user requested one comprehensive context document for future assistants. SESSION_RULES.md consolidates explicit working rules and settled boundaries while directing readers to current source, release notes and verified deployment outcomes. It contains no credentials or environment identifiers and does not turn pending capabilities into completion claims. Implementation: `140dccc`.

## Evaluate APME locally without broadening deployment

The user authorized a pinned isolated APME installation and local OPA container evaluation. Its full-project scan failed certified collection provisioning, so a builtin-only role subset was evaluated separately and coverage limitations were retained. The partial scan reported no remaining policy violations and proposed only value-preserving YAML formatting. No automatic fixes, AI requests, authentication reuse or mandatory gate were introduced. Installation capture and reproducible audit instructions are documented. Implementation: `5692d3c`.

## Enable only account profiles the operator currently uses

The operator disabled unused work profiles in the current environment while retaining their installations, credentials and project definitions. This is an environment-specific enablement choice, not a removal from the eight-profile catalog or a default restriction for future operators. Existing account state and running work are not erased or silently reassigned.

## Safely replace a disposable deployment test clone

The user explicitly authorized removal of only the second test VM and a fresh third-clone end-to-end deployment. A dedicated normal AAP retirement playbook defaults to read-only preflight, validates the selected disposable naming convention, verifies one exclusive regular clone disk against all other domains, gracefully shuts down the selected guest and checks that the golden image and other domains remain intact. Separate encrypted retirement and fresh definitions prevent accidental reuse of the old recovery address. Safety rejection tests pass and the new role passes production lint. Actual AAP retirement and fresh deployment results are tracked separately after execution. Implementation: `e1545f9`.

## Interpret completed APME checks against the supported deployment

The user authorized all read-only APME scans without repeated approval and relevant fixes after contextual security, compliance and stability assessment. The certified dependency was supplied through upstream proxy conversion/cache using its original SHA256-verified artifact. Full-codebase Native, OPA and Ansible checks completed, followed by optional collection-health and Python auditing. Findings include intentional privileged actions, statically unresolved encrypted inputs and future-version migration warnings; these do not justify blanket rewriting. Optional dependency coverage limits are retained, including the non-PyPI certified wheel and old pip in the disposable scanner environment. No project code defect was selected from this first assessment, and no automatic source edits or AI requests were made. Implementation: `e169e6b`.

## Supported personal Antigravity with scoped native authentication

Implementation: `3a5a1b9` (version 0.10.0).

Personal Gemini moved to the supported official Antigravity native CLI because
Google retired the former personal Gemini CLI client. Keep the existing profile
name and isolate the pinned program, HOME, configuration and authentication there;
Gemini work continues using its native CLI through Vertex. A dedicated Ansible
role downloads the official checksum-verified binary. Existing account data is
not migrated and deployment performs no authentication or model inference.

Current Antigravity deliberately uses file token storage for SSH/container
sessions and can fall back to files when a keyring is unavailable. Consequently
GNOME packages are unnecessary for this selected native workflow. Keep profile
directories 0700 and launcher umask 077, with credentials controlled by the
operator. These local permissions are not encryption at rest and do not protect
against root, sudo or other processes under the same runtime account. Git secrets
remain encrypted independently. No forced keyring bypass was introduced.

Login, local clear and saved-auth reporting use the scoped native wrapper. Saved
credentials do not prove model entitlement. Explicitly reject personal Antigravity
project assignment until an agents-connector adapter is implemented, rather than
claiming its different native protocol works with the existing Gemini ACP adapter.

Validation: 80 local tests passed, production Ansible lint had zero findings,
and targeted Ansible deployment to the original environment succeeded with all
eight native version checks. Read-only Antigravity help/version checks passed;
the personal profile and its Gemini state directory were verified mode 0700.
No login or inference was performed by deployment. Operator authentication and
personal team integration remain separate subsequent verification steps.

## Make Ansible operations easier to read without changing behavior

After the APME assessment, the user requested an end-to-end Ansible readability review that retains relevant practices and functionality. Entry playbooks and roles were reviewed from provisioning through validation. Three shell pipelines now use explicit cmd/executable/chdir mappings; normalized parsed tasks confirm identical commands, conditions and async settings. A repeated internal root-growth result name was simplified and the user module desired state made explicit. No new architecture or role consolidation was introduced. All 80 tests and production lint pass; the APME rescan completes with the three M027 pipeline indicators removed and other contextual limitations preserved. Implementation: `00af762`.

## List existing projects without needing a project argument

The user tried the natural team --list command and requested it after the router incorrectly reported a missing project. The operator router now hands off --list and list-projects before requiring a selected project, including when a project environment variable is present. Listing inspects only valid-name regular project directories with initialization markers, expected files and workspace; it does not open databases, prompts or credentials or start services. Six new tests cover actual installed-router execution, empty/multiple/partial/invalid/symlink cases and authentication isolation. All 86 tests and production lint pass. Targeted Ansible project-framework deployment succeeded on the original VM and both actual listing aliases returned exit zero. Implementation: `fb49a04`.

## Make operator help and command errors explicit

The user requested complete team --help and clear invalid-command errors after create NAME produced a misleading missing-project message. The project framework now lists every public command with parameters and brief explanations; the router delegates discovery and environment commands without requiring project or auth state. Unknown commands explicitly identify the invalid action, while valid commands with missing project parameters retain a separate error. No create alias was invented. All 90 tests and production lint pass, including real installed-router checks with and without a project environment. Targeted original-VM project-framework deployment completed successfully before the subsequent deployment pause. Read-only runtime verification confirmed complete help, explicit invalid create and successful listing. Further original-VM deployment is held at the user's request; installed metadata remains the implementation version. Implementation: `83ebd8f`.

## Distinguish project prompt sections from inactive examples

The user selected bracket sections such as [Role: Investigator] with # comment lines rather than Markdown role headings. All starter example prose and human guidance are comments, removed before delivery to harnesses in the new format; no fallback activates examples. The shared goal uses [Project]. Authors add their active text or uncomment examples. Each supported role must appear exactly once and receives only its own active section plus the shared goal and existing workspace context. Legacy # Role: files retain their prior interpretation and existing project files are preserved; new projects convert old default-template prose into commented samples. Seven new tests exercise comment exclusion, blank roles, legacy compatibility, aliases, validation and private-observer isolation; all 97 tests and production lint pass and the contextual APME rescan completes. The operator explicitly holds deployment of the new template/parser/generator to the original VM while starting a first team; these changes are committed source only. Implementation: `14914da`.

## Wait for idle tmux before native harness launch

Implementation: `c7d4473`.

The first project launch reached tmux commands before a newly detached Podman
container had finished its idle entrypoint. Restarting that idle container made
tmux immediately available without a model request, supporting a startup race
rather than a persistent permission problem. Launch now waits for readiness for
at most 15 seconds and reports stopped containers or timeouts explicitly. Existing
containers restore a missing session only after PID 1 reaches its idle sleep,
avoiding competing tmux creation. New entrypoints stop on tmux initialization
failure. Five readiness regressions passed, along with all 102 tests and production
Ansible lint with zero failures or warnings.

## Protected editable-prompt migration and parallel implementation

Implementation: `2e3c616` (0.14.0).

The operator requested converting an already edited project to explicit bracket
sections rather than leaving legacy role headings. Conversion is opt-in through
Ansible, preserves role-specific custom instructions and meaningful heading text,
comments known rough-template guidance, and writes a protected backup before atomic
replacement. It does not restart sessions or alter saved account credentials.
Independent background tasks now run in parallel; shared Git and VM changes remain
coordinated to prevent conflicting writes.

## Human-readable operational diagnostics

Implementation: `373b8f7` (0.15.0).

The operator wanted logs made for humans alongside structured JSON. Runtime events
now have matching readable lines, correlation IDs, protected permissions and bounded
rotation. Known failure guidance is fixed safe text instead of unfiltered native
errors. Deployment transfers provide readable counterparts too. Exports continue to
validate JSON metadata and exclude arbitrary text, credentials and conversation data.
Validation: 106 unit tests passed before commit; focused diagnostic and migration
cases passed; production Ansible lint passed for the affected role and transfer play.

## Verify the guarded lifecycle with a complete fresh AAP run

The guarded retirement design (`e1545f9`) was exercised through read-only preflight job 1389 and removal job 1391. The selected disposable test clone and its exclusive disk were removed while other domain names and the source image were preserved. Fresh deployment job 1394 then completed all roles in one pass without recovery or retries at `405c24f2f44259dab90545a63d0bd6832b867972`, version 0.9.1. The run verified full root growth, package updates/reboot, container and host-native clients, the scoped SDK and disposable two-project isolation, without copying provider authentication or invoking models. Later changes are outside this tested snapshot; further deployments remain separately authorized. Detailed results and limitations are recorded in DEPLOYMENT_TEST_RESULTS.md.

## Verified operator prompt and log deployment

Deployment source: `949d2c6` (0.15.2), including prompt migration `2e3c616`
and readable diagnostics `373b8f7`.

The targeted Ansible project-framework deployment completed successfully with zero
failed or unreachable tasks. The explicitly selected operator-edited project was
converted to eight bracket role sections and has one protected backup; custom
instructions were preserved by migration validation. Live checks verified readable
and JSON log correlation and 0600 file permissions. Authentication files and active
sessions were not changed or restarted. No prompt contents were included in reports.

## Supply Codex process inspection and repair only its failed builder

Implementation: `c1806f8`.

The real authenticated Codex session exposed a runtime dependency missed by CLI
version checks: its managed app server invokes `ps`. The tmux image extension now
includes `procps`, and image validation executes process inspection in a temporary
container without credentials or networking. The certified image module supports
selected flavour rebuilds. An explicit repair refuses live or non-Codex builder
panes, replaces only the failed builder container and preserves mounted private
state and shared artifacts. No work prompt is supplied on restart.

The targeted original-environment Ansible run rebuilt only Codex, passed image
process inspection and repaired the dead builder: 23 successful tasks, zero
failures. Its actual native process and tmux pane remained alive in three checks
over 10 seconds. All seven sibling container IDs and start times were unchanged.
Four focused repair safety tests passed within the full 110-test suite, and
production Ansible lint passed with zero failures or warnings.

The user also established a stricter storage rule: model authentication material
must never enter Git, even encrypted. Deployment configuration may continue using
Ansible Vault. No new secret manager or credential migration was introduced.

## Restore event wake-up bookkeeping after builder repair

Implementation: `24fa9a8`.

Final project status inspection found that the image-repair path started the native
builder but omitted the launch marker used by event wake-up. Normal launch callers
create that marker separately. Repair now restores it only after successful native
launch; failure leaves it absent. A guarded marker-only recovery mode verifies a
live Codex pane and restores bookkeeping without image build, container replacement
or native-session restart. Regression coverage includes actual event-routing
behavior with mocked transport rather than marker state alone.

The targeted marker-only Ansible run completed 17 tasks with zero failures. All
eight actual native panes remained alive and had launch markers; all container IDs,
start times and pane PIDs were unchanged. The full 114-test suite and production
Ansible lint passed with zero failures or warnings. No work prompt, model request
or provider credential content was sent to the chat.

## Recognize native Antigravity saved authentication correctly

Implementation: `a990e87`.

The operator completed personal Antigravity authorization, but the reporting
wrapper classified it as failed because its detector expected top-level OAuth
fields. A metadata-only inspection of the native 1.3.1 artifact showed that those
fields are stored under a `token` object. The detector now accepts that actual
structure without inspecting identity values or treating local evidence as proof
of remote model access. Newly persisted valid evidence after a TUI interruption
is saved/unverified; cancellation without new evidence and unrelated errors remain
failed/cancelled. Unchanged saved state receives a separate explanation rather
than an unnecessary re-login instruction. Native interruption remains in diagnostic
metadata while a saved-evidence wrapper outcome exits successfully.

Synthetic fixtures cover native shape, malformed artifacts, cancellation, unchanged
evidence and the complete interrupted-wrapper path. All 118 tests and production
Ansible lint passed. A helper-only original-environment deployment completed 13
tasks with zero failures and the installed detector recognized the saved artifact.
Credential contents and permissions were unchanged; all eight live container
identities and native pane PIDs remained unchanged. No sign-in, inference or
credential clearing was performed, and historical diagnostic records were preserved.

## Complete named projects through archive or destroy

Implementation: `7113c71`.

The user defined two explicit completion operations: both check whether the named
team is running and stop it if necessary; destroy deletes the project and home
assignment config, while archive moves their whole contents into a private
project-archive directory. Retirement checks every named service and container,
handles orphan instances, verifies socket writer quiescence and removes only
stopped project containers. Shared account profiles, images and systemd templates
are retained. Unsafe paths and archive/config collisions fail before shutdown.
Archive moves config into the project before atomic directory rename and rolls
that config placement back if rename fails. Internal links and file modes are
retained. Same-project concurrent lifecycle/edit operations are unsupported and
are explicitly documented. Both actions enter bounded JSON and human diagnostics.

Fifteen behavior regressions and all 133 tests passed; production Ansible lint had
zero failures or warnings. The targeted original-environment deployment completed
33 tasks with zero failures. Installed CLI checks created disposable model-free
projects, verified archive hashes for their full contents and assignment config,
rejected an archive collision, destroyed named fixtures and cleaned them all up.
The existing team had separate logged stop operations before fixture creation;
its unchanged container identities were retained and it was not restarted. No
existing project was archived/destroyed and no model request was performed.

## Include read-only runtime status in project listings

Implementation: `235a6cc`.

The user requested project status beside each listed name. Listing now distinguishes
running, starting, stopping, stopped, failed, partial orphan components and unknown
metadata. It checks target/service metadata and, for inactive services, exact named
containers. Query errors remain unknown with an actionable user-bus/Podman access
hint instead of being mistaken for stopped. Listing neither activates services nor
opens project prompts, credentials or SQLite. Running describes target state, not
individual native-pane health or provider entitlement.

Four added category/error regressions and the installed-router tests passed within
all 137 tests; production Ansible lint had zero failures or warnings. Targeted
Ansible deployment completed 33 tasks with zero failures. The installed list command
returned NAME/STATUS columns and reported the independently stopped existing team
as stopped. All eight existing container identities, states and start times were
unchanged by listing, and existing project/config files were retained.

## Move the editable default into the templates directory

Implementation: `db1c663`.

The user requested that the default new-project prompt live in
`~/templates/assistant-prompts.md` rather than the home directory. Project
creation and default prompt helpers now use that canonical path. Migration uses
Ansible built-in file operations: reject symlinks and conflicting destinations,
copy without overwriting, verify unchanged bytes, then remove the legacy source.
Operator edits and existing project prompts remain independent. The directory is
private and the template writable only by its owner. Focused deployment neither
rebuilds images nor starts or restarts teams.

All 141 tests passed, including actual local Ansible migration, idempotence,
conflict preservation and linked-path rejection. The targeted deployment
completed 28 target tasks with no failures. Installed verification confirmed the
old file was absent, the new file retained its exact previous checksum, and the
existing project prompt was unchanged. A disposable model-free project was
created from the moved template and destroyed successfully; no credentials were
read and no inference was performed. The stopped original team was not started.


## Always date archives and forget retired systemd instances

Implementation: `6368773`.

The user requested a dated directory for every archive, using the operation-start
local time in day/month/two-digit-year/24-hour-hour/minute order. Existing archive
contents are never overwritten or renamed. Both same-minute destinations and an
archive matching the current project name exactly are rejected before shutdown;
the latter recommends changing the project name. Private timestamp metadata
records the operation time. No timestamp suffix is invented to hide a collision.

Retirement disables only named instances, clears their failed state and verifies
that systemd has forgotten all four using nonloading unit-list queries. Files
remain when shutdown, collection or verification fails. Shared templates and
other instances are retained. Config moves roll back on archive failure, while
full-directory moves preserve project files, private role state and internal links.

All 153 tests and production Ansible lint passed. Targeted deployment completed
31 target tasks without failure. Installed disposable checks exercised a failed
unit without authentication or inference, confirmed all four instances unloaded,
verified dated content/config permissions and both collision guards, and cleaned
the fixtures. Shared templates and unrelated container states were unchanged.
The real project was not archived, deleted or started.

## Restore retained archives as dated projects

Implementation: `9cc9321` (0.20.0).

The operator chose copying rather than moving archived projects: the full retained
archive remains unchanged and restoration explicitly reports that fact. The dated
archive directory becomes the restored logical project name. Older plain archives
use their recorded archive time or documented directory-mtime fallback. Structured
configuration and generated role instructions are rebased; user-authored prompts,
artifacts, provider state and conversation history are preserved. Stock broker
project session identity is supplied by the new runtime instance, not a stored
project column requiring conversation rewriting.

Restoration enables only its exact target and leaves services stopped. Preflight
rejects destination/configuration conflicts, existing instances or containers,
unsafe links, malformed metadata and invalid broker databases. SQLite validation
uses a private snapshot to avoid changing retained WAL sidecars. Failed publication
or enablement rolls back the new copy and target enablement. Known stale launch
markers, IPC sockets and archive metadata are excluded only from the restored copy.
Shared name validation permits bounded timestamp suffixes and checks actual Unix
socket byte limits before project operations. Re-archiving a restored project first
requires a new logical name because its original retained archive already has the
exact current name.

Validation: all 162 unit tests passed; production Ansible lint reported zero
failures or warnings across the content processed. Live deployment verification
is reported separately after completion.

## Rename project identity without rewriting user content

Implementation: `75842fb` (0.21.0).

The operator requested a project rename command, including renaming restored
dated project names. `team rename-project OLD NEW` stops and forgets only the
old named runtime, renames the project directory and authoritative home config,
and rebases their structured identity and generated role instructions. Native
account state, the editable prompt, shared artifacts and SQLite conversation
history remain unchanged. The stock broker's session identity is supplied by
the new instance at startup; its stored history needs no blind text replacement.

The new target preserves the old target's persistent/runtime enablement and
stays stopped until explicitly started. Destination path/config/unit/container
conflicts and actual Unix socket limits fail before shutdown. Partial rename,
rendering or target-enable failures roll back retained files and identity where
possible; incomplete rollback is reported instead of overwriting recreated paths.
Same-project lifecycle commands must not run concurrently. Shared images,
provider profiles, systemd templates and other projects remain outside scope.

Validation: 172 tests passed and production Ansible lint reported zero failures
or warnings. The targeted Ansible deployment completed 34 target tasks without
failure. Installed disposable fixtures verified conflict preservation, old/new
config identity, unchanged user content and database bytes, retained native
fixture state, enabled but stopped new target, and human/JSON lifecycle logs.
The fixtures were cleaned; no real project was renamed and no model was invoked.

Rename rollback follow-up: implementation `7ec7121` (0.21.2) also handles
unexpected renderer exceptions and terminal interruption, because transactional
protection must cover these failures as well as ordinary filesystem/systemd
errors. The old directory, exact config and generated instructions are restored
and remain stopped. All 11 focused rename tests pass, including both unexpected
error and interruption regression cases; no Ansible content changed in this fix.


## Restore native cache state safely within the existing layout

Implementations: `d687ceb`, `489aa88`, `22fd447`.

A native Codex archive included regenerated launch/control links, a daemon cache
pointer referring to its container home, and a daemon updater socket. Blanket
link rejection prevented restoration. Relative links to ordinary internal targets
are now preserved. Only Codex arg0/control scopes and its exact updater socket
(after a socket-type check) are omitted from the restored copy. Ordinary files
at the updater pathname are preserved. A verified own-release cache pointer is
rewritten to a relative link. Other absolute/external, dangling, cyclic and
special-file links remain rejected; the complete staging tree is checked before
publication and target enablement. Retained archive data is never rewritten.

Installed testing exposed a rewritten-cache-target variable overwriting the
named systemd target; the follow-up separates those values and verifies exact
enable/disable arguments, including failure rollback and legacy archive names.
The initial isolated full suite passed 177 tests and production Ansible lint;
a strengthened full suite passed 178 tests. Final focused checks passed all
13 restore tests, including all 19 observed link shapes, a real Unix updater
socket and preservation of ordinary files.

Pinned old-layout Ansible deployment succeeded without migration. Disposable
installed acceptance verified link rebasing, narrow cache omissions, unchanged
archive digest, enabled-but-stopped target and unchanged other containers; its
fixtures were cleaned. After the final updater-socket correction, the coordinating
agent completed the operator's actual restore and verified its enabled target
and stopped project state. The archive remains retained; no models were started.

## SELinux gateway listener socket identity

Implementation: `9b1fe2a5e8cdd12b298b4b597e99ff843dfe52a9`.

A native startup hook could not connect even though its private socket inode and
container process had matching MCS mount labels. Sanitized audit metadata showed
a Unix `connectto` denial against the host gateway listener's kernel socket
identity. Linux checks that listener identity separately from the filesystem
inode label; changing file permissions or repeating mount relabeling would not
resolve the cause.

Use the existing policy's permitted container socket identity only when creating
each listener. The host process retains its own identity; the thread-local socket
creation setting is restored immediately before asynchronous or RPC work. Keep
private mount labels, restrictive permissions, and role token checks. Fail closed
if context setup/restoration fails. No custom policy, enforcement exception or
new package is required on the supported host.

An authorized disposable socket probe succeeded from a running container under
enforcing policy and was removed. Eight focused tests cover ordinary IPC exchange,
prior-context restoration, failures, resource cleanup and non-SELinux hosts; the
full 187-test suite and production lint passed. The focused `connector_ipc`
Ansible deployment installed only the routing file and required path facts.
Installed-file checksum matched the implementation; the gateway PID and all eight
running container IDs stayed unchanged.

The installed fix is not yet active in the existing gateway process. Its
container service depends on the gateway, so an unplanned gateway restart could
stop native sessions. Coordinate an explicit `team stop NAME`, followed by
`team start NAME`, with the operator before activating the new listeners.
Successful live hook authentication remains to be verified after activation.

Technical basis: [Linux SELinux Unix stream connection check](https://github.com/torvalds/linux/blob/master/security/selinux/hooks.c)
and the [SELinux socket-context API](https://github.com/SELinuxProject/selinux/blob/main/libselinux/include/selinux/selinux.h).

## Complete shutdown before subsequent start

Implementation: `e119e2dd04bb6b637a90e73879747d2a6ab8798b`.

Stopping only a systemd target could return while its PartOf-dependent services
and containers were still shutting down. An immediate start could then conflict
with remaining stop jobs. Explicitly stop the exact target, broker, gateway and
container service as one blocking request, and verify their states, container
shutdown and listener closure before returning success. Stop preserves target
enablement and project configuration, authentication, prompts and stopped
containers; it does not perform retirement cleanup.

Start checks for pending stop jobs and deactivating services or stopping
containers before submitting its own job. Restart uses completed stop followed
by start. Bounded waits and failed metadata queries report a clear failure rather
than declaring shutdown complete. Status uses the dependent-aware project
summary so an inactive target does not conceal stopping services.

Ten focused regression tests and the full 197-test suite passed, along with
production lint. Disposable real systemd units with delayed stops verified both
completion before return and an immediate start waiting out a queued shutdown.
The same checks passed against the actually installed helper after the focused
`project_control` Ansible deployment. Its installed checksum matched the
implementation, fixture files were removed, and existing running container IDs
stayed unchanged. Only the control file and path facts were installed; no live
team was stopped, no provider was invoked and no installation-layout migration
was deployed.

## Keep Codex updates under deployment control

Implementation: `82ba8a6`.

A Codex startup update prompt attempted a global npm update inside a read-only
container and exited on the resulting filesystem error. Disable the documented
`check_for_update_on_startup` option for centrally managed installations rather
than granting installation writes to running agents. Fresh role configs include
the top-level setting; launch arguments enforce it while preserving existing
operator TOML byte-for-byte. The managed native host wrapper uses the same option
so its pinned installation metadata remains consistent. Version updates continue
through Ansible and image rebuilds. Sandbox, approval, MCP and authentication
settings are unchanged.

Three focused regressions check parsed top-level TOML, preservation of existing
configs and effective container launch arguments with existing security flags.
Native wrapper tests check the update override alongside device authentication
and the credential-file store. The full 200-test suite and production lint passed.
These changes are source-only pending coordinated deployment; no native session
was launched or altered by this work.

A separate provider sign-in/401 issue is not solved by this update setting. Saved
credentials and login-status output describe local state, not acceptance of an
actual provider request. Keep operator login and native first-run onboarding
distinct from tool-approval design, and do not bypass access controls.

Technical basis: [official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Container-owned Codex session lifecycle

Implementation: `c48cab5`.

During authorized startup recovery, normal Codex startup still displayed sign-in
after explicit role authentication, while the installed CLI's supported
`--no-daemon` mode reached the normal prompt after operator hook-trust steps.
The specific upstream shared-server authentication cause remains unproven.

Persist direct mode only for Codex role container launches: a per-role container
and tmux session already own the process lifecycle, so a reused shared background
server is unnecessary in this setup. Retain the native host wrapper's daemon
default. This selects a supported session mode; it does not authenticate users,
trust hooks automatically, bypass sandboxing or change tool approvals.

Launch regression checks include direct mode together with the managed update
setting, workspace-write sandbox and on-request approval policy. Native wrapper
regression checks confirm direct mode does not leak into host launches. All 200
tests and production lint passed. The change remains source-only pending
coordinated deployment; the running builder and other native sessions were not
modified by this implementation.

## Exact Vertex model IDs and first-run onboarding

Documentation: `1df4e5f9b12a7207455c4b27a60857dc752b9329`.

A Gemini work role used `gemini-3.1-pro`, which was not a valid provider model ID.
The published Gemini 3.1 Pro ID is `gemini-3.1-pro-preview`; verification against
the [official Google model reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-1-pro)
confirmed the suffix. The authorized runtime correction changed only model
selection in the local work profile and its role configuration. Authentication
content was not exported or added to Git. The role subsequently accessed its
inbox after operator session-tool approval.

Keep model choice in local provider configuration instead of hard-coding one
model for every installation. The existing Vertex setup accepts an explicit model
ID and work role launch refreshes `.vertex.json` from that selected profile.
Its syntax check is not a remote model-access test. Runtime guide templates now
explain exact IDs and the difference between saved login and usable model access.

Native first-run screens require per-role operator attention: theme, workspace
trust, hook trust and requested session-tool permissions are distinct from
provider authentication and from the future tool-approval design. Document how
to attach and complete those steps before handing the task to the orchestrator;
do not bypass those controls automatically. Source formatting and production
lint passed. No runtime sessions were changed by this documentation work.


## Keep stock MCP behavior compatible with Gemini JSON promotion

Implementation: `67c5ac4` (0.21.19).

Read-only probes of the installed stock shim confirmed inbox and peer-list tools
return text content, with no structuredContent field. Its pinned upstream source
returns arrays serialized as text. The installed Gemini 0.63 compliance transport
parses the first JSON text block and unconditionally assigns its value to
structuredContent; Gemini's MCP schema then rejects arrays and scalar values
because structured content must be an object. The initial suspicion of an invalid
stock structured-content array was therefore disproved: the promotion occurs in
the client. See the [MCP structured-content specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#structured-content),
[stock shim source](https://github.com/Aldenysq/agents-connector/blob/44c195a6ed9e4df608d9fde30e3d8759fc92b900/src/shim/mod.rs)
and [Gemini transport source](https://github.com/google-gemini/gemini-cli/blob/v0.63.0/packages/core/src/tools/mcp-compliance-transport.ts).

A Gemini-only stdio compatibility adapter wraps successful non-object JSON text
in an object structured-content envelope while retaining original text, IDs and
errors. Arrays use items; other scalars use value. Existing structured content,
objects, notifications and tool definitions remain unchanged. Input bytes and
child exit codes are forwarded; output is bounded and failures never echo payloads.
Claude/Codex keep the direct shim. The stock broker and vendor harnesses remain
unmodified; role authentication and tool approval are not changed.

Ansible reproduces the adapter and Gemini config selection. No active native
session was restarted, no model was invoked and no deployment occurred during
this implementation. A future controlled MCP reconnect remains necessary for
installed acceptance. Validation: all 206 local tests passed, including six new
transport regressions; production Ansible lint passed with zero failures/warnings
across 145 files.


## Apply the MCP compatibility fix without replacing active native sessions

Implementations: `e63b2b3` (0.21.21) and `471916d` (0.21.22).

The focused adapter tag now includes all account/path prerequisites; its model-free
regression verifies file-copy actions without service handlers. A guarded opt-in
Ansible repair updates only the selected existing Gemini collaboration role's
recognized stock MCP command. It preserves model selection, authentication settings,
hooks, other MCP servers and existing broker credentials. Unsafe paths, unknown
commands and non-Gemini roles are refused. An owner-only exact backup is retained,
publication is atomic, and an already wrapped command is unchanged. No provider
authentication file is copied or refreshed.

Two pinned old-layout Ansible deployments completed without failure. The selected
configuration deployment ran 24 target tasks. Read-only checks confirmed all eight
container IDs/start times unchanged, a matching digest for all Gemini settings
except the connector command, and unchanged credential-file metadata. Real broker
checks through the installed adapter returned object structuredContent for an empty
inbox and the five-agent roster, with original array text unchanged, isError false
and exit zero. No model call or native input was sent during these checks.

The running Gemini process still uses its prior stock shim children; a controlled
MCP reconnect remains necessary. A real Gemini read/rollcall roundtrip is therefore
not yet verified. This limitation is explicit rather than treating deployment as
proof of end-to-end completion. The source-only installation-layout branch remains
separate and was not deployed. Validation: all 211 local tests passed and production
Ansible lint reported zero failures/warnings across 148 files.

## Preserve Gemini adapter access during focused live updates

Implementation: `4a8fc99`.

The newly copied adapter initially retained a home-file SELinux type, so an already
running container could not read it. The exact adapter file now uses the same
shared container-readable type as the mounted stock executable; no authentication
directory is relabeled and SELinux enforcement remains unchanged.

The focused Ansible deployment succeeded. The preserved native Gemini conversation
was resumed with its existing model, then successfully read messages and the
roster and posted a reply to its original readiness ask. Broker metadata confirmed
the recipient authored that correlated reply. One-time approvals covered only
those exact tools. This proves native protocol compatibility after manual recovery,
not automatic wake-up, which requires separate verification.

## Verify automatic idle ask delivery after native recovery

Relevant implementation: `4a8fc99`; previous acceptance documentation: `8c4e740`.

After receiving all original rollcall replies, the orchestrator sent one bounded
readiness ask to the idle Gemini role. The stock notification path started that
role without manual input. The exact reply call was approved once, SQLite
confirmed author and ask correlation, and the waiting orchestrator received
the response. Thus the existing idle ask wake path works with native approval.
No claim is made for unattended permission handling, busy-queue recovery or
tell-only wake behavior; those were not exercised.

## Add personal Antigravity to the existing team architecture

Implementation: `43ee337`; credential/stop-state correction: `f936ccf`.

The personal Gemini profile uses the official native Antigravity CLI, while its
work counterpart retains Gemini CLI/Vertex. Reusing the existing Gemini container
image with an exact read-only pinned native executable avoids a second image
installation while preserving separate account homes. Native MCP configuration
and lifecycle events are translated to the existing scoped broker and tmux route;
no ACP migration or broad approval policy is introduced. A partial native Stop
remains busy, and context is injected once using a per-role cursor.

Only a missing private native token is seeded. Directory-descriptor traversal
rejects symlinks, exclusive publication prevents replacing refreshed credentials,
and work ADC, API keys and provider settings are not imported. The separate
Ansible verification role runs native help in a networkless rootless container
without credential mounts.

Focused deployment and this native dependency probe passed. All 220 local tests
and production-profile Ansible lint passed. A disposable private role launched
with the saved account but awaits the operator's terms/data-use decision. Thus
actual native model and addressed-wake/reply acceptance are still pending; no
legal consent or data-collection choice is inferred from authentication evidence.
Task-specific model selection remains ON HOLD BUT PRIORITY by explicit decision.

## Role account and model visibility

Implementation: `6d575c8` (0.24.0).

Display the account profile and configured model with each role’s lifecycle state
in `team status NAME`, so operators can distinguish private/work assignments
without inspecting authentication files. Read only allowlisted model configuration
fields; never probe providers or expose unrelated settings. A configured model is
not proof of the actual provider identity, entitlement or an interactive override.
When no explicit model is present, report the unverified harness default rather
than invent a vendor default. Once a role has launched, ignore newer operator
bootstrap defaults that may differ from its isolated running configuration.
Ansible installs the same helper; a dedicated `project_status` tag permits updates
without restarting roles, touching authentication or applying the held directory
layout migration. Validation: 226 unit tests; production Ansible lint passed.

## Color live discussion routing labels

Implementation: `101cc13` (0.25.0).

Use a stable color for each sender and recipient label in terminal watch output,
so operators can follow multiple conversations without coloring message content.
The existing stock broker subscription and its privacy scope remain unchanged.
Keep message IDs and available question correlation identifiers. Unknown roles
and worker broadcasts use neutral colors. Escape/control characters cannot
inject terminal styling through labels or message content. Redirected output,
NO_COLOR and TERM=dumb remain plain. The viewer selects its formatting when
started; operators restart only the viewer, never the running project team, to
load an update. A dedicated Ansible connector_watch tag installs the helper
without profile regeneration, container changes, daemon reloads or model calls.
Validation: 232 unit tests passed; production Ansible lint passed.

## Tail-style communication history

Implementation: `ca641e8` (0.26.0).

Make bare watch show the last 50 communication entries and exit. Explicit -f
follows new entries only; an optional -NUMBER selects preceding history, with
-NUMBER -f combining history and live following. Zero is supported; counts are
bounded at 10000 and duplicate/unknown flags fail explicitly. This intentionally
changes the earlier bare-watch live default to the operator’s requested semantics.
Read only project message rows, which already contain tell, ask and reply events;
avoid joining asks/replies and duplicating their communication. Order by message
ID and retain question/reply correlation. For follow, acknowledge the stock
subscription before a read-only SQLite snapshot, then suppress queued entries
already included through that snapshot’s ID boundary. Preserve terminal colors
and existing privacy boundaries. Upstream slow-viewer stream loss remains an
explicit limitation; no timed polling, model calls or agent restarts were added.
Validation: 239 unit tests passed, including snapshot/follow boundary and parser
coverage; production Ansible lint passed.

## High-level project decision feed

Implementation: `b3242fb` (0.27.0).

Provide workspace/DECISIONS.log for tail-followable, brief timestamped accepted
decisions, agreed direction changes and blockers that require user input. The
orchestrator requests updates only at meaningful milestones, and the summarizer
is the sole intended writer. Proposals cannot be presented as accepted outcomes.
Exclude routine progress, repetitive entries, credentials, raw connector content
and hidden/private-role information. No timer-driven inference or quota fallback.

Fresh projects initialize an empty owner-only file; existing projects preserve
its contents. Managed instruction blocks change only orchestrator/summarizer
generated files while retaining user text outside those blocks and the editable
project prompt unchanged. The separate project_decisions Ansible role reproduces
this migration, refuses redirected workspace/log destinations and does not
restart native sessions. Active conversations require an explicit refresh or
normal subsequent launch; editing files alone does not prove live adoption.
Append-only behavior and writer ownership are role instructions, not a changed
filesystem security boundary; shared-workspace permissions remain unchanged.
Validation: 245 unit tests passed, including content preservation, block
idempotence and unsafe path rejection; production Ansible lint passed.

## Confined Codex native sandbox compatibility

Implementation: `96eec40` (0.28.0).

The native Bubblewrap sandbox could not start inside the original constrained
rootless container on enforcing SELinux. A dedicated Codex-only domain preserves
the relevant standard container permissions, MCS confinement and original outer
controls. Its additional filesystem permissions permit private devpts mounting
and device/tmpfs remounts required by native readonly masking. Those grants apply
to filesystem types, not individual paths or only readonly directions; rootless
namespace and inherited mount locks remain important bounds. The standard
container domain is unchanged. No outside-sandbox tool approval was granted.

Use the already installed certified RHEL system roles module loader instead of
adding development packages. Its module transaction suppresses activation, so an
explicit reload handler and handler flush make the new policy active before
container creation. The separate role intentionally requires the supported
SELinux-enforcing host configuration and existing policy tools.

Actual model-free native sandbox checks passed for ordinary execution and shared
workspace writes. Writes into the writable outer home and protected workspace
metadata directories failed readonly, network creation failed with EPERM, and
outer capabilities remained zero with no-new-privileges, seccomp and MCS active.
A guarded builder-only replacement verified and resumed the exact saved native
conversation; all seven sibling container identities/start times stayed intact.
The original shared checkin completed exactly once and produced a correlated
broker reply after one specific reply approval. No other task was introduced.

Validation: 246 tests passed under Python 3.12, followed by all three focused
container-scope/saved-session guards; production-profile offline ansible-lint
passed with zero findings across 168 files. Ansible policy activation and guarded
builder deployment succeeded. The current conversation returned to its native
prompt. Hidden-role architecture and installation-prefix changes remain separate
source-only work and were not deployed by this fix.


## Flexible watch arguments — 0.28.2

Implementation: `10177d8`. Accept watch options before or after the single project
name, and compact `-NUMBERf`, because users naturally apply familiar tail syntax.
Preserve last-50 snapshot defaults, new-only `-f`, explicit history limits and
zero-history support. Reject duplicate options, unsupported flags and missing or
multiple projects with actionable usage. The existing framed live subscription,
role colors and message privacy remain unchanged. Ansible installs only the CLI
helpers and operator guides; running model sessions need no restart.

Validation: 250 tests passed, including both reported commands and parser failure
cases. Production-profile offline ansible-lint passed across 169 files using the
already available certified collection path.

## Canonical installation root without migrating the running environment

Implementation: `2cf98a7` (0.22.0).

A single `PREFIX/ac-agents` root makes future fresh installations easier to locate,
reproduce and inspect. The prefix is a parent directory and defaults to the destination
runtime user's real home. Tools live in `bin`, connector code in `agent-connector`,
account profiles in `model-environments`, and environment/template configuration in
`conf`. Each project's singular `project.NAME.config` lives beside its editable prompt.
Central path helpers drive runtime, authentication, lifecycle and Ansible references
so profile discovery and authentication clearing remain within the correct scope.

Systemd user units and Podman engine storage retain their standard real-home locations;
units explicitly reference the installation root. Existing parent directory ownership
is preserved. Fresh-install preflight refuses legacy layouts, unsafe ancestors and
conflicting same-user service namespaces rather than creating an overlapping environment.
Native profile credential isolation and validated archive-link/cache handling remain
unchanged. Deeper paths are checked against actual Unix socket byte limits.

The user explicitly prohibited deployment to the current environment. This change is
therefore source-only: no target deployment, credential migration or model call ran.
Controlled migration prerequisites are documented separately; an executable migration
procedure and fresh installed acceptance remain future work, not verified deliverables.

Validation: Python 3.12 executed all 191 local tests without skips; production Ansible
lint reported zero failures and warnings across 149 files. Regression tests cover
project-local configuration and lifecycle rebasing, profile-auth copy scope, actual
socket limits, destination-prefix forwarding and rendered systemd path quoting.


## Clarify project ownership and defer CLI renaming

The installation-layout implementation `2cf98a7` retains the existing command
behavior. Operator documentation now calls its named unit `PROJECT`: one project
owns one team, and roles identify participants within it. Current command parameters
are documented to make this distinction explicit. A proposed shorter verb scheme
is tracked in TODO only; no command/subcommand renaming is implemented here.
The live broker-hook SELinux connection blocker remains separately under diagnosis,
without a claim that the source-only layout or these documentation changes fix it.


## Generate scoped permissions and communicate blocked approvals

Proposal documentation: `f6f900b` (0.22.4).

The next permission-management design separates workspace trust and onboarding
from tool approval. Generate operator-controlled allow/ask/deny policies per
project and role before launch, permit only authorized broker operations within
project scope, and preserve private/corporate and hidden-observer boundaries.
A deterministic private notification relay should correlate sanitized approval
metadata in SQLite without requiring a blocked model turn. Process launch must
be distinguished from readiness and waiting for approval. The initial operator
path remains attaching the exact tmux role; no blind Enter or timeout may approve
an action. Supported native hooks/protocols and unimplemented transport gaps
are documented; a unified approval CLI is not claimed.

This is source-only documentation. No policy generator, relay, model call, trust
acceptance or deployment ran. The user subsequently put implementation on hold
while completing interactive native introductions. Documentation diff checks
passed; new runtime behavior was neither implemented nor tested.
## Private passive summarizer and observer — source only

Implementation: `6f6141a` (0.29.0), isolated feature branch; no deployment.

The user changed the role design: only orchestrator, builder, investigator and
challenger participate in team activity. Summarizer and observer read raw
communication privately, never answer participants or ask the orchestrator for
management, and never send feedback into the team. This supersedes the earlier
observer-to-orchestrator stop recommendation and orchestrator-requested summary
workflow. Private/corporate connectors retain their separate existing scope.

Remove reader registration, worker messaging targets, shared artifact mounts and
mentions in generated participant rosters. A deterministic host listener uses the
existing broker stream and message-only SQLite recovery, with short event burst
coalescing and queued batches while readers are busy. No timed model polling.
Readers receive private read-only raw context and write individual private drafts;
private lifecycle callbacks cannot perform broker operations. The host appends
changed drafts to separate operator-only SUMMARY/ASSESSMENT outputs. Preserve
existing private mount labels on newly written raw inputs. Initial reader support
uses Claude profiles, with unsupported assignments rejected explicitly rather
than silently changing provider. Native approval/onboarding controls remain.

The earlier DECISIONS.log native append verification failed: ownership/mode were
correct but the Ansible-created file had user_home_t rather than its shared
workspace's container_file_t label. The narrow label correction was preserved
as local WIP and not deployed after the user's stop/change instruction. The log
remains empty; new project creation no longer enables this superseded workflow.

Isolation does not erase old conversation knowledge or conceal framework source
from a worker explicitly tasked to inspect it. Operator-owned instructions and
history require a separately reviewed stopped migration. Source tests cannot
prove native event hooks, entitlement, permission handling or restart behavior
on a live deployment. Deployment remains explicitly held. Validation: 249 unit
tests passed, including raw-feed privacy, worker registration, role/mount
isolation, callback boundaries, busy-event coalescing and report deduplication;
production Ansible lint passed. Shared installation-prefix checkout unchanged.

Also document the latest collaboration rule: prefer automatic subagent completion
notifications instead of fixed-interval polling; status checks need a blocker,
missing notification or task-specific reason. External jobs still need verified
outcomes. This aligns with the separately documented source-layout session rule.

## Fresh integrated installation and private readers

Implementation `a3d4f07` combines the approved prefix layout with the latest runtime fixes. Implementation `eded349` integrates private event-driven readers, the operator-only SUMMARY.md, and the dedicated Codex sandbox role in complete and portable deployment. This provides one current fresh-install configuration while preserving existing environments until their separate migration is approved. The authentication vault, model selection and general permission automation remain on hold. Unit checks cover the merged runtime paths and private-reader boundaries; deployed native acceptance remains a separate verification.

Implementation `7656f7d` aligns native provider verification and disposable deployment checks with the prefix layout and private-reader isolation. This avoids deploying a passing unit-tested source tree with an obsolete shared-observer acceptance check. The existing development VM is not changed by these integrated fresh-install commits.

## Exact disposable-clone retirement and fresh replacement

The encrypted retirement definition now binds its selected name to an explicit
authorized name; other clones, the original environment and source image remain
protected. A fresh replacement clears the previous recovery address so provisioning
discovers only the new guest. Implementation: `4a67ef7`. Four focused retirement
safety tests passed.
## Selective bootstrap authentication replication

Implementation: `1c4dcd4`.

The operator authorized replicating enabled bootstrap model authentication from an
existing environment to a fresh deployment, followed by separately bounded model
checks. A dedicated Ansible role/playbook uses protected delegated capture and
module stdin, with no persistent credential bundle. It copies supported native
credential documents and only the explicitly allowlisted provider/onboarding
material required for each context. Existing target credentials remain untouched;
project-role refresh streams, workspaces, sessions, SSH and broker secrets are
excluded. Work and private profiles remain independent.

No-follow directory traversal, private permissions, active bootstrap writer
guards, complete manifest preflight and atomic missing-only publication protect
source and destination state. Each profile rolls back only its own new files on
publication failure. The target's secret-free metadata report lists restored,
skipped and missing profiles and accepted vault material paths/field names. A
later external vault stage remains separate and has not been implemented. No
legal consent, paid fallback, native restart or model inference occurs in this
transfer playbook.

Validation passed: the full 263-test suite, an additional focused writer-scope
regression (14 transfer tests total), and production Ansible lint with zero
findings across 176 files. These were synthetic/local checks, not proof of live
provider entitlement. Actual transfer and bounded access checks remain pending
the successful fresh AAP deployment and are not claimed as completed.

## Preserve native JSON across Ansible transport

Fix: `ffd661e`.

A disposable local Ansible acceptance test found that native templating could
convert captured JSON text into a mapping before passing command stdin. Explicit
JSON deserialization/serialization keeps the restore helper's supported transport
format and avoids relying on implicit conversion. Errors report only fixed helper
diagnostic codes; neither native payloads nor raw exception details are exposed.

Actual model-free Ansible role execution passed metadata-only preflight (six
profiles present), missing-only restore (six restored) and an idempotent rerun
(six existing profiles skipped), with temporary helper directories removed. All
15 focused transfer tests and production lint for the role/playbook passed. These
checks used synthetic credentials and did not copy or read real authentication.
## Preserve source-review findings for later assessment

Implementation `5eb9f18` adds thirteen review-only backlog items from the team review of snapshot `12ac41f` (0.28.1). The purpose is to preserve evidence and open questions without approving fixes or carrying rejected claims into the active defect list. Current-source reassessment and live verification are required because the installation and private-reader design have changed since that snapshot. Only generic findings were retained; raw conversation and environment information were excluded. Validation: documentation diff check passed; no runtime or system change was made.

## Consolidate parallel development for version 1.0.0

The release integrates `511c76c` (fresh definition and guarded retirement), `288abfb` (selective authentication transfer, including its synthetic Ansible transport validation), and `43f476b` (review-only backlog) with integrated source `7b84c4d`. Branch release-note collisions were combined without rewriting their original commit histories. The final release snapshot is 1.0.0; these integration/documentation commits belong to that same consolidation rather than claiming separate released versions. Subsequent fixes resume patch increments. Existing environments remain unchanged by source publication. Provider auth material is excluded from Git; encrypted deployment definitions are permitted. Live AAP, auth and team acceptance remain separate checks after publication.

Release implementation `160385d` reconciles the 1.0.0 source scope and incremental branch history. Documentation `09515b3` updates the active acceptance plan. The active fresh-install/transfer/native-team acceptance plan replaces obsolete fresh-test holds, while existing environment migration, external auth vault and broad permission automation remain separately constrained.

## Match Mistral's native Vibe installation metadata

Fix: `54434f5`.

Mistral work/private directories retain their public profile names, while the
installed vendor harness identifies its flavour as `vibe`. The bootstrap transfer
validator now checks this actual installed metadata instead of rejecting an
otherwise supported source. The fixtures use the same native flavour. All 15
focused tests, including actual local Ansible preflight, six-profile restore and
missing-only rerun, passed again using synthetic credentials only.

Release source also includes Vibe metadata compatibility implementation `9a7680c`: native Mistral installations identify their harness flavour as vibe. Synthetic protected Ansible transfer checks verify capture, missing-only restore and rerun preservation without reading live credentials.

The final 1.0.0 source validation passed 283 unit/fixture tests and offline production Ansible lint across 183 files with zero findings, using the pinned certified collection. The test suite includes synthetic protected Ansible authentication preflight/restore/rerun; no live auth data or VM was changed by these source checks. Native AAP/team acceptance follows the published source release.
