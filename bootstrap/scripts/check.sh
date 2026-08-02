#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repository_root}"

python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --requirement bootstrap/requirements.txt

export ANSIBLE_CONFIG="${repository_root}/bootstrap/ansible.cfg"
export ANSIBLE_LOCAL_TEMP="${repository_root}/.ansible/tmp"
mkdir -p "${ANSIBLE_LOCAL_TEMP}"

.venv/bin/ansible-playbook \
  --inventory bootstrap/inventory/pi5b/hosts.yml \
  bootstrap/playbooks/cluster.yml \
  --syntax-check
.venv/bin/python bootstrap/scripts/validate_cluster_networks.py \
  bootstrap/inventory/pi5b/hosts.yml \
  bootstrap/inventory/pi5b/group_vars/all.yml
.venv/bin/python bootstrap/scripts/validate_helm_applications.py clusters/pi5b/argocd
