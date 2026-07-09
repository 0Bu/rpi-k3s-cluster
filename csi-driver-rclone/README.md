# [csi-driver-rclone](https://github.com/veloxpack/csi-driver-rclone)

CSI driver that mounts [rclone](https://rclone.org) remotes (50+ cloud/object
storage backends) as PersistentVolumes via FUSE + rclone VFS cache.

Used by `adguard`, whose volume is a static PV backed by the encrypted
Google Drive `crypt` remote — see [`adguard/`](../adguard).

> ⚠️ Cloud/object storage is **not** a POSIX filesystem (no locking, no atomic
> renames, VFS write-cache can lose data on node/pod failure). It is unsuitable
> for database-/state-backed workloads. See issue #2272 for the full analysis.

## Helm install
```
helm dependency build
helm install csi-driver-rclone .
```
