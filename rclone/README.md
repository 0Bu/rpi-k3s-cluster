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
