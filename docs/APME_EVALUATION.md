# Local APME evaluation

APME was installed in an isolated local Python 3.12 virtual environment from
upstream release `v2026.10.1`, commit
`fe9bcb747a92ead08d269ffcc5026110932eb403`. Its wheel reports version `0.1.0`;
the source release identifies the evaluated snapshot. The captured dependency
lock records the installation; it is an optional audit tool, not a deployed
runtime dependency or mandatory quality gate.

```sh
python3.12 -m venv local/apme
local/apme/bin/python -m pip install -r docs/apme-requirements.lock
```

Installation is an explicit operator action. The project does not run this
installer automatically. Use SSH Git access for the pinned upstream source.

## Result and coverage

The full-project check targeted ansible-core `2.16.19`, rather than assuming the
tool's installed core `2.21.5` matched AAP. It failed with exit 2 because APME's
Galaxy Proxy could not provision certified `redhat.rhel_system_roles:1.120.5`.
The existing local Ansible collection search path did not satisfy its isolated
session dependency installer. This is an infrastructure failure, not a passing
policy result. The certified requirement was retained.

A separate partial check excluded `agent_images`, `agents_connector` and
`podman_host`, the three roles referencing certified content. It uploaded 58
files and the Ansible validator checked 31 files. Native, Ansible and OPA
validators returned no remaining violations; exit 0. Dependency collection-health
and Python-CVE validators were explicitly skipped for this partial evaluation.
APME check is a dry-run remediation pipeline: its 17 proposed file changes were
formatting/key ordering, and parsed YAML values matched the originals. No source
changes were applied. These results do not establish whole-repository coverage.

OPA ran locally through the approved rootless Podman container; upstream selected
`docker.io/openpolicyagent/opa:1.17.1`. The daemon used loopback only, with protected
state/output in a temporary directory. No Vault decryption, external AI/model
request or automatic remediation was performed. No daemon remained running at
completion. Production-profile ansible-lint remains the existing verified check.

Full APME evaluation needs a supported authenticated certified-content path through
its Galaxy Proxy. Do not remove certified requirements, leak Hub credentials,
interpret scan-aborted as clean, or add this incomplete scan as a required gate.

References: [upstream CLI guide](https://github.com/ansible/apme/blob/fe9bcb747a92ead08d269ffcc5026110932eb403/docs/guides/CLI.md)
and [dependency provisioning](https://github.com/ansible/apme/blob/fe9bcb747a92ead08d269ffcc5026110932eb403/src/apme_engine/venv_manager/session.py).
