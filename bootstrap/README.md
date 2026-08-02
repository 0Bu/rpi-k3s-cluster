# Test-cluster bootstrap

This directory implements the first reproducible, isolated cluster slice:

1. verify the SSH target exactly matches the selected cluster inventory;
2. reject unsafe 6.18 kernels and NFS mounts, then hold installed Pi kernel packages;
3. install pinned k3s and Argo CD versions;
4. grant `oleg` access through a dedicated `k3s-admin` group and install pinned k9s;
5. create only a random local Grafana admin secret;
6. let the cluster root Argo CD Application reconcile only its own overlay.

Run from the `codex/pi5b-bootstrap` worktree:

```sh
make check
make bootstrap-pi5b
make bootstrap-pi5c
make status-pi5b
make status-pi5c
```

Controller-only state is written below `.state/<cluster>/` and ignored by Git. The
generated kubeconfig and Grafana password stay mode `0600`/inside a mode `0700`
directory.

On the Pi, `~/.kube/config` points to the current k3s-generated kubeconfig. k3s
keeps that source at `root:k3s-admin 0640`, so certificate rotation is picked up
without copying credentials again. An existing user kubeconfig is preserved once
as `~/.kube/config.pre-<cluster>-bootstrap`. A fresh SSH login activates the added
group; then both `kgpa` and `k9s` work without `sudo` or `KUBECONFIG` exports.

## Deliberate phase-3 boundaries

- LAN DNS resolves `*.pi5b.burau.dev` to `192.168.1.15` and
  `*.pi5c.burau.dev` to `192.168.1.25`; DNS remains router/AdGuard-owned and is
  only validated, never changed, by this bootstrap.
- TLS is deferred until an independent test DNS/ACME credential is available.
- `local-path` is intentionally used; test workloads never mount prod NFS.
- Production `192.168.1.5` and the other test cluster are protected by each
  inventory and rejected as accidental targets.
