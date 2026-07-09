# [rclone](https://rclone.org)

Encrypted backup to [Google Drive](https://rclone.org/drive/).

### Local installation

```bash
brew install rclone
```

### Configuration

```bash
rclone config
```

**Create remote `google-drive`:**

```
n  → New remote
name: google-drive
type: 18  (drive)
client_id: <your-client-id>       # leave empty to use rclone's shared app
client_secret: <your-secret>       # leave empty to use rclone's shared app
scope: 1  (drive – full access)
root_folder_id: (leave empty)
service_account_file: (leave empty)
Edit advanced config: n
Use auto config: y  → browser opens, authorize your Google account
Configure as shared drive: n
```

**Create remote `google-drive-crypt` (encryption):**

```
n  → New remote
name: google-drive-crypt
type: 16  (crypt)
remote: google-drive:k3s-backup          # subdirectory in Google Drive
filename_encryption: 1  (standard)
directory_name_encryption: true
Password or pass phrase:           → enter a strong password (stored obfuscated)
Password or pass phrase 2 (salt):  → enter a second password
```

**Verify the configuration:**

```bash
rclone config show
# Expected output: both remotes [google-drive] and [google-drive-crypt] visible

rclone lsd google-drive-crypt:
# Lists existing backup directories (empty on first run)
```

### Seal the rclone config

```bash
kubectl create secret generic rclone-config \
  --from-file=rclone.conf=$HOME/.config/rclone/rclone.conf \
  --dry-run=client -o json \
  | kubeseal --format json
```

## Restore

### Prerequisites

```bash
rclone config show google-drive-crypt
```

### Restore a single volume

```bash
rclone sync google-drive-crypt:home-assistant /nfs/home-assistant \
  --progress \
  --transfers 4
```

## Monitoring

The CronJob pushes per-volume status metrics to VictoriaMetrics after every run:

| Metric | Meaning |
| --- | --- |
| `rclone_backup_success{volume}` | `1` on success, `0` on failure of the last run |
| `rclone_backup_last_success_timestamp_seconds{volume}` | Unix time of the last successful backup |

Import [`dashboards/rclone-backup.json`](dashboards/rclone-backup.json) into Grafana
(**Dashboards → New → Import**) and pick the VictoriaMetrics/Prometheus data source
when prompted.

`vmalert`/`alertmanager` are disabled in this cluster, so there is no active
notification path. Once one is enabled, alert on:

```promql
# a volume has not been backed up successfully for > 26h
time() - max by (volume) (rclone_backup_last_success_timestamp_seconds) > 93600
# or the last run failed
min by (volume) (rclone_backup_success) == 0
```
