# [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/)
- [GitHub](https://github.com/influxdata/telegraf)
- [Documentation](https://docs.influxdata.com/telegraf/)
- [Helm Chart](https://github.com/influxdata/helm-charts/tree/master/charts/telegraf)

## Helm install
```
helm install telegraf .
```

## Helm unintall
```
helm uninstall telegraf
``` 

## Create sealed secret
```
kubectl create secret generic telegraf-influxdb-token --dry-run=client -oyaml --from-literal=INFLUXDB_TOKEN=... | kubeseal -oyaml
```

