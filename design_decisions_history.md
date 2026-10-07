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
