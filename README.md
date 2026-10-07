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
- `src/deploy_linux_vm.yml`: generic golden-image Linux VM provisioning.
- `tests/test_deployment.py`: launch-validation tests without VM changes.
- `ansible.cfg`: local Vault password-file configuration.
- `design_decisions_history.md`: decisions and implementation commit references.

Add application source in `src/`, tests in `tests/`, and static assets in `assets/`
when implementation begins. No application build, runtime, test, or formatting
toolchain has been selected yet.

## Infrastructure

`src/deploy_linux_vm.yml` adapts the existing golden-image Linux VM setup
playbook for the **Generic Linux VM Deployment** AAP job template. It provisions
one VM, waits for its DHCP lease by MAC address, and verifies authenticated
Ansible access, Linux, the hostname, CPUs, and available memory. It does not install AAP.

Launch variables are `vm_name`, `vm_vcpus`, `vm_memory_mb`, and `vm_disk_gb`.
Defaults are 2 vCPUs, 4096 MiB RAM, and a 40 GiB disk. The VM name defaults to
the encrypted configuration. Environment settings and guest credentials are
under `provisioning` in `vars/environment.vault.yml`. AAP must supply the Vault
and hypervisor machine credentials; its project needs a GitHub source-control
credential with read access to this private repository over HTTPS.

Provisioning refuses an existing VM or disk and refuses shrinking the golden
image. A failed deployment preserves resources for investigation; it does not
automatically delete or overwrite them. Increase `vm_disk_gb` if the golden
image is larger than the requested disk. Disk resizing changes the virtual disk
capacity; guest partition and filesystem growth are not performed by this playbook.

The golden image supplies the guest access configuration. Provisioning resets
the cloned machine identity and host keys. Logs are protected with `no_log`;
verified VM details are stored in AAP job artifacts. Keep controller access
restricted, and record deployment details in the encrypted configuration file.

## Validation

Check that encrypted configuration decrypts without displaying its contents:

```bash
ansible-vault view vars/environment.vault.yml >/dev/null
git diff --check
ansible-playbook --syntax-check -i 'localhost,' src/deploy_linux_vm.yml
python3 -m unittest discover -s tests -v
```

The tests reject unsafe names, invalid sizing, and multiple hypervisor targets
before remote work. Python's standard library runs the suite; Ansible must already
be installed. Use `ansible-lint src/deploy_linux_vm.yml` when a working installation
is available. No additional dependencies are installed automatically.
