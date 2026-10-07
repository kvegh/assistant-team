# Design agreements awaiting implementation

The container foundation supplies native harnesses and isolated instances. The
following agreements guide the next application design; the central service is
not implemented yet.

## Central discussions and persistence

Use SQLite for central persistence of discussions, task handoffs, and verified
outcomes. Define company/private access boundaries explicitly and enforce them
in the service. A worker's knowledge of collaboration roles does not grant
access to another worker's context, workspace, credentials, or restricted threads.

A high-level summarizer and an orchestrator have separate responsibilities.
The summarizer produces useful overview material; the orchestrator coordinates
work and handoffs. Provider-native agent loops remain in their respective
harnesses. Cross-agent communication and database schemas still need implementation
and validation through reproducible roles.

## Separate observation and evaluation

Start with one observer covering two responsibilities and producing separate
reports: output evaluation and design evaluation. Give it access to permitted
discussions and verified outcomes through a separate service boundary. Its role,
instructions, and reports stay out of working-agent-readable communication.
The worker-visible roster describes collaboration roles only.

Output evaluation considers correctness, usefulness, judgment, and efficiency,
and recommends provider-role fit. Recommendations require an operator decision;
they do not automatically reassign work or become routine approval gates.

Design evaluation recommends only significant improvements supported by evidence
of productivity, security, simplicity, or efficiency benefits. Include the
expected benefit and the complexity or cost of the proposal. Leaving the design
unchanged is a valid outcome. Recommendations do not trigger automatic changes.

## Provider access and usage

Provider authentication is isolated per instance and must be supplied explicitly.
Do not reuse the development session's credentials. Under the user's chosen
access arrangements, exhausted subscription allowances pause the relevant work;
there is no automatic switch to a paid API. Availability, allowance detection,
usage reporting, and the concrete pause/resume mechanism require later design
and implementation. Container builds and smoke tests perform no model requests.

## Availability, event handling, and bounded discussions

Keep agent containers and local listener processes available. Idle local listening
does not invoke a model. Addressed, relevant events may invoke a native harness
or resume its saved session; verify each harness's supported interaction and
resume mechanism before implementation. A continuously running interactive CLI
must not be assumed to accept externally injected messages.

Use bounded discussion rounds and explicit completion signals to avoid response
loops. Observation can run at selected checkpoints, timers, or events instead of
making a model call for every message.

The observer also privately identifies discussions becoming repetitive,
off-topic, speculative, or unproductive, and sends the orchestrator a concise
stop recommendation with its reason. The orchestrator decides whether to close
or pause the thread, cancels queued discussion responses, and tells workers to
stop that discussion. Containers remain available and unrelated implementation
work continues. The instruction need not disclose the observer, and its stated
reason must be truthful.

Record the unfinished question or disagreement. Reopening the discussion requires
an explicit orchestrator or user decision. These lifecycle and communication
behaviors remain design agreements awaiting implementation; current container
smoke tests launch short-lived offline processes only.

## Separate private and corporate connectors

Use two distinct Claude Code connector roles: Private Connector and Corporate
Connector. Give each separate credentials, context, and scoped plugin tools.
Disable general shell and unrelated tools for these connector roles. Start with
reads; add writes with explicit approval later. The tool layer enforces access
and approval independently of model claims. Connector provisioning and provider
integration are not implemented by the container foundation.

The orchestrator distinguishes simple routine work, direct implementation of an
agreed design, and debate followed by implementation when significant ambiguity,
architecture choices, or tradeoffs require discussion.

## Connector execution audit

Every connector action must generate SQLite audit metadata from actual tool
execution. Link it to task, thread, and correlation IDs and record the connector's
account boundary, a typed action such as `mail.read` or `task.complete`, timestamps,
status, error code, item count, and the applicable write-approval ID. Record both
the attempt and result, including failures and retries sharing a logical operation
ID. Model self-reports are not the execution audit source.

Do not capture email bodies, complete resource content, or secrets by default.
Sensitive resource identifiers belong in protected SQLite runtime storage and
must not appear in plaintext Git files. Completing a task means marking it
completed, preserving its history. Audit storage, connector adapters, and their
permission enforcement require later implementation and validation.

## Persistent native sessions and event delivery: implementation TODO

Each native harness session must run in tmux inside its continuously running
rootless Podman container so the operator can attach. Keep instance state and
authentication isolated; this requirement does not authorize sharing host tmux
sockets, provider credentials, or broader host mounts. The current container
foundation has not implemented this session lifecycle.

Prefer an existing inter-agent communication and listener implementation. Do not
implement timed inbox polling. Wake means delivering an addressed event to the
existing running harness, preferably through a native inbound interface that can
serve multiple harnesses. Outbound MCP client tool calls are not proof of inbound
idle-session support. Verify actual native capabilities and compatibility with all
four harnesses before choosing a mechanism. A tmux wake, if selected, may submit
only a fixed notification; authenticated MCP carries the message content.

Transport evaluation is pending. No candidate is selected, and no persistent tmux
service, new communication service, or polling timer is deployed by this decision.
