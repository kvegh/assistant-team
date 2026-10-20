# linux_vm_shutdown

Gracefully shut down one live inventory-selected VM without deleting any resource.

`shutdown_vm_name` is required. The calling `shutdown_linux_vm.yml` playbook first
resolves its unique explicit `assistant_vm_name` binding in the `assistant_team`
AAP inventory group. Production membership does not block shutdown; it blocks
retirement only. Requires existing libvirt CLI tools and hypervisor access through
the normal AAP Machine credential.

The role validates a single hypervisor, checks the exact domain exists, requests
only graceful shutdown and waits for `shut off`. Already stopped domains remain
unchanged. No forced stop, undefine, file removal or authentication changes occur.
All defined domain names must remain identical after completion. Check mode is
refused because it cannot verify the live shutdown outcome.
