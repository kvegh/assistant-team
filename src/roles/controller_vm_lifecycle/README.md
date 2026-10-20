# Controller VM lifecycle setup

`configure_vm_lifecycle.yml` reconciles three narrowly prompted job templates,
the `assistant_team` and `prod` inventory groups, and their dedicated lifecycle
credential. It does not start jobs, change existing host memberships, or delete
controller resources. Existing credential associations are retained.

Provide the controller URL, administrator setup token, organization, project,
inventory, execution environment and required credential IDs through the
`controller_vm_lifecycle_*` variables. The release pin is managed separately.
Controller REST requests support the custom credential schema and surveys without
requiring an additional execution-environment collection.

The lifecycle token and controller CA bundle come from operator-owned absolute
paths, `AC_AGENTS_LIFECYCLE_TOKEN_FILE` and `AC_AGENTS_LIFECYCLE_CA_FILE`.
The token must belong to a nonadministrator, nonsystem-auditor principal with
direct administrator membership on the selected inventory. Provisioning that
principal and its narrowly scoped grant is an explicit prerequisite. This role
verifies that grant rather than silently widening privileges.

Surveys require a target name without a default. Retirement defaults to a
read-only preflight; select `true` for `retire_test_execute` to delete. Arbitrary
launch extra variables and simultaneous runs are disabled. Membership in `prod`
is enforced by the runtime inventory guard, independently of survey answers.
