# Dual-stack test-cluster bootstrap

This directory builds one reproducible two-node cluster:

1. verify both SSH targets, hostnames, IPv4 addresses, stable IPv6 addresses,
   roles, peer reachability, and the absence of NFS;
2. reject unsafe 6.18 kernels and hold installed Raspberry Pi kernel packages;
3. configure persistent IPv4/IPv6 forwarding without dropping the
   router-advertised IPv6 default route;
4. install pinned k3s with `pi5b` as the only server and join `pi5c` as an agent;
5. grant `oleg` access through a dedicated `k3s-admin` group and install pinned k9s;
6. install Argo CD once and let the `pi5b-root` Application reconcile the
   shared cluster overlay.

Run from the `codex/pi5b-bootstrap` worktree:

```sh
make check
make bootstrap-pi5b
make status-pi5b
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

## Deliberate phase-3 boundaries

- LAN DNS resolves `*.pi5b.burau.dev` to `192.168.1.15` and
  `*.pi5c.burau.dev` to `192.168.1.25`. DNS remains router/AdGuard-owned and is
  validated but never modified by this bootstrap. AAAA records are likewise a
  router/DNS responsibility.
- TLS is deferred until an independent test DNS/ACME credential is available.
- `local-path` is intentionally used; test workloads never mount prod NFS.
- Production `192.168.1.5` is protected by the inventory and rejected as an
  accidental target.
