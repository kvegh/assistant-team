# linux_vm_retire

Retire only the explicitly selected disposable second test clone, through a normal AAP job.

## Interface and dependencies

Encrypted `linux_vm_retire_definition` supplies the exact domain, disk directory and source image. `linux_vm_retire_execute` defaults false for read-only preflight. The calling play computes the exact clone disk. Requires existing libvirt CLI tools.

## Safety and validation

Accepts only the second disposable clone naming convention. Refuses shared, extra, symbolic or source-image disks. Checks every defined domain's disk references, uses graceful shutdown only, and confirms all other domain names and source-image file identity remain intact. No wildcard deletion, credential copying, forced stop or source modification. Live preflight is required; check mode is refused. A completed removal is deliberately not repeated. Run production lint and validate through its dedicated AAP template.
