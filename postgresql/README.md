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

A CronJob runs daily at midnight and writes compressed dumps to the NFS volume (`postgresql-backup` PVC). The 10 most recent dumps are retained.

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

**2. Drop and recreate the database:**
```bash
kubectl exec -i postgresql-0 -n default -- psql -U postgres \
  -c "DROP DATABASE homeassistant;" \
  -c "CREATE DATABASE homeassistant OWNER homeassistant;"
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
