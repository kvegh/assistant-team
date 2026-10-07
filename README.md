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
- `src/templates/clean_linux_clone.sh.j2`: cleanup inside the cloned image.
- `src/reset_linux_identity.sh`: reset cloned machine identity and SSH host keys.
- `tests/test_deployment.py`: launch-validation tests without VM changes.
- `tests/test_clone_cleanup.py`: checks that cleanup preserves protected accounts.
- `tests/test_identity_reset.py`: identity reset with a missing legacy D-Bus directory.
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
Memory verification checks the exact allocation in libvirt and accounts for the
guest kernel's crash-recovery reservation when checking usable RAM. Controller
artifacts report allocated RAM, guest-visible RAM, and the crash reservation separately.

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

Before booting, provisioning removes AAP installer artifacts under `/opt/sources`,
the unused AAP service account and its home, associated lingering and sudo entry,
package caches, inherited shell histories, and logs from the cloned disk. The
automation access account is preserved. Configure `provisioning.aap_service_user`
in Vault; cleanup refuses to remove root, the automation account, or an account
with an unexpected home directory. The shared source image is never customized.
Guest verification checks that installer artifacts and the AAP account are absent.

After boot, the job registers RHEL with the existing activation key if needed,
enables BaseOS and AppStream, updates every installed package with DNF, and
reboots if packages changed. It reconnects and requires `dnf --refresh check-update`
to return no pending updates before publishing success. Subscription details are
encrypted under `provisioning.rhsm_org` and `provisioning.rhsm_activation_key`.

If provisioning succeeded but guest configuration failed, rerun the same template
with the `guest_config` job tag and the same VM name. This discovers the existing
guest through libvirt and resumes guest configuration without cloning or replacing
its disk. The template must allow job tags at launch and must not use a hypervisor-only
host limit, because the later play runs against a dynamically added guest.

If offline customization failed before a VM was defined, use the `offline_recovery`
job tag to resume customization and boot from the existing disk without repeating
the copy or cleanup. Recovery refuses to customize a disk associated with a defined
VM. For that identity task alone, `vm_identity_diagnostics: true` reveals its command
result temporarily; other task output and guest credentials remain protected.
The diagnostic default remains off.
For guest resource mismatches, `vm_guest_verification_diagnostics: true` reveals
only the verification assertion and basic OS, hostname, CPU, and memory values.
Guest connection and subscription credentials remain protected.

The golden image supplies the guest access configuration. Provisioning resets
the cloned machine identity and host keys. Logs are protected with `no_log`;
verified VM details are stored in AAP job artifacts. Keep controller access
restricted, and record deployment details in the encrypted configuration file.

## Deployment status

The private repository has synchronized successfully to its AAP project using a
repository-scoped GitHub credential. Local syntax checks and all eight tests pass.
Live deployment has not started: the AAP MCP connection currently rejects its
configured authentication token. Job-template creation still needs confirmation
after controller access is restored. Environment-specific controller references
and the approved VM hostname remain in the encrypted configuration.

## Validation

Check that encrypted configuration decrypts without displaying its contents:

```bash
ansible-vault view vars/environment.vault.yml >/dev/null
git diff --check
ansible-playbook --syntax-check -i 'localhost,' src/deploy_linux_vm.yml
python3 -m unittest discover -s tests -v
```

The tests reject unsafe names, invalid sizing, and multiple hypervisor targets
before remote work, and verify cleanup account guards without deleting files.
Python's standard library runs the suite; Ansible must already
be installed. Use `ansible-lint src/deploy_linux_vm.yml` when a working installation
is available. No additional dependencies are installed automatically.
