# [AdGuard](https://adguard.com/adguard-home.html)
- [GitHub](https://github.com/AdguardTeam/AdGuardHome)
- [Docker Hub](https://hub.docker.com/r/adguard/adguardhome)

## Storage

Live storage is a static `PersistentVolume` backed by
[`csi-driver-rclone`](../csi-driver-rclone), mounting the encrypted
`google-drive-crypt:adguard` remote (`conf` + `work` subPaths).

> ⚠️ AdGuard keeps bbolt databases (`work/data/stats.db`, `sessions.db`) and
> rewrites `AdGuardHome.yaml` via atomic rename. FUSE/object storage supports
> neither, so this carries a real data-corruption/-loss risk (see issue #2272).
> The VFS mount options in `values.yaml` mitigate but do not remove it.

### Providing the rclone credentials

The driver needs the rclone config under the `configData` key. It is the **same
plaintext** as the existing `rclone-config` secret, re-sealed under this chart's
SealedSecret name (`adguard-rclone`). Seal it before first sync:

```
# 1. Get the current rclone.conf plaintext from the cluster
kubectl -n default get secret rclone-config \
  -o jsonpath='{.data.rclone\.conf}' | base64 -d > /tmp/rclone.conf

# 2. Seal it for this chart's secret (strict scope: name + namespace)
kubeseal --raw --namespace default --name adguard-rclone < /tmp/rclone.conf

# 3. Paste the output into adguard/values.yaml -> rclone.sealedConfig
rm /tmp/rclone.conf
```

## Helm install
```
helm install adguard .
```

## Helm uninstall
```
helm uninstall adguard
```
