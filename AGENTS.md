# Project working rules

Use Ansible for deployment and configuration where its modules provide clear,
reliable and idempotent behavior. Prefer an obviously suitable certified collection
when available; do not force one where it would complicate the architecture.
Keep runtime CLI, authentication-flow and broker routing logic as application code
installed by Ansible. Review deployment helpers after blocking fixes, rather than
rewriting unrelated working code during an active deployment.

Direct SSH access with sudo to the project VM is authorized for project work.
Keep deployment access credentials and environment-specific values in Ansible Vault.
Model authentication must remain outside this application/code repository.
Active encrypted deployment and recovery configurations also belong in the
private companion repository under `vaults/configuration`, not this code tree.
Load them through the shared external configuration role; refresh AAP's encrypted
file snapshots after committed changes and retain separate Vault credentials.
The operator explicitly permits Ansible Vault-encrypted authentication snapshots
in the private companion repository assistant-team-secrets only. Never commit
plaintext credentials, decrypted output or the Vault password file anywhere.
Do not broaden this authorization to unrelated hosts or security-control bypasses.

Name encrypted configuration files `NAME_vault.yml`, including files in the
private companion repository. Update current code and documentation references
when renaming. A filename change does not change the Vault ID, encryption key,
credential boundaries or ciphertext contents.

All read-only APME scans are authorized without repeated approval, provided they
leave systems and project code unchanged. Preserve existing installation,
credential-protection, and security-control rules. Assess findings for relevance
to this project's security, compliance, stability, and supported Ansible version;
implement justified fixes with validation. Do not blindly apply automatic upstream
remediation or use external AI fallback.

For every lasting design or configuration change:

- Keep README.md and README.TLDR.md (including the deployed home operator guides) current; update the design decision history to describe the final state
  and the reason for the decision.
- Implement the resulting configuration in separate Ansible roles called by
  the project playbook so it can be reproduced on a fresh deployment.
- Commit and push the implementation and README together to the private repository.
  Record its commit ID in the decision history in a following documentation commit
  when the ID was not known beforehand.

Document final design decisions and resulting behavior. Interim steps, temporary
experiments, retries, and routine testing details do not need individual design
history entries. Include validation results when they help assess the final change.
Do not leave a lasting manually applied configuration change without automation.

## Background implementation

Keep the main conversation focused on building and design. After a design decision
is settled, delegate its implementation to background subagents as appropriate.
Subagents handle configuration changes, separate Ansible roles, documentation,
meaningful validation, commits, and pushes. Run tasks in parallel when they do not
overlap or endanger one another. Coordinate file ownership, and serialize shared
Git mutations and conflicting VM configuration changes; these constraints do not
require unrelated investigation or implementation to wait.

Distinguish "design agreed, implementation pending" from "implemented and verified."
Continue independent design discussion while the subagent works; dependent work
must wait for the implementation result. Report completion briefly, and bring
blockers requiring a significant decision or approval back to the main conversation.
Background execution does not waive validation, outcome monitoring, security rules,
or required approvals.

Use automatic subagent completion notifications rather than fixed-interval polling.
Every ten minutes during active work, check unfinished subagents for stalled,
blocked or deferred work and a need to resume. Preserve explicit holds and never
restart completed work. Share meaningful results and blockers promptly; user
status requests and task-specific needs can warrant additional checks.
External jobs without notifications still require appropriately spaced checks and
verified outcomes; elapsed waiting time is not evidence of completion.

## Release versions

Use "Document" rather than "Record" in documentation-only commit subjects and
release-note summaries. Existing Git commit subjects are historical and must not
be rewritten just to change this wording.

After the verified initial 0.0.1 release, every commit increments VERSION. Feature
commits increment the minor version and reset patch; all other commits, including
documentation/history commits, increment patch. Use `python3 src/bump-version.py`
or add `--feature`, and deploy matching version/build metadata. Keep README.md,
README.TLDR.md and both home operator guides current with lasting changes.
