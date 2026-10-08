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

The full-project check on source revision `405c24f` (version `0.9.1`) targeted
ansible-core `2.16.19`, rather than assuming APME's installed core `2.21.5`
matched AAP. It uploaded 140 files and validated 511 tasks. Native, OPA and
Ansible validators all completed. The initial core result was exit 1 with 408
remaining findings: 361 native and 47 OPA. This is a completed scan with findings,
not a clean policy result.

The earlier certified-content resolution failure was resolved without weakening
requirements or copying credentials. The original certified collection tarball
was already available locally. Its SHA256 matched the authenticated Hub metadata;
APME's upstream `tarball_to_wheel` converter and `ProxyCache` stored the real
artifact in the proxy's normal offline cache. The isolated scan then installed
`redhat.rhel_system_roles:1.120.5` through that proxy. An ordinary Ansible collection
search path alone does not satisfy APME's isolated dependency installer.

A second run enabled installed optional collection-health and Python-audit
validators. Collection health completed with 1,176 additional risk indicators in
the third-party certified collection; combined output contained 1,584 findings.
These do not become defects in our repository or justify editing vendor content.
Gitleaks was not installed and was not run.

| Finding group | Assessment |
| --- | --- |
| 131 possibly undefined variables (`L039`) | Static uncertainty around encrypted inputs, registered values and role data; no evidence that all are runtime failures. |
| Parameterized file paths and deletion (`R114`, `R115`) | Review the actual validation and ownership guards. Existing retirement checks constrain the domain and prove exclusive disk ownership before deletion. |
| Parameterized commands and privilege escalation (`R101`, `R108`) | Risk indicators requiring context; quoted argument arrays and authorized privileged deployment are intentional. |
| Five high-severity `M005` findings | Future Ansible 2.19+ templating migration warnings, not proof of defects in the supported 2.16.19 target. |
| Local archive flagged as unauthorized network transfer (`R104`) | False positive for `unarchive` with `remote_src: true` on a downloaded checksum-pinned local file. |
| Backups, inline environment, loop naming and bracket notation | Advisory preferences; blanket changes can add credential copies or obscure deliberate runtime isolation. |

The initial `L057` syntax diagnostic came from a playbook's encrypted
`vars_files`: the scanner had no Vault secret and reported that decryption could
not proceed. Do not weaken Vault or expose decrypted inputs to make this scan
appear clean. The final dry-run rescan reported no Ansible violations; that does
not independently prove the original encrypted playbook's syntax without its
operator-provided Vault context.

The integrated Python auditor uses strict mode and could not audit the converted
certified collection wheel because it is not a PyPI distribution. Its empty
findings therefore do not mean a passing dependency audit. A separate run of the
already installed `pip-audit`, without strict mode, explicitly recorded that
collection as unauditable and examined public Python dependencies. It reported
14 entries representing seven unique CVEs in `pip 23.2.1`, bootstrapped inside
APME's disposable session virtual environment. This is an audit-tool environment
issue, not evidence about pip installed on a deployed VM. Keep these results
separate; do not claim full dependency coverage.

No project code changes were justified solely by these indicators after the
initial assessment. Relevant findings may be fixed after contextual review,
meaningful validation and documentation; raw counts are not a compliance grade.
The production-profile ansible-lint check remains the established quality gate.

## Safety and repeatability

OPA ran locally through the approved rootless Podman image
`docker.io/openpolicyagent/opa:1.17.1`. The isolated daemon used separate loopback
ports when the defaults were occupied and was stopped after each scan. State and
reports remained in protected temporary storage. There was no Vault decryption,
external AI request, automatic source remediation or host deployment action.
APME's `check` command does propose and rescan edits in its temporary sandbox;
it did not apply those edits to the repository.

For a future offline scan, verify the original certified tarball against trusted
Hub artifact metadata before populating the normal proxy cache through its
upstream converter/cache API. Keep dependency requirements unchanged. Configure
optional validators' session root to the actual isolated collection-cache
`sessions` directory so their containment checks remain effective. Do not disable
those checks or interpret unavailable validators as successful checks.

All read-only APME scans are authorized by the operator. Tool installation,
credential protection and security-control rules still apply. Assess findings
against the supported deployment and fix relevant security, compliance or
stability defects; do not blindly apply automatic upstream remediation.

References: [upstream CLI guide](https://github.com/ansible/apme/blob/fe9bcb747a92ead08d269ffcc5026110932eb403/docs/guides/CLI.md)
and [dependency provisioning](https://github.com/ansible/apme/blob/fe9bcb747a92ead08d269ffcc5026110932eb403/src/apme_engine/venv_manager/session.py).
