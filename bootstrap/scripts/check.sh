#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repository_root}"

python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --requirement bootstrap/requirements.txt

export ANSIBLE_CONFIG="${repository_root}/bootstrap/ansible.cfg"
export ANSIBLE_LOCAL_TEMP="${repository_root}/.ansible/tmp"
mkdir -p "${ANSIBLE_LOCAL_TEMP}"

.venv/bin/ansible-playbook bootstrap/playbooks/pi5b.yml --syntax-check
.venv/bin/python bootstrap/scripts/validate_helm_applications.py clusters/pi5b/argocd
