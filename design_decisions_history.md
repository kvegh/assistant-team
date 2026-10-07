# Design decisions history

## Initial project setup

Implementation: `83589382dd6311e87564bdcf5529cf511fca7849`.

The user chose a new private repository rather than adding this project to an
existing private repository. Privacy does not replace encryption: all sensitive
and environment-specific configuration must use Ansible Vault with the existing
workspace password file. The password file remains outside Git. An encrypted
configuration file and documented Vault commands establish this convention.

Ansible's local temporary directory is configured under `/tmp` because the
default home-directory location is read-only in the development environment.
Encryption and decryption were verified without displaying decrypted contents.

Application requirements and tooling remain undecided. Existing golden-image
Linux provisioning is the planned basis for the first VM, with a separate AAP
job template to avoid changing another project's deployment settings. The user
specified two vCPUs and 4 GiB RAM. A 40 GiB disk is an initial implementation
assumption, not an explicit user requirement. Provisioning has not run yet.
