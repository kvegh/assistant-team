# project_workspace

Add missing shared artifact directories to initialized existing projects.

## Interface

containers.runtime_user identifies the owner.

## Dependencies and platform

project_framework layout exists.

## Safety, idempotence and check mode

Built-in find/stat/file are idempotent. Active containers acquire new mounts only at normal stop/start.

## Validation

Run the repository production lint and tests. Fresh installation and configuration recovery are verified through the normal AAP deployment template; authenticated model tests are separate operator actions.
