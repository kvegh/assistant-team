# Recovery guest isolation release

After the existing generic Linux deployment verifies authenticated guest facts,
hostname, resources and requested configuration, this role fetches the reviewed
AutoDeploy implementation at an exact Git revision and includes its shared role
inside the same job. A failure during guest setup never reaches this role.

The existing job needs its current SSH/snapshot/Vault credentials plus the existing
AutoDeploy source API, Git writer, CaC Vault and source CA credentials. These allow
the verified transition to be saved in the existing encrypted captures and source
inventory. There is no additional job, wrapper playbook, credential type or store.

The selected guest returns to normal IPv4 firewall handling. Production addresses
remain explicitly blocked; other guests, normal firewalld, private MCP policy and
IPv6 quarantine are retained. Runtime identity checks, atomic apply, readback,
durable publication and bounded rollback are implemented in the shared AutoDeploy
role. Failed publication must be resolved before the deployment reports success.

The current pin selects AutoDeploy implementation `f22171b8` (0.62.3).
This includes the native YAML serializer compatible with Core 2.20's dumper
factory. The old dependency could fail while loading publication code after
the guest had passed verification. Synchronize the caller and use `guest_config`
to continue on that same guest; local compatibility checks are not live
publication acceptance.
This shared source reads instance Zabbix firewall settings from
`zabbix.configuration.firewall`. Update its encrypted CaC layout and caller pin
together; a stale explicit dependency override is refused.

Its existing shared role accepts `linux_recovery_release_operation: guest_bootstrap_https`
through this caller to grant only approved public IPv4 TCP 443 access. The
complete-deployment playbook invokes that permission only after authenticated
base/root verification, then requests default `release_guest` only after all
updates, software and model-free installation validation succeed. The generic
Linux playbook keeps its existing default full-release order. Update provenance
is false before the update role's final check and true only after that check.

The same caller accepts `linux_recovery_release_operation: guest_bootstrap_http`
for public IPv4 TCP 80 to public destinations only. The complete playbook uses
it after HTTPS has published verified ownership, and only when the selected
encrypted generic profile explicitly sets `container_build_http_bootstrap: true`.
That approval is bound to the profile's exact VM name and reviewed pin; it
defaults off for every other profile. Private/reserved and production blocks,
host-service restrictions and full-release ordering remain unchanged. Exact
guest retirement removes its own HTTP permission as well.

Each shared publisher invocation resolves encrypted repository settings through
its current native action-plugin path. Ansible may retain an imported plugin
after the previous checkout is removed; the current path prevents that cached
module from reading the deleted directory. Missing or invalid native paths refuse
publication. Authentication, identity and policy checks and per-call cleanup
remain unchanged.

The implementation preserves
AAP inventory display aliases through existing verified physical VM ownership.
It also supports a fresh source that has not installed the optional Hactar
inventory, accepting its absence only after an authenticated source API
superuser check. Shared/recovery inventory requirements, exact guest ownership,
production protection and trusted TLS remain enforced.
The same reviewed code persists approved native firewalld grants in saved policy
metadata, so later host firewall reconciliation retains the declared permissions.

For an existing successfully provisioned generic guest, use the same deployment
template with `guest_config` tags to repeat authenticated verification without
cloning or replacing its disk. Keep its saved image and complete current isolation
policy consistent with the maintained encrypted configuration. The temporary
public-code checkout is removed on success and failure.
For the current serialized test, refresh only the selected encrypted profile and
its injected ciphertext to canonical policy before a retry following bootstrap or
release. The strict policy check is not relaxed and no automatic cross-inventory
policy lookup is introduced.

The same role accepts `linux_recovery_release_operation: retire_guest` with
`linux_recovery_release_retire_phase: plan` or `publish`, the exact
`linux_recovery_release_retire_guest_name` and independently pinned
`linux_recovery_release_retire_hypervisor`. It includes the shared retirement
tasks in the existing job. Plan before physical deletion; publish after verified
domain/disk absence and before removing this application's inventory row. Saved
canonical/API ownership supports interrupted retries without guest SSH. Temporary
code and trust files are cleaned after each phase.
The pinned shared plan keeps a missing guest as a real null value rather than
empty text in either Ansible mode. This permits the existing verified-absence
retry after shared ownership removal; native absence and all production guards
remain mandatory.

The current source reader also accepts canonical decimal Controller SSH-port
strings only when they equal the exact integer pin. Malformed, out-of-range or
different values are refused; no live port or credential is rewritten.
