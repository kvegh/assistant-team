# Ansible good-practices review

Reference: [Red Hat Automation Good Practices](https://redhat-cop.github.io/automation-good-practices/).
The guide is opinionated; this review applies it to this repository without adding
unnecessary architecture. It covers this project, not the umbrella repositories.

| Area | Applied here | Limits or next work |
| --- | --- | --- |
| Desired state and roles | Playbooks call separate roles; the fresh guest play contains roles rather than mixed role/task orchestration. | Runtime login, routing and project-control programs remain application code installed by Ansible. |
| Module choice | Built-in users, files, templates, facts, services and retention tasks; pinned certified system roles and Podman modules. | Guarded image transfer and storage safety checks retain commands where modules do not express the needed operation clearly. |
| Role contracts | Each deployed role has a README and argument specifications; owned variables have role prefixes. | Shared encrypted `provisioning` and `containers` dictionaries are deliberate cross-role interfaces. Legacy VM resource aliases remain compatible. |
| Inventory and secrets | Isolated encrypted deployment definitions, dynamically discovered guest inventory, explicit Vault credentials. | Real connections and operator secrets are not example inventory data. |
| Idempotence and handlers | Read-only commands report no change; guarded mutations report changes; reboot is a notified handler; role instructions render in one template. | Disposable verification deliberately creates and removes fixtures. Downloads and image builds can still report changes; zero-change whole-play convergence is not claimed. |
| Check mode | Role READMEs describe required live facts and validation. | Image export/build, native CLI checks and fixture lifecycle need a live installation. Universal check-mode support is not claimed. |
| Naming and style | Named tasks, FQCNs, YAML/Jinja formatting, explicit privilege changes; production-profile lint passes. | Certified role internals are upstream content and are not rewritten here. |
| Testing | Behavioral unit tests, syntax checks and normal AAP fresh/recovery runs; validation checks full root capacity and two-project isolation. | No authenticated inference during deployment. Molecule matrix and a second portable-runner fresh target are not yet exercised. |
| Dependencies | Pinned certified collection, CLI artifacts and SDK checksums; documented role ordering. | Hub authentication and target prerequisites remain operator-owned. No unsolicited test-tool installation. |
| Logging and errors | Protected metadata diagnostics, bounded retention, explicit failure guards, protected sensitive tasks. | Some broad `no_log` scopes reduce failed-task detail; scoped safe diagnostic improvements remain useful. |
| AAP configuration | Private HTTPS SCM, explicit credentials, certified dependency synchronization and recovery tags. | Controller configuration-as-code draft is not verified or included as a supported deployment path yet. |
| Quality workflow | Versioned focused commits, release notes, implementation-linked history and operator guides. | CI, pre-commit installation, branch protections and signing are not configured automatically; they require a separate practical proposal. |
| Collections and custom modules | Suitable certified content is preferred without forcing a collection migration. | Project-owned module/collection development is exploratory backlog work. |

The local production lint and unit suite are necessary checks, not a blanket
compliance certificate. Live deployment outcomes and known limitations are recorded
in the design history and release notes.
