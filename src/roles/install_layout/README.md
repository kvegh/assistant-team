# Install layout

`assistant_install_prefix` is the absolute destination parent. Its default empty
value resolves the destination runtime account's home, not the controller home.
The installation root is `PARENT/ac-agents`, with protected model, project, config,
archive and diagnostic subdirectories. Real HOME remains the user manager and
rootless Podman identity; standard engine storage is not relocated.

Existing legacy home-level environment markers fail closed before install
content changes. Automatic migration is not implemented. This source change
must not be deployed to the current environment until controlled migration or a
fresh destination is explicitly selected.

The assistant_* path variables are an explicit cross-role public contract; the
narrow role-prefix lint exceptions retain this shared API rather than duplicating
path formulas in every role. Internal facts keep the install_layout prefix.
