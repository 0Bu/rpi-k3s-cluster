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

The `postgresql-backup` CronJob covers the `forgejo` database — it is listed in
`backup.databases` of the postgresql chart. Note that a `pg_dump` does not
include the `forgejo` role, so a restore onto a fresh cluster needs the
`CREATE ROLE` above first. See [../postgresql/README.md](../postgresql/README.md)
for the restore procedure.

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

## Actions runner

Forgejo Actions is enabled and served by a single runner (`forgejo-runner`
Deployment). k3s runs containerd, so there is no host docker socket to share —
jobs get their container backend from a privileged `dind` sidecar that listens
on `127.0.0.1:2375` inside the pod only.

Runner and server share a 40-character hex secret (`forgejo-runner` sealed
secret). The runner derives its `.runner` file from that secret on every start,
so it needs no persistent volume and re-registration is idempotent.

**Labels live on the runner side**, in `runner.labels` of `values.yaml`, which
renders into the `forgejo-runner` ConfigMap. The daemon reports them to the
server on every start and overwrites whatever is stored there — registering
server-side with `--labels` alone is not enough, the server value gets wiped on
the next runner restart. Changing labels therefore only needs a commit; the
config checksum annotation rolls the pod automatically.

`ubuntu-latest` is mapped so workflows written for GitHub find a matching
runner. Note that `actions/*` steps resolve against `DEFAULT_ACTIONS_URL`
(`https://code.forgejo.org`), so GitHub workflows pinning actions to a GitHub
commit SHA will not resolve — use a tag, or mirror the action.

The one-off server-side registration (only needed when the shared secret
changes):

```bash
kubectl -n default get secret forgejo-runner -o jsonpath='{.data.secret}' | base64 -d | kubectl -n default exec -i deployment/forgejo -- sh -c '
  read -r S
  forgejo forgejo-cli actions register --name k3s --secret "$S"'
```

## Configuration notes

- `DISABLE_REGISTRATION` and `REQUIRE_SIGNIN_VIEW` keep the instance private.
- Sessions are stored in PostgreSQL (`session.PROVIDER=db`) so logins survive
  pod restarts; the deployment uses the `Recreate` strategy because the NFS
  volume is `ReadWriteOnce`.
- Forgejo Actions is disabled — enabling it requires deploying runners.
