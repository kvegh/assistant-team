# Native Antigravity team runtime

Verify the already installed personal Antigravity 1.3.1 executable inside the
existing Gemini connector image after `native_auth` has prepared profiles. The
binary is mounted read-only; the temporary smoke container has no network or
credentials and runs only `--help`. No native tools are auto-approved.

`agents_connector` installs the scoped lifecycle adapter and selects the native
Antigravity executable when a project's challenger uses `gemini-priv`. MCP uses
Antigravity's separate native configuration; account credentials are copied only
when the corresponding role context has none. Work authentication is isolated.
