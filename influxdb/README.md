# [InfluxDB](https://www.influxdata.com/products/influxdb/)
- [Helm Chart](https://github.com/influxdata/helm-charts/tree/master/charts/influxdb2)

## Helm install
```
helm install influxdb .
```

## Helm unintall
```
helm uninstall influxdb
``` 

## Backup and Restore
### [Get operator token](https://docs.influxdata.com/influxdb/v2/reference/cli/influxd/recovery/auth/list/)

```
cd /var/lib/influxdb2
cp influxd.bolt influxd.bolt.copy
influxd recovery auth list --bolt-path influxd.bolt.copy
```

or [create new one](https://docs.influxdata.com/influxdb/v2/reference/cli/influxd/recovery/auth/create-operator/) 
  - [get organization](https://docs.influxdata.com/influxdb/v2/reference/cli/influxd/recovery/org/list/) `influxd recovery org list --bolt-path influxd.bolt.copy`
  - [get user](https://docs.influxdata.com/influxdb/v2/reference/cli/influxd/recovery/user/list/) `influxd recovery user list --bolt-path influxd.bolt.copy`

```
influxd recovery auth create-operator --org influxdata --username admin
influxd recovery auth list --bolt-path influxd.bolt.copy
```

### [Backup](https://docs.influxdata.com/influxdb/v2/reference/cli/influx/backup/)
```
mkdir -p /var/lib/influxdb2/backup
influx backup /var/lib/influxdb2/backup/ --compression none --token OPERATOR_TOKEN
```

### [Restore](https://docs.influxdata.com/influxdb/v2/reference/cli/influx/restore/)
```
influx restore /var/lib/influxdb2/backup --token OPERATOR_TOKEN
```

