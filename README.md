# assistant-team

Private project for an assistant team. Application requirements are still being defined.

## Security

Repository privacy does not replace encryption. Store all environment-specific
data, including usernames, hostnames, addresses, credentials, and tokens, in
Ansible Vault-encrypted files. Plaintext documentation and examples must use
generic placeholders. Never commit the Vault password file or decrypted output.

## Vault setup

Ansible and Git must already be available. Run commands from this repository.
`ansible.cfg` uses the existing workspace password file at `../../vpf`.
The password file stays outside this repository; do not copy it here.
On another checkout, override the location with `ANSIBLE_VAULT_PASSWORD_FILE`.
Ansible uses a project-specific temporary directory under `/tmp` for local work.

```bash
ansible-vault edit vars/environment.vault.yml
ansible-vault encrypt path/to/environment-specific.yml
ansible-vault view vars/environment.vault.yml
```

The last command displays plaintext locally; do not capture or commit its output.

## Layout

- `vars/environment.vault.yml`: encrypted environment configuration.
- `ansible.cfg`: local Vault password-file configuration.
- `design_decisions_history.md`: decisions and implementation commit references.

Add application source in `src/`, tests in `tests/`, and static assets in `assets/`
when implementation begins. No application build, runtime, test, or formatting
toolchain has been selected yet.

## Infrastructure

Reuse the golden-image Linux VM setup playbook from the existing automation
repositories through a dedicated AAP job template. Run only VM provisioning;
the later AAP installation stages are outside this project's initial scope.
Record actual environment details and deployment results in the encrypted file.

## Validation

Check that encrypted configuration decrypts without displaying its contents:

```bash
ansible-vault view vars/environment.vault.yml >/dev/null
git diff --check
```
