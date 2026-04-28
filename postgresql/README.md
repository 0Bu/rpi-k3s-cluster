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
```
kubectl -n default exec -i postgresql-0 -- pg_dumpall -U postgres > backup.sql
```

### Restore
```
kubectl -n default exec -i postgresql-0 -- psql -U postgres < backup.sql
```
