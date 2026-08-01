# [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/)
- [GitHub](https://github.com/influxdata/telegraf)
- [Documentation](https://docs.influxdata.com/telegraf/)
- [Helm Chart](https://github.com/influxdata/helm-charts/tree/master/charts/telegraf)

## Modbus integrations

- [FoxESS H3 Smart](FOXESS-MODBUS.md) — prioritized read-only polling of power,
  grid/BMS health, energy totals and inventory registers.
- [Daikin Home Hub](DAIKIN-MODBUS.md) — prioritized read-only heat-pump polling.

## Helm install
```
helm install telegraf .
```

## Helm unintall
```
helm uninstall telegraf
```
