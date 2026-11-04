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

The current pin selects AutoDeploy implementation `1e89880` (0.37.2). It preserves
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
