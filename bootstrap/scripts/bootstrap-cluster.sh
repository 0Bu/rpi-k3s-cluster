#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repository_root}"

cluster_name="${1:-}"
case "${cluster_name}" in
  pi5b|pi5c) ;;
  *)
    printf 'Usage: %s pi5b|pi5c [--storage-backend nfs|local-path] [--nfs-server-host HOST] [ansible-playbook arguments...]\n' "$0" >&2
    exit 2
    ;;
esac
shift

storage_backend=nfs
nfs_server_host=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    --storage-backend)
      if [[ $# -lt 2 ]]; then
        printf 'Safety stop: --storage-backend requires nfs or local-path.\n' >&2
        exit 2
      fi
      storage_backend="$2"
      shift 2
      ;;
    --nfs-server-host)
      if [[ $# -lt 2 || -z "$2" ]]; then
        printf 'Safety stop: --nfs-server-host requires an inventory hostname.\n' >&2
        exit 2
      fi
      if [[ ! "$2" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]*$ ]]; then
        printf 'Safety stop: invalid NFS server hostname %s.\n' "$2" >&2
        exit 2
      fi
      nfs_server_host="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done
case "${storage_backend}" in
  nfs|local-path) ;;
  *)
    printf 'Safety stop: unsupported storage backend %s.\n' "${storage_backend}" >&2
    exit 2
    ;;
esac

if [[ "${storage_backend}" == "local-path" && -n "${nfs_server_host}" ]]; then
  printf 'Safety stop: --nfs-server-host is valid only with the NFS backend.\n' >&2
  exit 2
fi

extra_vars=("storage_backend=${storage_backend}")
if [[ -n "${nfs_server_host}" ]]; then
  extra_vars+=("nfs_server_host=${nfs_server_host}")
fi

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
  --extra-vars "${extra_vars[*]}" \
  "$@"
