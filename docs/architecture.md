# Design agreements awaiting implementation

Latest source-only decision supersedes the earlier observer/summarizer participation
and feedback sections below. The team has four broker identities: orchestrator,
builder, investigator and challenger. Summarizer and observer are passive raw-feed
readers with no worker MCP access, no shared workspace, no answers and no feedback
to participants. A deterministic private host event listener drives bounded native
analysis; changed drafts append to operator-only SUMMARY.md and ASSESSMENT.log.
The current environment has not received this architecture. Earlier sections are
historical design context, not permission to deploy or claim live acceptance.

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

## Persistent native sessions and event delivery requirement

Each native harness session must run in tmux inside its continuously running
rootless Podman container so the operator can attach. Keep instance state and
authentication isolated; this requirement does not authorize sharing host tmux
sockets, provider credentials, or broader host mounts. The initial container
foundation does not implement this lifecycle; the selected three-harness connector
setup below now provides persistent tmux availability.

Prefer an existing inter-agent communication and listener implementation. Do not
implement timed inbox polling. Wake means delivering an addressed event to the
existing running harness, preferably through a native inbound interface that can
serve multiple harnesses. Outbound MCP client tool calls are not proof of inbound
idle-session support. Verify actual native capabilities and compatibility with all
four harnesses before choosing a mechanism. A tmux wake, if selected, may submit
only a fixed notification; authenticated MCP carries the message content.

The subsequent setup decision selects Agents Connector and fixed tmux routing
for three harnesses. Generic native inbound control remains a research question;
no polling timer is deployed.

## Selected first setup: Agents Connector with isolated native sessions

The user selected Agents Connector for an initial usable setup with native Claude
Code, Codex and Gemini, omitting Vibe from assigned team roles. The dedicated account, home-local binary,
prompts, SQLite broker and enabled user services are reproduced by a separate role
called from the connector playbook. Existing images are extended with tmux rather
than replacing native harnesses. Idle tmux shells become native sessions only when
the operator completes authentication and explicitly launches them.

The stock launcher assumes shared host paths and tmux. A small lifecycle wrapper
instead launches tmux inside each isolated container. A restricted host tmux adapter
routes the stock broker's fixed wake notification to that container; message bodies
remain in MCP/hook delivery. No polling timer or new orchestration platform is built.
Stock broker administrative IPC is kept private, with a per-instance filtered socket
for native MCP shims and hooks. Observer and connector profiles now have separate available containers but remain
unregistered in the worker broker. The observer uses a manual read-only snapshot
and private report bridge; external connector tools are still unconfigured. Provider accounts, native hook approval and live model
session behavior require operator setup and later verification.

## Group lifecycle through a user target

The user selected `assistant-connector.target` as the single start/stop/restart
control. It requires the three existing services; service ordering starts broker,
gateway and containers in that order. `PartOf` propagates target stop/restart,
while only the target is enabled for user-manager startup. No synthetic master
service is introduced. The availability service explicitly stops all eight named
containers; persistent homes, provider state and SQLite survive. Group start
restores idle tmux shells and does not automatically launch or resume model
sessions. Routing-service refresh remains independent of container lifetime.

## Native login directories, editable prompts and human controls

The user requested actual home-local native installations in claude-work,
claude-priv, gemini, codex and mistral, with all configuration/cache/state/temp
inside each directory. A separate native_auth role reuses pinned native artifacts,
uses a compatible portable Python for Vibe, and provides simple ./login commands.
Work/private Claude account boundaries remain separate. Explicit role launch seeds
only missing credentials and minimal account metadata, preserving independent
role hooks/configuration and existing credential refresh state. Authentication and
provider refresh remain unverified until the operator signs in.

A single editable assistant-prompts.md outside those directories supplies all
eight role sections. It is seeded without overwriting user edits and never mounted
whole into containers. Apply/launch renders only each role's permitted context.
All eight containers are available, while only the five collaboration roles join
the worker broker. Observer evaluation/report context remains private.

The home-local team utility supports native launch/attachment, live stock-broker
subscription, prompt application, scoped observer snapshot and private report
delivery. Observer source context is mounted read-only; reports reach only the
orchestrator's private workspace. Connector profiles disable native tools and
have no external tools/account credentials. Continuous orchestration/evaluation
and tool-audit integrations remain future work. The home README.md documents every existing
operator command. The project framework described below supersedes the earlier
single-project limitation.

## Project-scoped runtime framework

Each named project lives under the runtime home projects directory with its own
stock-schema SQLite database, editable assistant-prompt.md containing goal and
eight role sections, native homes, workspaces and filtered IPC. The installed
CLI/images and provider login directories are reused; project state is not shared.
Five collaboration identities alone join each broker. Hidden observer reporting
and private/corporate connector contexts remain outside worker-readable IPC.

Creation invokes the stock broker for schema migration and registration, without
containers or models. Start first checks all required saved subscription/OAuth
credential formats and then activates a systemd instance target with ordered
broker, gateway and eight native tmux harnesses. Native approvals remain enabled.
Stop and restart are project-scoped and preserve disk state; automatic restoration
of a previous conversation is not claimed. The original default runtime is retired; operator commands require a project.
Projects are not boot-enabled automatically. Resource scaling for multiple busy
teams and continuous orchestration/evaluation remain unverified or unimplemented.

## Retire the redundant default runtime

A separate retirement role stops/disables/removes only the original non-instance
units and exact original container definitions. Their bind-mounted profile homes,
credentials, editable prompt defaults and SQLite data are preserved. Project
instance templates, databases and containers are not targeted. The foundation
role no longer creates or starts original services/containers on rerun.
Operator commands require a project name and there is no all-projects master.

## Shared project artifacts with separate role context

The project-root workspace is a shared artifact directory mounted at
/workspace/shared. Seven working roles get read/write access and the observer
gets read-only access. Each role retains private /workspace instructions and its
own native home; neither provider credentials nor full prompt/account contexts
are mounted into shared artifacts. Connector publication remains explicitly
authorized and their general tools remain disabled. Codex uses workspace-write
with on-request approval. File ownership is coordinated through the orchestrator.

Ansible adds missing shared directories without touching existing contents.
Running containers are never replaced for migration; the normal project stop/start
rebuilds only stopped definitions whose mounts differ, preserving disk state.
