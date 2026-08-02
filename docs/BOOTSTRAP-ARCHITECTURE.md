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
not need an agent. The k3s version, installer URL, installer SHA-256, node IP,
Pod CIDR, and Service CIDR are declarative. Each cluster gets unique network
ranges. Argo CD is a bootstrapped platform component; normal applications are
not installed imperatively.

## Phase 3: isolated GitOps application slice

The pi5b root Application may reconcile only `clusters/pi5b/argocd`. Its
AppProject permits only the `monitoring` namespace and the Grafana Community
chart repository. Grafana uses a dynamically provisioned local-path PVC. Its
hostname, persistence, resources, and chart settings live directly in the Argo
CD Application. There is no environment-specific `grafana/values.yaml` wrapper
and no NFS reference.

## Next phases

1. Move production one application at a time into `clusters/prod/argocd`, first
   by rendering and diffing without changing the live cluster.
2. Add SOPS/age or External Secrets with a separate key per cluster.
3. Add an explicit DNS and certificate layer per cluster; do not reuse prod
   wildcard credentials in disposable clusters.
4. Add a storage class contract (`local-path`, replicated, or dedicated NFS)
   and ban literal storage endpoints in reusable charts.
5. Add an image/bootstrap path for blank Pis and OpenTofu only where an
   external provider actually owns DHCP/DNS/VM resources.
