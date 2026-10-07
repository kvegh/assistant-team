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
