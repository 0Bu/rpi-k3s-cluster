# [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/)
- [Helm Chart](https://github.com/influxdata/helm-charts/tree/master/charts/telegraf)

## Helm install
```
helm upgrade -i --dependency-update telegraf .
```

## Helm upgrade
```
helm upgrade -i telegraf . --reuse-values
```

## Helm unintall
```
helm uninstall telegraf
``` 

## Create sealed secret
```
kubectl create secret generic telegraf-influxdb-token --dry-run=client --from-literal=INFLUXDB_TOKEN=<...> -oyaml | kubeseal -oyaml
```

