# Dual-stack test-cluster bootstrap

This directory builds one reproducible cluster with one server and zero or more
agents:

1. verify both SSH targets, hostnames, IPv4 addresses, stable IPv6 addresses,
   roles, peer reachability, and the absence of undeclared NFS mounts;
2. reject unsafe 6.18 kernels and hold installed Raspberry Pi kernel packages;
3. configure persistent IPv4/IPv6 forwarding without dropping the
   router-advertised IPv6 default route;
4. install pinned k3s with `pi5b` as the only server and join every declared agent;
5. grant `oleg` access through a dedicated `k3s-admin` group and install pinned k9s;
6. install Argo CD once and let the `pi5b-root` Application reconcile the
   shared cluster overlay.

Run from the `codex/pi5b-bootstrap` worktree:

```sh
make check
make bootstrap-pi5b
make status-pi5b
```

`make bootstrap-pi5b` uses NFS on the control-plane host at `/nfs`. The two
non-default storage choices must be requested explicitly:

```sh
# Keep NFS, but place the /nfs share on another declared cluster node.
./bootstrap/scripts/bootstrap-cluster.sh pi5b --nfs-server-host pi5c

# Build a disposable cluster with node-local persistence instead of NFS.
make bootstrap-pi5b-local-path
```

The single bootstrap command processes both inventory members in ordered plays:
common host preparation, server creation, agent join, GitOps installation, and
operator access. Controller-only state is written below `.state/pi5b/` and
ignored by Git. The generated kubeconfig and Grafana password stay mode `0600`
inside a mode `0700` directory.

On the server, `~/.kube/config` points to the current k3s-generated kubeconfig.
The bootstrap distributes the same protected operator kubeconfig to the agent;
both sources are `root:k3s-admin 0640`. A fresh SSH login activates the group,
then both `kgpa` and `k9s` work without `sudo` or `KUBECONFIG` exports.

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

`bootstrap/inventory/pi5b/group_vars/all.yml` selects the cluster-wide backend:

```yaml
storage_backend: nfs
persistent_storage_class: homelab-persistent
nfs_server_host: pi5b
nfs_export_path: /nfs
```

Applications reference only the stable `homelab-persistent` StorageClass and do
not need environment-specific wrapper charts. NFS is the default. Only the
explicit `--storage-backend local-path` option (or the corresponding Make target)
maps that class to the built-in k3s provisioner. With NFS, the bootstrap:

- installs `nfs-common` on every declared node;
- defaults `nfs_server_host` to the control plane, while allowing the explicit
  `--nfs-server-host` override for another declared node;
- installs and exports `/nfs` only on `nfs_server_host`;
- limits the export to the exact IPv4 addresses in the inventory;
- performs a temporary read/write mount probe from every node;
- installs the pinned GA Kubernetes NFS CSI driver; and
- maps `homelab-persistent` to dynamically provisioned NFS subdirectories.

For a one-node start, leave `k3s_agents` empty and list only `pi5b` in
`cluster_expected_nodes`. To add pi5c or further agents later, add their exact
host variables and append their names to `cluster_expected_nodes`; rerunning the
same bootstrap joins only the new nodes and expands the NFS export allow-list.

NFS removes the local-volume scheduling constraint, but it does not make storage
highly available: if the selected NFS node is offline, Pods on other nodes cannot
mount their data. Moving an existing NFS share to another node or switching an
existing PVC between `local-path` and NFS requires an explicit backup/restore.
The bootstrap refuses to mutate an existing stable StorageClass to a different
provisioner.

### Why rclone CSI is not the primary StorageClass

The existing rclone application remains the encrypted off-site backup layer.
An rclone CSI mount is useful for cloud/object content and read-mostly exchange,
but it does not share the local `/nfs` directory between nodes by itself. Doing
that would require an additional SFTP, WebDAV, or object-storage service and a
FUSE/VFS cache on every node. Those semantics are a poor fit for SQLite,
PostgreSQL, VictoriaMetrics, and other write-intensive application state. The
kernel NFS client plus the GA Kubernetes NFS CSI driver therefore remains the
primary multi-node persistent-storage path.

## Deliberate phase-3 boundaries

- LAN DNS resolves `*.pi5b.burau.dev` to `192.168.1.15` and
  `*.pi5c.burau.dev` to `192.168.1.25`. DNS remains router/AdGuard-owned and is
  validated but never modified by this bootstrap. AAAA records are likewise a
  router/DNS responsibility.
- TLS is deferred until an independent test DNS/ACME credential is available.
- The selected local-path or dedicated test-cluster NFS share never references
  the production NFS service.
- Production `192.168.1.5` is protected by the inventory and rejected as an
  accidental target.
