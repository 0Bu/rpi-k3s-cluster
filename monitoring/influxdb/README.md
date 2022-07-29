# [InfluxDB](https://www.influxdata.com/products/influxdb/)
- [Helm Chart](https://github.com/influxdata/helm-charts/tree/master/charts/influxdb2)

## [Recover user credentials after reinstallation](https://docs.influxdata.com/influxdb/v2.3/reference/cli/influxd/recovery/user/update/)

### Prepation
Shutdown influxd
```
cp /nfs/influxdb/influxd.bolt /nfs/influxdb/influxd.bolt.copy
```

### Reseting admin password
```
influxd recovery user update --username admin --password ABCDE --bolt-path /var/lib/influxdb2/influxd.bolt.copy
```

### Final
```
mv /nfs/influxdb/influxd.bolt.copy /nfs/influxdb/influxd.bolt
```

## Helm install
```
helm upgrade -i --dependency-update influxdb . 
```

## Helm unintall
```
helm uninstall influxdb
``` 
