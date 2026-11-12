"""Validate only an ungrouped host left by interrupted fresh registration."""
from ipaddress import IPv4Address
import re
import yaml
from ansible.errors import AnsibleFilterError


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def complete(value):
    require(isinstance(value, dict) and value.get('next') is None
            and isinstance(value.get('results'), list)
            and value.get('count') == len(value['results']), 'Repair requires complete unambiguous API results.')
    return value['results']


def repair_binding(hosts, groups, inventory, name):
    require(re.fullmatch(r'[a-z][a-z0-9-]*-v(?:0[1-9]|[1-9][0-9]+)', name or ''),
            'Repair requires one explicit versioned guest name.')
    require(re.fullmatch(r'[1-9][0-9]*', str(inventory)), 'Repair requires the credential-owned inventory.')
    rows = complete(hosts)
    selected = []
    for row in rows:
        variables = yaml.safe_load(row.get('variables', '')) or {}
        require(isinstance(variables, dict), 'Host variables must be a mapping.')
        if row.get('name') == name or variables.get('assistant_vm_name') == name:
            selected.append((row, variables))
    require(len(selected) == 1, 'Repair requires exactly one current name and explicit ownership binding.')
    host, variables = selected[0]
    # Accept metadata-tagged native Ansible integers without accepting bool IDs.
    require(isinstance(host.get('id'), int) and not isinstance(host['id'], bool)
            and host['id'] > 0 and host.get('inventory') == int(inventory)
            and host.get('name') == name and variables.get('assistant_vm_name') == name
            and host.get('enabled') is True, 'Selected host identity or inventory differs.')
    address = variables.get('ansible_host')
    try:
        require(str(IPv4Address(address)) == address and IPv4Address(address).is_private, 'Select a private canonical guest address.')
    except (ValueError, TypeError):
        raise AnsibleFilterError('Select a private canonical guest address.') from None
    require(sum((yaml.safe_load(row.get('variables', '')) or {}).get('ansible_host') == address for row in rows) == 1,
            'Guest address is shared by another inventory host.')
    managed = complete(groups)
    require(len(managed) == 1 and managed[0].get('name') == 'assistant_team'
            and managed[0].get('inventory') == int(inventory)
            and isinstance(managed[0].get('id'), int) and not isinstance(managed[0]['id'], bool)
            and managed[0]['id'] > 0,
            'Repair requires exactly the managed group in the credential-owned inventory.')
    return {'host_id': host['id'], 'group_id': managed[0]['id'], 'address': address, 'name': name}


def ungrouped(value):
    require(complete(value) == [], 'Repair refuses every existing direct or inherited group, including production.')
    return True


class FilterModule:
    def filters(self):
        return {'assistant_registration_repair_binding': repair_binding,
                'assistant_registration_repair_ungrouped': ungrouped}
