# Release notes

Keep a concise entry for each version, newest first. Describe what changed and
what it enables, including limitations that affect use. Entries cover committed
changes; a Git tag identifies a published release snapshot.

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
