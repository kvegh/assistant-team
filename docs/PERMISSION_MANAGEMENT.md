# Scoped permission management proposal

Status: design only. No unified policy generator, approval relay or heterogeneous
approval command is implemented by this document. Current teams retain native
interactive approvals. This source-only proposal must not be deployed to the
running environment as part of the installation-layout work.

## Generate policy before launch

Define one operator-controlled policy per project and role, with `allow`, `ask`
and `deny` rules, then translate it into the chosen harness's supported native
configuration before launching that role. Policies describe permitted workspace
paths, tools, connector operations and account context. Validate both the common
policy and generated native configuration; refuse launch if a restriction cannot
be represented or enforced. Default unclassified consequential actions to `ask`;
deny forbidden scopes explicitly. Keep the effective policy revision with runtime
metadata so each permission outcome can be correlated with its generating policy.

Policies and their enforcement code must be host-controlled and unavailable for
agent modification. Read-only mounts, filesystem boundaries and restricted tools
must enforce that separation; prompt instructions alone are insufficient. Recheck
permissions after account/role assignment changes. Private and corporate connector
roles must be denied access outside their explicitly authorized account context.
Workspace trust, authentication, first-run acknowledgements and tool permissions
are separate decisions. A trust choice must never silently enable all tool calls.

Always allow the specifically authorized, authenticated project-broker operations
needed to read addressed messages, send messages/questions/replies, report state
and emit approved metadata. Restrict operations to the current project and role,
including permitted recipients. This exception does not grant arbitrary MCP tools,
shell execution, other-project inboxes, provider credential access or connector
actions. The observer's private channel and exclusion from the worker roster remain
intact; no worker-readable permission event may disclose its role or reports.

## Communicate blocked requests without another model turn

A native hook or structured transport emits an event when approval is required.
A deterministic relay records sanitized metadata in the project's SQLite history
and notifies the operator privately, without asking the blocked model to explain
its own blockage. The event contains a correlation ID, project, role, native session
and request identifiers, action category, policy revision, time and outcome.
Do not persist full commands, tool arguments, prompts, credential-bearing URLs or
provider content by default. The operator can inspect details in the exact native
session or a protected, explicitly requested view. Redact before recording, not
only when exporting diagnostics; retain private permissions and bounded logs.

A private notification must distinguish `waiting_approval` from `busy` and
`ready`. `launched` means only that a process was started; it does not prove that
onboarding finished, tools are usable or the model is conversationally ready.
Use separate states for starting/onboarding, ready, busy, waiting for approval,
stopped and failed. Where no reliable native readiness signal exists, report
unknown/onboarding rather than declaring readiness from a live pane alone.

The initial tmux fallback is: notify the operator with the project and exact role,
then let them use the existing `team attach PROJECT ROLE` command and answer the
visible native question. Never send blind Enter, synthetic approval text or a
broker wake notice into an approval/onboarding screen. Queue addressed events while
the role cannot consume them safely. An acknowledgement timeout, missing hook or
unavailable operator never grants approval; remain blocked or fail closed according
to the native transport. Approval/denial/cancellation updates share the original
correlation ID. A future shared approve/reject interface needs explicit transport
support, request identity checks and replay protection; it is not available now.

## Native capability boundaries

| Harness | Evidence and proposed integration | Current limitation |
| --- | --- | --- |
| Claude Code work/priv | `PermissionRequest` hooks expose tool approval requests; `Notification` with `permission_prompt` covers permission alerts, including sandbox network requests in the installed version. Prefer the immediate request hook for tool approvals and notifications for supplementary coverage. | These supported events are not yet wired to this proposal's private relay. Notification timing can be delayed; it is not a readiness proof. |
| Codex | Official app-server protocol has structured approval requests suitable for correlation and explicit answers. | Our current integration uses tmux, not an implemented app-server approval transport. Do not promise remote approval through the existing connector. |
| Gemini | ACP defines `session/request_permission`, with explicit selected/cancelled responses and scoped options. | Verify the installed Gemini adapter's actual ACP behavior before choosing it. Headless `ask_user` denial is not an automatic pause/resume guarantee. |
| Mistral Vibe | Installed 2.26 supports an explicit `--agent` selection and separate `--trust`; choose an explicit policy agent and scoped tool settings. | Current online documentation and installed help differ on programmatic defaults. Never rely on implicit approval defaults; the Mistral team adapter is still unimplemented. |
| Antigravity | Retain native trust/approval controls until a supported protocol is verified. | No team adapter or unified approval transport is implemented. Broad permission-skipping flags are not an approval notification solution. |

Claude hook capabilities and notification timing are documented in the
[official hook reference](https://code.claude.com/docs/en/hooks#permissionrequest)
and [notification section](https://code.claude.com/docs/en/hooks#notification).
Codex's supported transport is described in the
[official app-server documentation](https://developers.openai.com/codex/app-server).
ACP's permission contract is in the
[protocol tool-call specification](https://agentclientprotocol.com/protocol/v1/tool-calls#requesting-permission);
that contract alone does not verify our Gemini runtime integration.
Vibe's scoped tool permissions and temporary trust are described in
[official safety documentation](https://docs.mistral.ai/vibe/code/safety-approvals-permissions),
with current CLI selection semantics in its
[official source](https://github.com/mistralai/mistral-vibe/blob/main/vibe/cli/entrypoint.py).

Correction to earlier research: Claude's global exact-workspace
`projects["<path>"].hasTrustDialogAccepted` is explicitly documented in the
[official workspace-trust guidance](https://code.claude.com/docs/en/permissions#what-runs-before-you-trust-a-folder).
It is not merely an undocumented internal field. Conversely, finding
`hasCompletedOnboarding` inside the installed binary does not make it a supported
public onboarding configuration contract. Trust must be approved for the intended
workspace before generating that persisted entry.

## Implementation acceptance

Implement the startup/communication blocker first: generated scoped policy,
meaningful readiness states and private blocked-request notification. Verify with
disposable, model-free fixtures: allow/ask/deny translation, prohibited scope refusal,
policy immutability, no secret leakage, observer-channel separation, request
correlation, queued wake behavior and timeout refusal. Keep live model/provider
checks separate and explicitly authorized. Choosing structured transports across
all vendors is a later architecture decision; this proposal preserves attachable
tmux as the safe initial operator path.
