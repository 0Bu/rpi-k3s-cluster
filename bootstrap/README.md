# pi5b bootstrap

This directory implements the first reproducible, isolated cluster slice:

1. verify the SSH target is exactly `pi5b` at `192.168.1.15`;
2. reject unsafe 6.18 kernels and NFS mounts, then hold installed Pi kernel packages;
3. install pinned k3s and Argo CD versions;
4. grant `oleg` access through a dedicated `k3s-admin` group and install pinned k9s;
5. create only a random local Grafana admin secret;
6. let the `pi5b-root` Argo CD Application reconcile `clusters/pi5b/argocd`.

Run from the `codex/pi5b-bootstrap` worktree:

```sh
make check
make bootstrap-pi5b
make status-pi5b
```

Controller-only state is written below `.state/pi5b/` and ignored by Git. The
generated kubeconfig and Grafana password stay mode `0600`/inside a mode `0700`
directory.

On the Pi, `~/.kube/config` points to the current k3s-generated kubeconfig. k3s
keeps that source at `root:k3s-admin 0640`, so certificate rotation is picked up
without copying credentials again. An existing user kubeconfig is preserved once
as `~/.kube/config.pre-pi5b-bootstrap`. A fresh SSH login activates the added
group; then both `kgpa` and `k9s` work without `sudo` or `KUBECONFIG` exports.

## Deliberate phase-3 boundaries

- `grafana.pi5b.burau.dev` currently resolves to the production ingress address,
  so DNS is not changed by this bootstrap. Validate with `curl --resolve` until
  the DNS cutover is explicitly authorized.
- TLS is deferred until an independent test DNS/ACME credential is available.
- `local-path` is intentionally used; test workloads never mount prod NFS.
- `192.168.1.5` and `192.168.1.25` are protected and rejected as targets.
