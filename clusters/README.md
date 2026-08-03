# Private cluster overlays

Real Argo CD `AppProject`, `Application`, `ApplicationSet`, cluster-specific
Helm values, and encrypted Git secrets do not belong in this public repository.
Their source of truth is the private
[`0Bu/rpi-k3s-cluster-apps`](https://github.com/0Bu/rpi-k3s-cluster-apps)
repository under `clusters/<cluster>/argocd`.

This public directory intentionally contains documentation only. The bootstrap
keeps the path contract visible in inventory while a cluster-scoped read-only
SSH deploy key grants Argo CD access to the private repository. Never add a real
overlay here as a public fallback.
