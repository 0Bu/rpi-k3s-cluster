# [PostgreSQL](https://www.postgresql.org)
- [Helm Chart](https://github.com/bitnami/charts/tree/main/bitnami/postgresql)

## Helm install
```
helm install postgresql .
```

## Helm uninstall
```
helm uninstall postgresql
```

## Home Assistant Migration

`configuration.yaml`:
```yaml
recorder:
  db_url: postgresql://homeassistant:<password>@192.168.1.26/homeassistant
```

## Backup and Restore

### Backup

A CronJob runs daily at midnight and writes compressed dumps to the NFS volume (`postgresql-backup` PVC), one per database listed in `backup.databases` (`homeassistant`, `forgejo`). Files are named `pg_dump_<database>_<timestamp>.sql.gz` and the 10 most recent dumps **per database** are retained.

Add a database by appending it to `backup.databases` in `values.yaml` — no other change is needed.

**Trigger a manual backup:**
```bash
kubectl create job postgresql-backup-manual --from=cronjob/postgresql-backup -n default
kubectl wait --for=condition=complete job/postgresql-backup-manual -n default --timeout=300s
```

**List available backups:**
```bash
kubectl run pg-ls --rm -i --restart=Never -n default --image=busybox \
  --overrides='{"spec":{"volumes":[{"name":"b","persistentVolumeClaim":{"claimName":"postgresql-backup"}}],"containers":[{"name":"pg-ls","image":"busybox","command":["ls","-1t","/backup"],"volumeMounts":[{"name":"b","mountPath":"/backup"}]}]}}' \
  2>/dev/null
```

### Restore

> **Warning:** This replaces all data in the `homeassistant` database. Back up the current state first if needed.

**1. Scale down Home Assistant** to close active database connections:
```bash
kubectl scale deployment home-assistant --replicas=0 -n default
kubectl wait --for=condition=available=false deployment/home-assistant -n default --timeout=60s
```

**2. Drop and recreate the database** (local `psql` needs the superuser password, which the pod already mounts as a file):
```bash
kubectl exec -i postgresql-0 -n default -- sh -c '
  PGPASSWORD=$(cat "$POSTGRES_POSTGRES_PASSWORD_FILE") psql -U postgres \
    -c "DROP DATABASE homeassistant;" \
    -c "CREATE DATABASE homeassistant OWNER homeassistant;"'
```

**3. Restore from a backup file** (replace filename as needed):
```bash
BACKUP_FILE="pg_dump_homeassistant_20260506-0000.sql.gz"

kubectl run pg-restore --rm -i --restart=Never -n default \
  --image=bitnami/postgresql:latest \
  --overrides='{
    "spec": {
      "volumes": [{"name":"b","persistentVolumeClaim":{"claimName":"postgresql-backup"}}],
      "containers": [{
        "name": "pg-restore",
        "image": "bitnami/postgresql:latest",
        "command": ["bash","-c","gunzip -c /backup/'"$BACKUP_FILE"' | psql -h postgresql -U postgres homeassistant"],
        "env": [{"name":"PGPASSWORD","valueFrom":{"secretKeyRef":{"name":"postgresql-credentials","key":"postgres-password"}}}],
        "volumeMounts": [{"name":"b","mountPath":"/backup"}]
      }]
    }
  }' 2>/dev/null
```

**4. Scale Home Assistant back up:**
```bash
kubectl scale deployment home-assistant --replicas=1 -n default
```

#### Restoring another database

The same four steps apply, with the deployment, database name, owner and backup
file swapped. For Forgejo that is `kubectl scale deployment forgejo`,
`CREATE DATABASE forgejo OWNER forgejo;` and `pg_dump_forgejo_<timestamp>.sql.gz`.
The `forgejo` role itself is not part of the dump — recreate it first if it is
missing, see [../forgejo/README.md](../forgejo/README.md).
