# Reproducible homelab architecture: phases 1-3

## Ownership model

| Layer | Source of truth | Responsibility |
| --- | --- | --- |
| Host | `bootstrap/inventory/<cluster>` | identity, kernel safety, base OS contract |
| Kubernetes | `bootstrap/playbooks` | pinned k3s and first Argo CD installation |
| Cluster | `clusters/<cluster>/argocd` | AppProjects, Applications, Helm values |
| Secrets | bootstrap initially; later SOPS/age | cluster-scoped ciphertext, never shared plaintext |

## Phase 1: repository and safety contracts

The legacy top-level charts remain untouched for production compatibility.
New work goes into cluster-owned overlays. Every inventory defines its exact
hostname/address and a deny list for protected systems. A bootstrap refuses a
host with a mismatching identity, an NFS mount, or a kernel in the known-bad
6.18.0 through 6.18.37 range.

## Phase 2: reproducible host and k3s bootstrap

Ansible is the controller because the Raspberry Pis already expose SSH and do
not need an agent. The k3s and k9s versions, download URLs and SHA-256 values,
node IP, Pod CIDR, and Service CIDR are declarative. Each cluster gets unique
network ranges. A dedicated local group can read the rotating k3s kubeconfig;
the operator's `~/.kube/config` is a symlink rather than a stale credential copy.
The validated hostname is made cloud-init-persistent and locally resolvable so
`sudo` and system services do not depend on external DNS.
Argo CD is a bootstrapped platform component; normal applications are not
installed imperatively.

## Phase 3: isolated GitOps application slice

Each test-cluster root Application may reconcile only its own
`clusters/<cluster>/argocd` directory. Its AppProject permits only the
`monitoring` namespace and the Grafana Community chart repository. Grafana uses
the bootstrap-owned `homelab-persistent` StorageClass. NFS on a declared
cluster node at `/nfs` is the default; local-path must be selected explicitly
for a disposable cluster. Its hostname, persistence, resources, and chart
settings live directly in the Argo CD Application. There is no environment-
specific `grafana/values.yaml` wrapper and no literal storage endpoint in the
application.

## Next phases

1. Move production one application at a time into `clusters/prod/argocd`, first
   by rendering and diffing without changing the live cluster.
2. Add SOPS/age or External Secrets with a separate key per cluster.
3. Add an explicit DNS and certificate layer per cluster; do not reuse prod
   wildcard credentials in disposable clusters.
4. Migrate production workloads to the stable StorageClass one at a time with
   an explicit backup, restore, and rollback test.
5. Add an image/bootstrap path for blank Pis and OpenTofu only where an
   external provider actually owns DHCP/DNS/VM resources.
