# Project working rules

Direct SSH access with sudo to the project VM is authorized for project work.
Keep access credentials and environment-specific values in Ansible Vault.
Do not broaden this authorization to unrelated hosts or security-control bypasses.

For every lasting design or configuration change:

- Update the README and the design decision history to describe the final state
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
is settled, delegate its implementation to one reusable background subagent.
The subagent handles configuration changes, separate Ansible roles, documentation,
meaningful validation, commits, and pushes. Process handoffs sequentially to avoid
conflicting Git changes or concurrent VM configuration changes.

Distinguish "design agreed, implementation pending" from "implemented and verified."
Continue independent design discussion while the subagent works; dependent work
must wait for the implementation result. Report completion briefly, and bring
blockers requiring a significant decision or approval back to the main conversation.
Background execution does not waive validation, outcome monitoring, security rules,
or required approvals.
