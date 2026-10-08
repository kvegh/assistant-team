# environment_validation

Verify that a cloned root filesystem uses its configured disk allocation, then
optionally exercise two disposable projects with dummy harnesses. No provider
credentials or inference are used.

Inputs are environment_validation_expected_disk_gb (20 by default) and
environment_validation_run_projects (false by default). The fresh AAP playbook
explicitly enables the model-free project check. Root capacity allows two GiB for
boot partitions and filesystem overhead.

Requires the full environment role chain and exported podman_host_runtime_home
and podman_host_runtime_uid. It publishes numeric filesystem capacity and
installation/source version artifacts. Model-free lifecycle checks create and
clean up only unique fixture projects, leaving other projects untouched.

The checks need a live configured guest; check mode cannot create their fixtures.
