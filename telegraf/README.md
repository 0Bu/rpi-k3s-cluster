# [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/)
- [Helm Chart](https://github.com/influxdata/helm-charts/tree/master/charts/telegraf)

## Helm install
```
helm upgrade -i --dependency-update telegraf . --set token=ABCDE
```

## Helm upgrade
```
helm upgrade -i telegraf . --reuse-values
```

## Helm unintall
```
helm uninstall telegraf
``` 
