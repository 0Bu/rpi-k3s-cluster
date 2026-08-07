# Daikin heating-curve MQTT archive

The Daikin ESP32 publishes accepted room evidence and its read-only heating-curve diagnosis as a
separate, non-retained domain snapshot. Telegraf archives it independently from the technical
heartbeat.

## Contract

- MQTT topic: `daikin-altherma-esp32/heating_curve`
- firmware schema: numeric top-level `schema_version` (currently `1`)
- VictoriaMetrics measurement: `daikin_heating_curve`
- stable tag: `device="daikin-altherma-esp32"`
- metric timestamp: Telegraf receive time
- cadence: approximately 10 seconds while the firmware's X10A publication gate is open
- retention: the MQTT document is not retained; a restarted consumer waits for the next live snapshot

The legacy Telegraf JSON parser joins nested object paths with `_`. Representative fields are:

- `room_temperature_c`, `room_setpoint_c`, `room_error_k`
- `room_temperature_valid`, `room_setpoint_valid`, `room_control_eligible`
- `room_source_unix_s`, `room_age_s`, `room_reason_code`
- `room_counters_messages`, `room_counters_errors`, `room_counters_rejections`
- `diagnosis_method_version`, `diagnosis_state`, `diagnosis_reason`
- `diagnosis_gates_plant_known`, `diagnosis_gates_plant_active`
- `diagnosis_gates_heating_mode_known`, `diagnosis_gates_heating_mode_active`
- `diagnosis_room_evidence_current_error_k`, `diagnosis_room_evidence_source_unix_s`
- `diagnosis_last_sample_room_error_k`, `diagnosis_last_sample_unix_s`,
  `diagnosis_last_sample_sequence`
- `diagnosis_counters_evaluations`, `diagnosis_counters_samples`,
  `diagnosis_counters_holds`, `diagnosis_counters_blocks`

Firmware validity and gate booleans are encoded as numeric `1`/`0`, so the numeric-only archive
keeps them. JSON `null` means unavailable evidence and produces no field for that snapshot; it must
never be interpreted as a measured zero. `room.source_id` is descriptive text and is deliberately
not promoted to a tag, keeping series identity bounded. Source and sample Unix timestamps remain
numeric fields; they do not replace Telegraf's receive time.

## Verification

Run the pinned parser fixture and chart checks:

```sh
telegraf/tests/verify-daikin-heating-curve-parser.sh
helm dependency build telegraf
helm lint telegraf
helm template telegraf telegraf
```

The fixture verifies nested flattening, numeric booleans, the fixed device tag, and omission of
unavailable (`null`) evidence. After Argo CD reports `Synced` and `Healthy`, verify the ready
Telegraf pod and real series:

```promql
daikin_heating_curve_schema_version{device="daikin-altherma-esp32"}
daikin_heating_curve_room_control_eligible{device="daikin-altherma-esp32"}
daikin_heating_curve_diagnosis_state{device="daikin-altherma-esp32"}
daikin_heating_curve_diagnosis_counters_evaluations{device="daikin-altherma-esp32"}
```

Room- or heating-curve-prefixed fields under `daikin_heartbeat_*` indicate a producer or deployment
regression; the heartbeat contract is board/link health only.
