# Meross thermostat MQTT archive

`templates/configmap-meross.yaml` archives the raw publisher view required by
`0Bu/daikin-altherma-esp32#288`.

## Contract

- MQTT scope: `meross-thermostat-bot/mts200b/+/state`
- measurement: `meross_thermostat`
- stable tags: `device_id`, `model`, `topic`, `source`
- fields: `current_temperature_c`, `target_temperature_c`, `enabled`, `active`
- timestamp: the original RFC3339 `thermostat.read_at`, rounded to the agent's whole-second
  precision; Telegraf arrival time is deliberately not substituted
- state encoding: `enabled` and `active` are integer `1`/`0` after the converter

The UUID from the payload/topic is the device identity. Pod name, mDNS instance,
host address, preset, HVAC mode, and mutable display labels are not tags, keeping
cardinality bounded. Missing current or target values reject the whole raw metric
because both JSON-v2 fields are required.

The firmware-accepted view is archived from the dedicated
`daikin-altherma-esp32/heating_curve` input and appears under measurement
`daikin_heating_curve` as:

- `room_temperature_c`, `room_setpoint_c`, `room_error_k`
- `room_temperature_valid`, `room_setpoint_valid`, `room_control_eligible`
- `room_source_unix_s`, `room_age_s`, `room_reason_code`
- `room_calibration_k` (fixed `0`)

This intentionally gives two queryable histories: raw `meross_thermostat_*` says
what the local poller emitted; `daikin_heating_curve_room_*` says what the firmware
accepted at heating-curve snapshot time. The technical heartbeat deliberately no
longer carries room or heating-curve fields.

The complete nested-field and null-handling contract is documented in
[`DAIKIN-HEATING-CURVE-MQTT.md`](DAIKIN-HEATING-CURVE-MQTT.md).

## Verification

Run the pinned parser fixture:

```sh
telegraf/tests/verify-meross-parser.sh
```

The test asserts the exact `read_at` second as metric time, stable identity, both temperatures, and
numeric `enabled`/`active` output. Then render the chart:

```sh
helm dependency build telegraf
helm lint telegraf
helm template telegraf telegraf
```

After Argo CD reports `Synced` and `Healthy`, verify both views in VictoriaMetrics:

```promql
meross_thermostat_current_temperature_c{device_id="<uuid>"}
meross_thermostat_target_temperature_c{device_id="<uuid>"}
daikin_heating_curve_room_control_eligible{device="daikin-altherma-esp32"}
daikin_heating_curve_room_reason_code{device="daikin-altherma-esp32"}
```
