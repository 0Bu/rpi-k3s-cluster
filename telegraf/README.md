# [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/)
- [GitHub](https://github.com/influxdata/telegraf)
- [Documentation](https://docs.influxdata.com/telegraf/)
- [Helm Chart](https://github.com/influxdata/helm-charts/tree/master/charts/telegraf)

## Modbus integrations

- [FoxESS H3 Smart](FOXESS-MODBUS.md) — prioritized read-only polling of power,
  grid/BMS health, energy totals and inventory registers.
- [Daikin Home Hub](DAIKIN-MODBUS.md) — prioritized read-only heat-pump polling.

## Daikin forecast history

The MQTT consumer stores the retained
`daikin-altherma-esp32/weather/openmeteo/forecast` document as measurement
`daikin_weather_openmeteo_forecast` in VictoriaMetrics. Numeric payload keys become series such as:

- `daikin_weather_openmeteo_forecast_outdoor_mean_2h_c`
- `daikin_weather_openmeteo_forecast_solar_energy_2h_wh_m2`
- `daikin_weather_openmeteo_forecast_available` and
  `daikin_weather_openmeteo_forecast_fresh`
- `daikin_weather_openmeteo_forecast_fetched_unix_s`,
  `daikin_weather_openmeteo_forecast_forecast_start_unix_s`, and
  `daikin_weather_openmeteo_forecast_valid_until_unix_s`

Only the stable `provider` and `model` values tag these numeric series. The categorical snapshot
context (`state`, `reason`, `freshness_reason`, and `error`) is stored separately on
`daikin_weather_openmeteo_forecast_info_schema`. This prevents changing status labels from forking
every numeric forecast series and leaving an obsolete label set behind.
Telegraf's receive time is the metric timestamp; the source and forecast timestamps remain fields,
so a retained replay cannot silently rewrite when the historian actually observed the snapshot.
Analysis must require both `available == 1` and `fresh == 1`. An unavailable snapshot may still
carry the last figures for forensic comparison and must not be interpreted as a usable forecast.

## Helm install
```
helm install telegraf .
```

## Helm unintall
```
helm uninstall telegraf
```
