# Reproducible homelab architecture: phases 1-3

## Ownership model

| Layer | Source of truth | Responsibility |
| --- | --- | --- |
| Host | `bootstrap/inventory/<cluster>` | identity, kernel safety, base OS contract |
| Kubernetes | `bootstrap/playbooks` | pinned k3s and first Argo CD installation |
| Cluster | private `rpi-k3s-cluster-apps/clusters/<cluster>/argocd` | AppProjects, Applications, Helm values |
| Secrets | private encrypted Git manifests or bootstrap `.state` | cluster-scoped ciphertext, never shared plaintext |

## Phase 1: repository and safety contracts

The legacy top-level charts remain untouched for production compatibility.
New application work goes into private cluster-owned overlays. Every inventory defines its exact
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
`clusters/<cluster>/argocd` directory in the private
`0Bu/rpi-k3s-cluster-apps` repository. Argo CD receives a distinct read-only SSH
deploy key for each cluster; the private key exists only in controller state and
the cluster's repository Secret. Its AppProject permits only the
`monitoring` and `authentik` namespaces and only the Grafana Community and
official Authentik chart repositories. Grafana and Authentik's test PostgreSQL
use the bootstrap-owned `homelab-persistent` StorageClass. NFS on the declared
control-plane host at `/nfs` is the default; another declared NFS node or
local-path must be selected explicitly. Hostnames, persistence, resources, OIDC
configuration, and the Authentik blueprint live directly in the Argo CD
Applications. Secrets remain bootstrap-owned references. There are no
environment-specific chart wrappers and no literal storage endpoint in either
application.

## Next phases

1. Move production one application at a time into the private
   `clusters/prod/argocd`, first by rendering and diffing without changing the
   live cluster. Keep the legacy public configuration until pi5a has switched
   repositories and every application is verified.
2. Add SOPS/age or External Secrets with a separate key per cluster.
3. Add an explicit DNS and certificate layer per cluster; do not reuse prod
   wildcard credentials in disposable clusters.
4. Migrate production workloads to the stable StorageClass one at a time with
   an explicit backup, restore, and rollback test.
5. Add an image/bootstrap path for blank Pis and OpenTofu only where an
   external provider actually owns DHCP/DNS/VM resources.
