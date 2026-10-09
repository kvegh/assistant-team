# Release notes

## 0.22.10

Document notification-driven background monitoring; remove the fixed 20-second
subagent polling rule while retaining outcome verification for external jobs.

## 0.22.9

Document the model-selection hold commit and the user's retained priority.

## 0.22.8

Document that task-specific model selection for cost and quality is on hold,
while retaining its priority when work resumes.

## 0.22.7

Document the communication-review commit and the decision to continue current
tmux development while alternatives await evaluation and an explicit decision.

## 0.22.6

Document the pending communication architecture review, comparison and recommendation.
Continue the current tmux route; ACP/acpx migration remains undecided and no runtime
configuration changes are made by this documentation update.

## 0.22.5

Document the permission proposal commit and its implementation hold while native
introductions are completed. Runtime approvals and the current environment stay
unchanged.

## 0.22.4

Document scoped permission policy generation, meaningful native readiness states
and private approval notifications as the next startup/communication work. Clarify
supported harness capabilities and current transport gaps; no permission automation,
trust acceptance, model invocation or deployment is implemented by this proposal.

## 0.22.3

Document the model-authentication replication plan, exact credential-file manifest
and existing implementation references. Mark vault implementation on hold; no
credentials are exported and no runtime configuration changes.

## 0.22.2

Document that each project owns one team and its roles are participants; clarify
current project/role/archive parameters in source and generated operator guides.
Add a proposed verb-only CLI transition and the unresolved live broker-hook blocker
to TODO. Existing commands and the current environment remain unchanged.

## 0.22.1

Document the canonical installation-layout implementation and its local verification.
Fresh-install support is source-only; existing-environment deployment and executable
controlled migration remain pending explicit work.

## 0.22.0

Add a canonical `PREFIX/ac-agents` installation root with destination-home default,
scoped model environments, project-local configuration, installation-local tools
and central path helpers. Rebase lifecycle and auth helpers, user units and
Ansible roles; refuse legacy or conflicting installations before creating overlap.
Keep standard systemd and Podman storage locations. Document controlled migration
prerequisites; this source-only release is not deployed to the existing environment.

Validation: all 191 local tests passed; production Ansible lint reported zero
failures or warnings. No model calls, credential migration or target deployment ran.

## 0.21.8

Document verified old-layout restore fixes and successful restoration of the
operator project. Its target is enabled but stopped; the archive remains retained.
No installation-layout migration or automatic model startup was performed.

## 0.21.7

Omit the exact Codex daemon updater socket from restored copies after checking
its socket type. Preserve ordinary files and other native state, and exercise
all observed generated links plus a real Unix socket in restore regressions.

## 0.21.6

Keep the named systemd target separate from the rewritten Codex cache-link target
and validate the exact enablement command in restore tests.

## 0.21.5

Restore safe relative internal links while keeping external/dangling links blocked.
Omit only regenerated Codex arg0/control state from the restored copy and rebase
its verified own-release daemon pointer. Validate staging before publishing;
retained archives, credentials and the existing installation layout remain intact.

## 0.21.4

Document the deferred installation-layout cleanup, including configurable prefix,
project-local singular configuration files, scoped model environments and the
default prompt template. Runtime paths remain unchanged.

## 0.21.3

Record the unexpected-error/interruption rename rollback fix and its focused
regression validation.

## 0.21.2

Roll back project rename on unexpected renderer exceptions or interruption too,
preserving the old identity and reporting a safe failure instead of leaving a
partially renamed project.

## 0.21.1

Record the project-rename design and successful installed fixture acceptance:
content/history preserved, stopped target enablement transferred, conflicts
refused before mutation, and readable/JSON outcomes logged.

## 0.21.0

Add `team rename-project OLD NEW`. Stop and forget only the old project,
rename its directory and config, and regenerate structured/generated identity
without changing editable prompts, artifacts, conversation history or auth.
Preserve target enablement while leaving the renamed team stopped. Refuse
conflicts before shutdown and roll back partial filesystem/render/enable failures.
Document safe lifecycle use and record readable/JSON rename outcomes.

## 0.20.1

- Record retained-archive restoration behavior, runtime identity decisions and validation references.

## 0.20.0

- Add unarchive: copy a retained archive to its dated project identity, enable the exact target and leave it stopped.
- Preserve archived originals and user content; validate collisions, links, database integrity and actual socket limits, with rollback on failure.

## 0.19.1

Document verified installed dated archives, collision preservation and exact
systemd-instance forgetting. Model-free fixtures exercised failed-unit collection
without changing existing projects, shared templates or other containers.

## 0.19.0

Archive every project to NAME-ddmmyyhhmm using local 24-hour operation-start time.
Refuse dated or exact-name archive collisions before shutdown and preserve
existing contents. Stop/disable only named instances, clear their failed state,
and verify systemd has forgotten them before moving or deleting project files.
Keep timestamp metadata private and explain collisions in safe diagnostic logs.

## 0.18.1

Document verified template migration, preserved operator and project prompts,
and successful new-project creation from the canonical templates directory.

## 0.18.0

Move the editable new-project default to `~/templates/assistant-prompts.md`.
Preserve operator bytes and project-specific prompts, reject linked/conflicting
paths, and verify the copied file before removing its old home-level location.
Project creation and prompt helpers use the canonical template directory.

## 0.17.1

Record verified installed project-status listing. Runtime queries preserve existing
containers and project files; stopped teams remain stopped without inference.

## 0.17.0

Show project runtime status beside each name in `team --list` / `list-projects`.
Distinguish running, starting, stopping, stopped, failed, partial orphan components
and unavailable metadata. Use read-only service/container checks without opening
project contents, authentication or the database, and explain unknown status.

## 0.16.1

Record verified named-project archive/destroy behavior and model-free installed
CLI checks. Disposable fixtures were cleaned; existing projects and account
profiles were retained.

## 0.16.0

Add `destroy NAME` and `archive NAME`. Check and stop only the named running team,
verify writer/container shutdown, then delete its project/config or move their
whole contents into private `~/project-archive/NAME`. Preserve other projects,
shared authentication profiles and images. Reject unsafe paths/archive collisions
before shutdown; record both operations in JSON and human-readable diagnostics.

## 0.15.9

Record verified Antigravity saved-auth detection. Helper-only deployment recognizes
existing native credentials without changing them or restarting any project agent;
remote model access remains unverified.

## 0.15.8

Recognize Antigravity's native nested OAuth token file instead of falsely reporting
failed login. Newly saved evidence survives an intentional TUI interrupt as
saved/unverified; unchanged credentials are explained without demanding another
login. Refresh reporting helpers without provider reinstall or credential changes.

## 0.15.7

Record verified marker-only recovery: all eight native panes are alive with launch
bookkeeping present, and every container and native process remained unchanged.

## 0.15.6

Restore event wake-up bookkeeping after successful Codex builder repair. Failed
launches do not claim success. Add guarded marker-only recovery for an already
live native Codex pane, preserving running sessions and container state.

## 0.15.5

Record successful Codex-only rebuild and native-session repair. The actual builder
process stayed alive and all seven sibling containers remained unchanged. Document
the rule that model authentication stays outside Git, including encrypted Git files.

## 0.15.4

Include `ps` in connector runtime images so Codex can start its managed app server.
Support focused certified image rebuilds and verify process inspection before a
guarded failed-builder repair. Preserve mounted data and other live agents; refuse
replacement when the selected builder is active or uses another harness.

## 0.15.3

- Record successful original-environment deployment and live checks for protected prompt conversion and correlated readable logs.

## 0.15.2

Record the successful guarded retirement and one-pass fresh AAP end-to-end deployment. The verified snapshot is 0.9.1 at commit `405c24f`; newer source changes are outside that fresh-test result. Full update/reboot, native clients, scoped SDK and two-project isolation passed without credentials or model inference.

## 0.15.1

- Record prompt migration and human-readable logging decisions with implementation references and validation.

## 0.15.0

- Provide protected, rotated human-readable runtime logs alongside correlated JSON; deployment transfers include readable logs too.
- Keep exported diagnostics JSON-only and reject symlink log destinations.

## 0.14.0

- Add explicit, backup-protected migration of edited legacy project prompts to bracket sections without restarting sessions.
- Record parallel background work for independent tasks; coordinate shared Git and VM changes.

Keep a concise entry for each version, newest first. Describe what changed and
what it enables, including limitations that affect use. Entries cover committed
changes; a Git tag identifies a published release snapshot.

## 0.13.3

Record the tmux startup race, bounded readiness fix and its validation.

## 0.13.2

Fix the detached Podman startup race by waiting for tmux readiness before harness
launch. Report stopped containers and bounded timeouts without inference; restore
missing idle sessions only after entrypoint initialization finishes. New entrypoints
stop if tmux initialization fails instead of masking that failure.

## 0.13.1

Record the verified prompt-template implementation and its explicit deployment hold.
Add the required future reusable post-deployment acceptance-suite TODO, building
on existing model-free validation rather than implying no checks exist.

## 0.13.0

Create editable prompt templates with `[Project]` and `[Role: Investigator]` style
sections. All starter examples and human guidance use inactive `#` comment lines;
the new renderer excludes them from harness input without fallback. Existing
legacy role headers remain compatible and project files are preserved. Seven new
parser/isolation tests pass (97 total); production lint and APME rescan complete.
Deployment of the new template/parser to the original VM is explicitly held.

## 0.12.1

Record verified runtime help, explicit command errors and listing. Further original-VM
deployment is paused at the operator's request; installed implementation is 0.12.0.

## 0.12.0

Add complete `~/team --help` with commands, parameters and explanations. Unknown
commands explicitly report `Invalid command`; missing project arguments remain
a distinct error. Help needs no auth or service actions, environment commands
route with or without a selected project, and all 90 tests pass.

## 0.11.1

Record verified project listing deployment and both successful runtime aliases.

## 0.11.0

Add `~/team --list` and `~/team list-projects` for sorted initialized project names
without authentication, database/prompt reads or service actions. Exclude partial,
invalid and symlink paths; account profile listing remains `~/team setup --list`.
Update both operator guides. All 86 tests and production lint pass.

## 0.10.3

Record the behavior-preserving Ansible readability review and its implementation.

## 0.10.2

Clarify existing Ansible shell parameter mappings and root-growth result naming;
make runtime account desired state explicit. Commands and behavior are preserved.
The 80-test suite, production lint and contextual APME rescan complete.

## 0.10.1

Record the personal Antigravity implementation, native file-storage protection
limits and successful targeted Ansible deployment with its actual commit.

## 0.10.0

Install the supported personal Antigravity native CLI in the isolated Gemini
private profile with pinned official checksum, scoped login/clear/status support,
and operator instructions. Gemini work remains on Vertex. Native SSH/container
file credentials use local permissions, not encryption at rest. Project role
selection refuses Antigravity until a compatible team adapter is implemented.

## 0.9.3

Record the full APME assessment and its implementation decision with the actual commit.

## 0.9.2

Complete full-codebase APME validation using the verified certified artifact;
document contextual findings, optional dependency-check limits and standing
authorization for read-only scans and assessed fixes. No blind remediation.

## 0.9.1

Record the guarded disposable test lifecycle implementation and its validation.

## 0.9.0

Add guarded AAP retirement of the explicitly selected disposable second test clone, then prepare an independent fresh third-clone deployment. Read-only preflight is the default; removal checks exclusive disk ownership and preserves other domains and the golden image. End-to-end deployment results are recorded after execution.

## 0.8.5

Document the scoped APME evaluation implementation and the non-destructive
operator enablement policy. Unused account contexts stay available without
forcing their login or deleting saved state.

## 0.8.4

Record the authorized local APME audit, pinned source and captured dependency lock.
Builtin-only role checks completed with no remaining violations and17 formatting
proposals preserving YAML values. Full-project scanning remains blocked by its
certified-content installer; this is not a new mandatory gate or full coverage claim.

## 0.8.3

Record the reusable session-context implementation and rationale with its actual
commit. Runtime capability status remains separate from agreed future requirements.

## 0.8.2

Add reusable session rules covering the user's security, Ansible, background-work,
authentication, documentation and release requirements. Link the handoff document
from README so future sessions can recover agreed context without exposing secrets.

## 0.8.1

Document the quality-workflow implementation and its operator prerequisites with
the actual implementation commit. Distinguish configured checks from an executed
CI run; no runner or credential installation is implied.

## 0.8.0

Add one reusable quality command for tests and production-profile lint, plus local
pre-commit hooks and a manually dispatched trusted-runner CI configuration.
No tools, runner registrations or cloud secrets are installed. Existing checks
pass and regressions cover failure propagation and missing Vault input. Actual
CI execution requires an operator-provisioned runner with certified dependencies.

## 0.7.1

Record the verified 0.7.0 AAP outcome and implementation-linked design history.
Add the practical good-practices matrix with explicit check-mode, idempotence,
controller configuration and CI gaps. Correct outdated fresh-test status and the
native profile catalog documentation. AAP job 1380 verified full root allocation,
all native versions and disposable project isolation without model calls.

## 0.7.0

Apply practical Ansible good practices with typed, documented role interfaces,
role-prefixed variables, explicit privilege escalation, a reboot handler and
built-in diagnostic retention. Render role instructions without rerun churn.
Validate full cloned root capacity and publish safe installation metadata through
AAP. Production-profile lint and 71 tests pass; live refactoring verification follows.
Existing encrypted definitions and legacy VM resource overrides remain compatible.

## 0.6.9

Make VM input-validation tests independent of the development Vault by running an isolated fixture playbook. Removing the checkout password assumption no longer prevents tests from reaching the intended safety guards. Four validation tests pass without target connections.

## 0.6.8

Document the fresh launcher bootstrap fix and safe recovery credentials with their implementation commits. The AAP configuration-only verification is in progress; no successful end-to-end result is claimed yet.

## 0.6.7

Fix fresh native CLI installation ordering: install the login helper before the launcher version check. Revalidate all contexts on recovery so an interrupted installation marker cannot conceal a broken launcher. A behavioral fresh-launcher regression and playbook syntax pass. The discovered guest recovery address is kept encrypted; repeat VM creation is avoided.

## 0.6.6

Use the dedicated encrypted become-password field when restoring a guest for configuration-only AAP recovery. Initial provisioning is unchanged, and separate SSH/sudo credentials remain supported.

## 0.6.5

Record explicit Vault input and the preference for suitable Ansible/certified content. Add exploratory future consideration of our own modules/collection; no runtime or active deployment changes.

## 0.6.4

Remove the checkout-relative Vault password path from tracked Ansible configuration. AAP uses its attached Vault credential without a misleading missing-file warning; local operators supply their own explicit file or environment setting. Fresh-playbook syntax and seven portable deployment tests pass.

## 0.6.3

Record the full model-ID usability fix and include its explanation in the reproducible home operator guide. No provider access probe or authentication change.

## 0.6.2

Clarify the Vertex Claude model prompt with a full-ID example and actionable errors for aliases. Keep project/location entitlement explicit and unverified; no model lookup or inference is added. Seven scoped Vertex tests pass, and the helper is deployed without interrupting existing logins.

## 0.6.1

Record the isolated AAP-only fresh deployment decision and safe configuration recovery, with its implementation commit. Actual end-to-end execution remains pending.

## 0.6.0

Add a dedicated normal-AAP-job playbook for isolated fresh provisioning and complete native environment installation, including root growth, full DNF updates, approved SDK and model-free project isolation validation. Keep its encrypted target definition separate and support configuration-only recovery after successful creation. Record AAP source revision in installed build metadata. Syntax validation passes; the actual fresh AAP deployment is the next verification step, not yet claimed complete.

## 0.5.1

Record scoped work SDK installation, correct archive pinning and Vertex provider selection. Documentation only; Google login and model entitlement still belong to the operator.

## 0.5.0

Install the approved Google Cloud CLI 588.0.0 in isolated Claude/Gemini work contexts, sharing only immutable program files. Scoped `./login` now guides user-owned Vertex project/location/model selection and ADC authentication; no cloud APIs, billing settings or model requests were invoked by installation.

Correct the versioned archive checksum after verifying its entire payload against the separately packaged official rolling archive and published digest. Check the installed SDK release exactly and remove staging downloads. Gemini ADC completion selects native Vertex authentication while preserving unrelated settings; competing API-key/ADC environment values are excluded from login setup. Six Vertex tests and the focused live SDK role/version check pass. Model entitlement remains untested and user authentication is still required.

## 0.4.1

Record the future20GiB clone policy and root-filesystem growth rationale. Preserve the already-expanded running VM; this documentation update performs no storage operation.

## 0.4.0

Default fresh Linux VM clones to 20 GiB and expand their direct last GPT root partition/XFS filesystem after guest setup, using the clone's actual capacity rather than retaining the golden image's small filesystem. Add a separate root-growth Ansible role with protected partition-table backups, identity checks and safe idempotent reruns.

The existing VM's already-completed 50 GiB expansion is preserved without shrinking or another reboot; it is not the future-clone default. No separate additional-disk resize feature is retained. Guest role rerun passed unchanged and storage unit/syntax tests pass; fresh 20 GiB end-to-end reprovisioning was not performed.

## 0.3.3

Record why headless Vibe sign-in needed a manual browser handoff and the implementing fix. Documentation only; provider authorization and model access remain separate.

## 0.3.2

Fix headless Vibe browser sign-in: a supported profile-local browser handoff lets native polling and PKCE exchange continue after the user opens the displayed link manually. Previously native browser-launch failure stopped polling while the UI retained the link and later waiting-step text. Preserve provider checks and avoid API-key fallback. Active-session protection also recognizes native CLIs that rewrite their process title.

The installed Vibe 2.26.0 auth service passed a fake-gateway regression proving zero polls after failed GUI opening and successful polling/exchange after manual handoff, without network, auth or model calls. Existing sessions and credentials are preserved; exit the earlier failed session before retrying.

## 0.3.1

Record the independent deployment and target diagnostics decisions with their implementing commit. Documentation update only; fresh-VM validation and provider authentication remain explicitly separate from offline deployment checks.

## 0.3.0

Add a concrete user-operated deployment path for both the current host and SSH destinations, using operator-owned encrypted configuration and the complete certified Podman/native installation role chain. It does not need this coding agent’s destination access or authenticate providers during installation.

- Preserve Ansible’s exit code and collect protected controller metadata; transfer prescribed safe events to the target environment logs when reachable.
- Replay an earlier safe spool explicitly after connection/account failures. Metadata export validates field values and refuses symlink traversal; raw output, access data, credentials and conversations stay excluded.
- Provide an independent deployment guide and version increment helper. A formal release must also push its annotated tag and publish GitHub notes.

Local/SSH command-generation, initializer, replay, schema and failure cases pass offline tests and Ansible syntax checks. No fresh-VM end-to-end installation has yet been performed. SDK installation and provider authentication remain operator-selected prerequisites.

## 0.2.5

Document the login follow-up policy and implementing commit. No additional authentication attempts, model calls or runtime behavior changes.

## 0.2.4

Add actionable provider-specific follow-up lines to login results, with the required prefix. Distinguish retryable account authorization, missing scoped Vertex prerequisites and retired personal Gemini access. Saved credentials suggest an explicit bounded check rather than automatic inference. Vibe guidance reflects its scoped native credential storage.

## 0.2.3

Record the required login-message prefix and its implementing commit. Documentation update only; native authentication and provider-access limitations remain unchanged.

## 0.2.2

Prefix wrapper-owned login outcomes, clear confirmations and actionable errors with `[AC-Agents]:`, while preserving native vendor output. Handle interrupted or unavailable native login commands as failed/cancelled without changing saved credentials. Scoped helpers are deployed in every account context; no model calls were used for validation.

## 0.2.1

Record the selectable environment/project configuration and account isolation rationale, implementing commit and operator limitations. No runtime behavior changes; retain the native-vendor adapter boundaries and provider-access caveats.

## 0.2.0

Add selectable environment profiles and isolated project account contexts.

- `team setup` selects enabled profiles before optional native login; `setup --list` reports installation/local credential evidence without model calls.
- Keep one strict JSON environment definition and separate home-level project role assignments. Prompt files contain goals and role prose; legacy account directives migrate once without becoming a second authority.
- Keep role homes/sessions separate per account and refuse live account/mount replacement. Disabled profiles retain their data; unresolved connector assignments require explicit configuration.
- Provide bounded protected environment metadata logs and manual sanitized export, plus matching full/condensed operator guides and installed version metadata.

Two disposable projects passed stock schema, eight dummy sessions, workspace permissions, stream and independent lifecycle checks without inference. Personal Gemini’s Google OAuth screen is correct, but the provider rejects this CLI client for individuals; no entitlement or paid fallback is implied. Work Vertex SDK approval, Mistral team adapter and automatic observer review remain pending.

## 0.1.1

Document the account/authentication decision and the initial release boundary. Record the implementing commit without changing authentication behavior; work Vertex SDK approval and later integration work remain pending.

## 0.1.0

Add the isolated native account and authentication foundation.

- Provide work/private installations for Claude, Gemini, Codex and Mistral; migrate existing personal installations without copying credentials into work contexts.
- Keep native configuration, credentials and mutable files inside each profile directory. Personal Gemini enforces Google OAuth and local file storage; concurrent login refuses existing native sessions instead of replacing them.
- Report failed/cancelled versus newly saved credentials with model access unverified. Explicit `./login --clear` removes only selected-profile authentication and matching stopped role copies, preserving program files and provider configuration.
- Prepare scoped work Vertex ADC helpers for Claude and Gemini. Google Cloud SDK installation remains approval-gated and is not installed on the development VM.

Mistral remains a standalone native CLI; its team adapter is future work. Environment/project assignment integration and portable diagnostics are committed separately. No automatic model verification or API-billing fallback is introduced.

## 0.0.1

Initial release of the project team framework and shared workspace.

- Create named projects with their own SQLite database, goal, role prompts and
  persistent state. Start, stop, restart and inspect each project independently.
- Run eight roles in rootless Podman containers, with native Claude Code, Codex
  CLI and Gemini CLI sessions accessible through tmux. Provider login is required
  before starting native sessions.
- Exchange messages through agents-connector using MCP and event-driven wake-up.
  Watch the project conversation with the live viewer.
- Share project artifacts in a workspace writable by the seven working roles
  and readable by the observer. Keep native homes and role instructions separate.
- Reproduce the committed setup with Ansible roles and consult the runtime home
  README for operator commands.

Observer snapshots and report delivery are manual. External connector tools and
Mistral team integration are not configured. This release does not claim a
complete fresh-VM deployment test.

Tag: `v0.0.1`; commit: `df70417`. Account separation, authentication fixes,
environment configuration, portable deployment, diagnostics and version tooling
under development at release time are excluded from this snapshot.
