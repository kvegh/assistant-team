# AAP fresh-deployment test results

## Latest verified complete deployment: 1.4.4

AAP retirement preflight 2100 and guarded retirement 2102 succeeded. Only the
explicitly selected previous disposable clone and its exclusively owned disk were
removed. The original installation, every other domain and the golden image
remained unchanged.

Fresh deployment 2104 succeeded in one complete run (31.6 minutes), without
retries or configuration repairs. It ran release 1.4.4, with execution revision
`9049fcd384c6e826a75771cecb81f7d35e9504e6` (before the subsequent repository
history cleanup). Resources were 2 vCPUs, 4 GiB allocated RAM and a 20-GiB virtual
disk. Root capacity was 18.74 GiB, with approximately 11.6 GiB free after setup.

The run verified full DNF updates and reboot, certified Podman configuration,
four native harness images, host CLI installations, Antigravity, Vertex SDK
support, CLI version/help checks and disposable project isolation. Automatic
restore populated all six enabled authentication profiles from encrypted companion
inputs; two unconfigured work profiles stayed disabled. Post-deployment checks
confirmed credential ownership and private file permissions. No model inference
was performed; restored credentials do not establish current provider entitlement.

Guest recap: 523 successful tasks, 135 changed, 144 skipped, no failures or
unreachable hosts. The hypervisor and controller stages also succeeded. The
new recovery binding was encrypted and published separately; retirement remains
bound to the previously authorized clone.

## Earlier fresh end-to-end installation

The dedicated disposable-test retirement preflight (AAP job 1389) and guarded removal (job 1391) succeeded. Only the selected second test domain and its exclusively owned clone disk were removed; other domain names and the golden image file identity, size and modification time were preserved.

The next fresh deployment completed in one full AAP run (job 1394, 30 minutes 12 seconds) at commit `405c24f2f44259dab90545a63d0bd6832b867972`, version `0.9.1`, without configuration recovery or retry. It exercised clean cloning and source-preserving cleanup, 2-vCPU/4-GiB allocation, a 20-GiB virtual disk with full guest root growth, full DNF updates and reboot, certified Podman configuration, native container and host CLI installations, the scoped Vertex SDK, and disposable two-project lifecycle/isolation validation.

Published verification metadata reports root capacity 20,122,152,960 bytes (18.74 GiB), free space 12,999,495,680 bytes (12.11 GiB), and installation verification true. The guest recap was 285 successful tasks, 111 changed, 118 skipped, and zero failures or unreachable hosts; the hypervisor also had zero failures. No provider credentials were copied and no model inference was performed.

This earlier run predates automatic authentication restore. Its deployment hold was subsequently lifted for the explicitly authorized fresh test below. Local validation for that earlier snapshot passed 77 tests and production-profile lint with zero findings.
