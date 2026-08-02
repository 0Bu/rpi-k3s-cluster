#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repository_root}"

cluster_name="${1:-}"
case "${cluster_name}" in
  pi5b|pi5c) ;;
  *)
    printf 'Usage: %s <pi5b|pi5c> [ansible-playbook arguments...]\n' "$0" >&2
    exit 2
    ;;
esac
shift

if [[ "$(git branch --show-current)" != "codex/pi5b-bootstrap" ]]; then
  printf 'Safety stop: expected branch codex/pi5b-bootstrap, got %s\n' "$(git branch --show-current)" >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --requirement bootstrap/requirements.txt

export ANSIBLE_CONFIG="${repository_root}/bootstrap/ansible.cfg"
export ANSIBLE_LOCAL_TEMP="${repository_root}/.ansible/tmp"
mkdir -p "${ANSIBLE_LOCAL_TEMP}" "${repository_root}/.state/${cluster_name}"

exec .venv/bin/ansible-playbook \
  --inventory "bootstrap/inventory/${cluster_name}/hosts.yml" \
  bootstrap/playbooks/cluster.yml \
  --limit "${cluster_name}" \
  "$@"
