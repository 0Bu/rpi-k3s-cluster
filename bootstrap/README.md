# Dual-stack test-cluster bootstrap

This directory builds one reproducible cluster with one server and zero or more
agents:

1. verify both SSH targets, hostnames, IPv4 addresses, stable IPv6 addresses,
   roles, peer reachability, and the absence of undeclared NFS mounts;
2. reject unsafe 6.18 kernels and hold installed Raspberry Pi kernel packages;
3. configure persistent IPv4/IPv6 forwarding without dropping the
   router-advertised IPv6 default route;
4. install pinned k3s with the inventory's control plane as the only server and
   join every declared agent;
5. grant `oleg` access through a dedicated `k3s-admin` group and install pinned k9s;
6. install Argo CD once, register a cluster-scoped read-only SSH deploy key,
   and let the `<cluster>-root` Application reconcile its overlay from the
   separate private desired-state repository.

Run from the `codex/pi5b-bootstrap` worktree:

```sh
make check
make bootstrap-pi5c
make status-pi5c
```

`make bootstrap-pi5c` builds the one-node pi5c test cluster and uses NFS on its
control-plane host at `/nfs`. The two
non-default storage choices must be requested explicitly:

```sh
# Keep NFS, but place the /nfs share on another declared cluster node.
./bootstrap/scripts/bootstrap-cluster.sh pi5b --nfs-server-host pi5c

# Build a disposable cluster with node-local persistence instead of NFS.
make bootstrap-pi5c-local-path
```

The single bootstrap command processes all selected inventory members in ordered
plays: common host preparation, server creation, optional agent joins, GitOps
installation, and operator access. Controller-only state is written below
`.state/<cluster>/` and
ignored by Git. The generated kubeconfig, Grafana break-glass password, Authentik
bootstrap password, and `oleg` password stay mode `0600` inside a mode `0700`
directory. The GitOps deploy-key pair is stored there as
`gitops-repo-ssh-key{,.pub}`. The bootstrap verifies through the authenticated
GitHub CLI that `0Bu/rpi-k3s-cluster-apps` is private, registers only the public
half as a read-only deploy key, and writes the private half only to Argo CD's
repository Secret.

## Public/private GitOps boundary

This public repository owns host preparation, k3s, Argo CD installation,
storage, reusable charts, and validators. Real AppProjects, Applications,
ApplicationSets, environment values, and encrypted Git secrets live in the
private `0Bu/rpi-k3s-cluster-apps` repository. Plaintext secrets remain forbidden
in both repositories; bootstrap-generated values stay in `.state/<cluster>` and
Kubernetes Secrets.

The controller must have `gh` authenticated as an account allowed to manage the
private repository. A separate deploy key is generated for every cluster and
registered without write access. Losing `.state/<cluster>/gitops-repo-ssh-key`
requires removing that cluster's named deploy key in GitHub before bootstrap can
create a replacement; a mismatched key is rejected rather than overwritten.

## Grafana authentication on pi5c

The private pi5c overlay deploys the pinned official Authentik chart as a separate
Argo CD Application at `https://auth.pi5c.burau.dev`. Its mounted blueprint creates
the Grafana OIDC provider, the `oleg` user, and application-scoped `Grafana
Admins`, `Grafana Editors`, and `Grafana Viewers` entitlements. Only users with
one of those entitlements can sign in; `oleg` receives `Grafana Admins` during
initial provisioning.

The bootstrap owns the Authentik, PostgreSQL, operator, and OAuth credentials;
Helm values contain only Kubernetes Secret references. The initial credentials
are available only on the controller:

```text
.state/pi5c/authentik-oleg-password
.state/pi5c/authentik-akadmin-password
```

Grafana starts the Authentik flow automatically. Its local admin remains a
break-glass account and can be reached with
`https://grafana.pi5c.burau.dev/login?disableAutoLogin=true`.

The private overlay also owns a cluster-specific cert-manager Application and a
Cloudflare token encrypted for that cluster's Sealed Secrets controller. One
wildcard certificate (`*.pi5c.burau.dev`) terminates at the shared Traefik
Gateway; cross-namespace HTTPRoutes expose Authentik and Grafana without copying
the private key into application namespaces. Another disposable cluster uses
the same pattern with its own SealedSecret and wildcard, for example
`*.pi5b.burau.dev`. The bundled PostgreSQL chart remains test-only; production
should use a separately managed PostgreSQL deployment.

On the server, `~/.kube/config` points to the current k3s-generated kubeconfig.
The bootstrap distributes the same protected operator kubeconfig to the agent;
both sources are `root:k3s-admin 0640`. It replaces only k3s's expected
`kubectl -> k3s` symlink with the checksum-pinned standalone kubectl matching
the Kubernetes minor version, so operator commands do not try to read the
root-only k3s server configuration. A fresh SSH login activates the group, then
both `kgpa` and `k9s` work without warnings, `sudo`, or `KUBECONFIG` exports.

## Address plan

The directly connected LAN prefix and the overlay networks must not overlap:

| Purpose | IPv4 | IPv6 |
| --- | --- | --- |
| pi5b node | `192.168.1.15` | `fd7c:3b4a:5f1d::5b/64` |
| pi5c node | `192.168.1.25` | `fd7c:3b4a:5f1d::5c/64` |
| Pods | `10.52.0.0/16` | `fd7c:3b4a:5f1d:42::/64` |
| Services | `10.53.0.0/16` | `fd7c:3b4a:5f1d:43::/112` |

The `/64` requested for the hosts is already directly routed on `eth0`; using
that same network for Flannel would route Pod traffic onto the LAN. The separate
`:42` and `:43` subnets retain the same ULA global ID while avoiding that conflict.
ULA Pod egress is masqueraded with `flannel-ipv6-masq`.

## Storage selection and node growth

Each `bootstrap/inventory/<cluster>/group_vars/all.yml` selects the cluster-wide
backend:

```yaml
storage_backend: nfs
persistent_storage_class: homelab-persistent
nfs_export_path: /nfs
```

Applications reference only the stable `homelab-persistent` StorageClass and do
not need environment-specific wrapper charts. NFS is the default. Only the
explicit `--storage-backend local-path` option (or the corresponding Make target)
maps that class to the built-in k3s provisioner. With NFS, the bootstrap:

- installs `nfs-common` on every declared node;
- derives `nfs_server_host` from `cluster_server_host`, while allowing the
  explicit `--nfs-server-host` override for another declared node;
- installs and exports `/nfs` only on `nfs_server_host`;
- limits the export to the exact IPv4 addresses in the inventory;
- performs a temporary read/write mount probe from every node;
- installs the pinned GA Kubernetes NFS CSI driver; and
- maps `homelab-persistent` to dynamically provisioned NFS subdirectories; and
- disables and removes k3s's packaged `local-storage` component. It remains
  enabled only when `--storage-backend local-path` was selected explicitly.

For a one-node start, leave `k3s_agents` empty and list only the control-plane
host in `cluster_expected_nodes`. To add agents later, add their exact host
variables and append their names to `cluster_expected_nodes`; rerunning the same
bootstrap joins only the new nodes and expands the NFS export allow-list. The
pi5c inventory is the executable example: pi5c is both the sole control plane
and, by default, the NFS server at `/nfs`.

NFS removes the local-volume scheduling constraint, but it does not make storage
highly available: if the selected NFS node is offline, Pods on other nodes cannot
mount their data. Moving an existing NFS share to another node or switching an
existing PVC between `local-path` and NFS requires an explicit backup/restore.
The bootstrap refuses to mutate an existing stable StorageClass to a different
provisioner.

## Deliberate phase-3 boundaries

- LAN DNS resolves `*.pi5b.burau.dev` to `192.168.1.15` and
  `*.pi5c.burau.dev` to `192.168.1.25`. DNS remains router/AdGuard-owned and is
  validated but never modified by this bootstrap. AAAA records are likewise a
  router/DNS responsibility.
- TLS credentials are cluster-bound SealedSecrets in the private GitOps overlay;
  no plaintext Cloudflare token or certificate private key is committed.
- The selected local-path or dedicated test-cluster NFS share never references
  the production NFS service.
- Production `192.168.1.5` is protected by the inventory and rejected as an
  accidental target.
