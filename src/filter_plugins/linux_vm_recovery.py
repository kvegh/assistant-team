"""Validate an explicit recovery connection and its two independent SSH identities."""

from ipaddress import IPv4Address
import re
import shlex

from ansible.errors import AnsibleFilterError


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def recovery_pin(pin, address):
    require(isinstance(pin, dict), "Supply the independently verified recovery hypervisor pin.")
    try:
        normalized = str(IPv4Address(pin.get("address")))
    except (ValueError, TypeError):
        raise AnsibleFilterError("Pin the recovery hypervisor IPv4 address.") from None
    require(normalized == pin["address"] == address, "The inventory host must match the recovery hypervisor pin.")
    require(isinstance(pin.get("machine_id"), str) and re.fullmatch(r"[a-f0-9]{32}", pin["machine_id"]),
            "Pin the recovery hypervisor machine identity.")
    require(isinstance(pin.get("user"), str) and pin["user"] != "root"
            and re.fullmatch(r"[a-z_][a-z0-9_-]*", pin["user"]), "Use the pinned managed hypervisor account.")
    require(type(pin.get("port")) is int and 1 <= pin["port"] <= 65535, "Pin the managed SSH port.")
    public_keys(pin.get("host_keys"))
    return pin


def public_keys(values):
    require(isinstance(values, list) and values and all(isinstance(key, str) and re.fullmatch(
        r"(?:ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)) [A-Za-z0-9+/]+={0,2}", key)
        for key in values), "Require explicitly provisioned public SSH host keys.")
    return values


def public_key(value):
    result = " ".join(value.split()[:2])
    public_keys([result])
    return result


def guest_ssh(pin, trust_file, alias):
    recovery_pin(pin, pin.get("address"))
    require(isinstance(trust_file, str) and trust_file.startswith("/") and "\n" not in trust_file,
            "Allocate a private controller-side SSH trust file.")
    require(isinstance(alias, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,62}", alias),
            "Use the selected guest name as its SSH host-key alias.")
    proxy = ("ssh -o BatchMode=yes -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no "
             "-o StrictHostKeyChecking=yes -o UserKnownHostsFile=%s -p %s -W %%h:%%p %s@%s" %
             (shlex.quote(trust_file), pin["port"], pin["user"], pin["address"]))
    return "-o StrictHostKeyChecking=yes -o UserKnownHostsFile=%s -o HostKeyAlias=%s -o ProxyCommand=%s" % (
        shlex.quote(trust_file), shlex.quote(alias), shlex.quote(proxy))


def saved_keys(data, name, identity, hypervisor_id, source_hash):
    require(isinstance(data, dict) and data.get("schema_version") == 1
            and data.get("deployment_type") == "generic-recovery"
            and data.get("vm_name") == name and data.get("uuid") == identity
            and data.get("hypervisor_machine_id") == hypervisor_id
            and data.get("source_image_sha256") == source_hash,
            "The existing domain's saved public provenance does not match this recovery target.")
    return public_keys(data.get("host_keys"))


class FilterModule:
    def filters(self):
        return {"linux_vm_recovery_pin": recovery_pin, "linux_vm_public_key": public_key,
                "linux_vm_public_keys": public_keys, "linux_vm_recovery_guest_ssh": guest_ssh,
                "linux_vm_recovery_saved_keys": saved_keys}
