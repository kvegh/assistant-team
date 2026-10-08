# AAP fresh-deployment test results

## Verified fresh end-to-end installation

The dedicated disposable-test retirement preflight (AAP job 1389) and guarded removal (job 1391) succeeded. Only the selected second test domain and its exclusively owned clone disk were removed; other domain names and the golden image file identity, size and modification time were preserved.

The next fresh deployment completed in one full AAP run (job 1394, 30 minutes 12 seconds) at commit `405c24f2f44259dab90545a63d0bd6832b867972`, version `0.9.1`, without configuration recovery or retry. It exercised clean cloning and source-preserving cleanup, 2-vCPU/4-GiB allocation, a 20-GiB virtual disk with full guest root growth, full DNF updates and reboot, certified Podman configuration, native container and host CLI installations, the scoped Vertex SDK, and disposable two-project lifecycle/isolation validation.

Published verification metadata reports root capacity 20,122,152,960 bytes (18.74 GiB), free space 12,999,495,680 bytes (12.11 GiB), and installation verification true. The guest recap was 285 successful tasks, 111 changed, 118 skipped, and zero failures or unreachable hosts; the hypervisor also had zero failures. No provider credentials were copied and no model inference was performed.

Later source changes are outside that tested snapshot. Further deployments, including operator-guide metadata updates, are held at the user's request; the deployment-test AAP project remains pinned to the tested commit. Local validation before deployment passed 77 tests and production-profile lint with zero findings.
