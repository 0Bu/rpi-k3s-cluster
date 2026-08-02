#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repository_root}"

if [[ "$(git branch --show-current)" != "codex/pi5b-bootstrap" ]]; then
  printf 'Safety stop: expected branch codex/pi5b-bootstrap, got %s\n' "$(git branch --show-current)" >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --requirement bootstrap/requirements.txt

export ANSIBLE_CONFIG="${repository_root}/bootstrap/ansible.cfg"
export ANSIBLE_LOCAL_TEMP="${repository_root}/.ansible/tmp"
mkdir -p "${ANSIBLE_LOCAL_TEMP}" "${repository_root}/.state/pi5b"

exec .venv/bin/ansible-playbook bootstrap/playbooks/pi5b.yml --limit pi5b "$@"
