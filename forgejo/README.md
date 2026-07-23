# [Forgejo](https://forgejo.org)
- [Helm Chart](https://code.forgejo.org/forgejo-helm/forgejo-helm)

## Helm install
```
helm install forgejo .
```

## Helm uninstall
```
helm uninstall forgejo
```

## Endpoints

Web UI and Git both run over HTTPS on <https://git.burau.dev>, served by
Traefik on `192.168.1.33`. Clone URLs look like
`https://git.burau.dev/user/repo.git`.

Git over SSH is disabled (`START_SSH_SERVER=false`, `DISABLE_SSH=true`), so no
LoadBalancer IP is used and the UI does not advertise SSH clone URLs. The
subchart renders the `forgejo-ssh` Service unconditionally — it stays as a
ClusterIP with nothing listening behind it. Authenticate pushes with an access
token from *Settings → Applications*.

## Prerequisites

### NFS export

The chart runs the rootless image as uid/gid `1000`:
```bash
sudo mkdir -p /nfs/forgejo
sudo chown 1000:1000 /nfs/forgejo
```

### Database

Forgejo shares the cluster PostgreSQL (`postgresql.default.svc.cluster.local`).
The `forgejo` role and database are not created by this chart — create them once
after the `forgejo-postgresql` sealed secret has been unsealed:

```bash
kubectl -n default get secret forgejo-postgresql -o jsonpath='{.data.password}' | base64 -d | kubectl -n default exec -i postgresql-0 -- sh -c "
  read -r PW
  export PGPASSWORD=\$(cat \"\$POSTGRES_POSTGRES_PASSWORD_FILE\")
  psql -U postgres -v ON_ERROR_STOP=1 -v pw=\"\$PW\" <<'SQL'
CREATE ROLE forgejo LOGIN PASSWORD :'pw';
CREATE DATABASE forgejo OWNER forgejo;
SQL
"
```

The password is piped straight into the pod and the superuser password is read
from the file the pod already mounts, so neither ends up in the shell history.
Rotating means resealing `templates/sealed-secret.yaml` and running
`ALTER ROLE forgejo PASSWORD ...` the same way.

> The `postgresql-backup` CronJob dumps only the `homeassistant` database, so
> the `forgejo` database is **not** covered by it yet.

## Admin user

Credentials live in the `forgejo-admin` sealed secret (keys `username` and
`password`). `passwordMode: keepUpdated` means the init container syncs the
password from the secret on every pod start, so a resealed secret is enough to
reset it.

Read the current credentials:
```bash
kubectl -n default get secret forgejo-admin -o jsonpath='{.data.username}' | base64 -d; echo
kubectl -n default get secret forgejo-admin -o jsonpath='{.data.password}' | base64 -d; echo
```

## Configuration notes

- `DISABLE_REGISTRATION` and `REQUIRE_SIGNIN_VIEW` keep the instance private.
- Sessions are stored in PostgreSQL (`session.PROVIDER=db`) so logins survive
  pod restarts; the deployment uses the `Recreate` strategy because the NFS
  volume is `ReadWriteOnce`.
- Forgejo Actions is disabled — enabling it requires deploying runners.
