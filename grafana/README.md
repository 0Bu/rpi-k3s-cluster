# [Grafana](https://grafana.com)
- [Helm Chart](https://github.com/grafana/helm-charts/tree/main/charts/grafana)

## Helm install
```
helm install grafana .
```

## Provisioned dashboards

The chart contains no dashboard JSON and creates no dashboard ConfigMap. It
only mounts the external `grafana-daikin-dashboards-manual` ConfigMap read-only
and keeps Grafana's file provider pointed at `/var/lib/grafana/dashboards/daikin`.
Dashboards in that ConfigMap are loaded into the `Daikin` folder and UI edits
remain disabled because the files are the source of truth.

Maintain the ConfigMap directly with `kubectl` server-side apply; do not add
dashboard JSON or a dashboard template back to this chart. Keep all desired
dashboard files in every apply, because `--from-file` describes the complete
data set:

```bash
kubectl create configmap grafana-daikin-dashboards-manual \
  --namespace default \
  --from-file=daikin-heating-curve-diagnosis-v2.json=/path/to/daikin-heating-curve-diagnosis-v2.json \
  --from-file=daikin-x10a-diagnostics.json=/path/to/daikin-x10a-diagnostics.json \
  --dry-run=client -o yaml \
  | kubectl apply --server-side --field-manager=grafana-dashboard-ops -f -
```

Server-side apply is intentional: it avoids duplicating the full JSON payload
in `kubectl.kubernetes.io/last-applied-configuration`. The ConfigMap must have
neither that annotation nor an Argo CD tracking annotation and must remain
below Kubernetes' 1 MiB object limit. The directory projection and Grafana's
30-second provider poll pick up later ConfigMap updates without a pod rollout.

## Helm unintall
```
helm uninstall grafana
``` 

#### [Reset admin password](https://grafana.com/docs/grafana/latest/administration/cli/#reset-admin-password)
```
grafana cli admin reset-admin-password '<password>'
```
