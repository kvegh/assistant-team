# vertex_auth

Install approved pinned work SDK and isolated Vertex helpers without authentication.

## Interface

vertex_auth_install_sdk defaults false; exact version/checksum are in role defaults.

## Dependencies and platform

Native work profile directories and runtime account already exist.

## Safety, idempotence and check mode

Reuses installed SDK/immutable files; work ADC stays separate. Login and model entitlement are never inferred or invoked by setup.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.

For Gemini work on Vertex, enter the exact provider model ID. The current
Gemini 3.1 Pro identifier is `gemini-3.1-pro-preview`, including the suffix;
`gemini-3.1-pro` is not the published identifier. Confirm model availability for
your project/location in the [official Google model reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-1-pro).
The login prompt checks identifier format, not remote model access. Keep the
selected ID in the local work profile's `.vertex.json`; work role launches copy
that configuration into the selected role home. Provider authentication files
remain outside Git.
