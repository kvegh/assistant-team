# Release notes

Keep a concise entry for each version, newest first. Describe what changed and
what it enables, including limitations that affect use. Entries cover committed
changes; a Git tag identifies a published release snapshot.

## 0.4.1

Record the future20GiB clone policy and root-filesystem growth rationale. Preserve the already-expanded running VM; this documentation update performs no storage operation.

## 0.4.0

Default fresh Linux VM clones to 20 GiB and expand their direct last GPT root partition/XFS filesystem after guest setup, using the clone's actual capacity rather than retaining the golden image's small filesystem. Add a separate root-growth Ansible role with protected partition-table backups, identity checks and safe idempotent reruns.

The existing VM's already-completed 50 GiB expansion is preserved without shrinking or another reboot; it is not the future-clone default. No separate additional-disk resize feature is retained. Guest role rerun passed unchanged and storage unit/syntax tests pass; fresh20GiB end-to-end reprovisioning was not performed.

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
