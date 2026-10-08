# linux_root_growth

Grow only the existing last GPT root partition and XFS filesystem.

## Interface

No tunable inputs; rejects unsupported filesystem/storage layouts.

## Dependencies and platform

growpart, sfdisk, lsblk, findmnt and xfs_growfs on the selected guest.

## Safety, idempotence and check mode

Mutation is idempotent with protected partition-table backups. Live GPT/XFS validation is required; do not treat check mode as a storage preview.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
