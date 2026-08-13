# [Grafana](https://grafana.com)
- [Helm Chart](https://github.com/grafana/helm-charts/tree/main/charts/grafana)

## Helm install
```
helm install grafana .
```

## Provisioned dashboards

`daikin-heating-curve-diagnosis-v2.json` is mounted read-only from a ConfigMap
and loaded by Grafana's file provider into the `Daikin` folder. It deliberately
keeps the historic `daikin-lwt-diag` UID so deployment replaces the former
manual #294 offset/saturation dashboard instead of creating a competing copy.

The dashboard uses a Prometheus-datasource variable and therefore does not pin
a cluster-specific datasource UID. Changes belong in
`dashboards/daikin-heating-curve-diagnosis-v2.json`; UI edits are disabled and
will be overwritten by provisioning.

## Helm unintall
```
helm uninstall grafana
``` 

#### [Reset admin password](https://grafana.com/docs/grafana/latest/administration/cli/#reset-admin-password)
```
grafana cli admin reset-admin-password '<password>'
```
