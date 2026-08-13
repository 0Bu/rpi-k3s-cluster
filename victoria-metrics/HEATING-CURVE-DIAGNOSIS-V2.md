# Heating-curve diagnosis v2

This is the versioned VictoriaMetrics contract for
`0Bu/daikin-altherma-esp32#294`. It evaluates the firmware's write-free
diagnosis method 2; it is not a controller and must not turn room kelvin into a
leaving-water-temperature correction.

## Evidence boundaries

- Select the domain topic `daikin-altherma-esp32/heating_curve` explicitly.
  Older heartbeat/controller series have different semantics and must not be
  joined into a v2 verdict.
- A diagnosis sample is the raw `target - actual` room error. Positive is too
  cold, negative too warm.
- Missing or stale evidence is absent, never zero. `plant_inactive` and Cooling
  are normal `HOLD` states, not failures.
- The reference room has its own thermostat and valves. Its closed inner loop
  can hide an overly high curve, so D1 never stands alone: read D2 clipping and
  D4 thermostat demand beside it.
- The plant-side outdoor series can freeze while the compressor is off. For
  the reference installation it may be joined only to confirmed heating
  evidence. #441 WP4 owns a future source/provenance improvement in firmware.

## Recorded inputs

| Series | Meaning |
|---|---|
| `daikin:heating_curve:eligible_heating` | Positive conjunction of armed, plant-known/active and mode-known/Heating gates; absent otherwise |
| `daikin:heating_curve:sample_room_error_k` | D1 room-error event with at most one 30-minute cadence window of statistical weight |
| `daikin:heating_curve:clipped_at_35c` | D2 0/1 sample during eligible heating; 35 C is this installation's current main-zone minimum |
| `daikin:heating_curve:samples_24h` | D3 recorded diagnosis samples in the rolling day |
| `daikin:heating_curve:expected_eligible_windows_24h` | D3 eligible time expressed as expected half-hour windows |
| `daikin:heating_curve:room_degree_hours_outside_0_5k_24h` | D4 integrated absolute room error beyond +/-0.5 K, excluding unavailable input |

The three raw Meross `meross_thermostat_active` series remain the D4 zone-demand
witness. Preserve `device_id`; do not average the three zones into a single
boolean before calculating each zone's duty cycle.

## D1-D4 report contract

### D1 - directional curve bias

Group `daikin:heating_curve:sample_room_error_k` by the plant-side outdoor
temperature and the archived two-hour solar-energy context. Initial reporting
bins are deliberately coarse because the sampler produces at most two events
per hour:

- outdoor temperature: `<0`, `0..<5`, `5..<10`, `10..<15`, `>=15` C;
- solar energy over the next two complete hours: `<50`, `50..<200`, `>=200`
  Wh/m2.

A cell may be described only with at least 24 samples spanning at least three
different local dates. An outdoor band receives a directional verdict only
with at least 48 total samples spanning at least seven dates and with no
opposite-sign median among solar cells that individually pass coverage. Below
those bars report `insufficient coverage`, not `balanced`.

Report median, interquartile range, sample count and distinct dates. `balanced`
means the median lies inside +/-0.25 K and both quartiles inside +/-0.5 K. This
is a room-bias statement, never a numeric LWT setting recommendation.

### D2 - clipping share

For a selected season or outdoor band:

```promql
avg_over_time(daikin:heating_curve:clipped_at_35c[30d])
```

State the eligible heating duration beside the percentage. A high share bounds
what lowering the weather-dependent curve can achieve; it does not by itself
license changing the installer minimum.

### D3 - coverage and failure reasons

Compare `samples_24h` with `expected_eligible_windows_24h`. Do not calculate a
ratio when expected windows are zero. Use raw
`daikin_heating_curve_diagnosis_reason` and the hold/block counter increases to
explain missing coverage. Idle and Cooling holds stay separate from blocks.

### D4 - comfort and demand context

Report the rolling degree-hours series and, per Meross `device_id`:

```promql
avg_over_time(meross_thermostat_active[24h])
```

The duty cycle is corroborating evidence: low room error with valves rarely
requesting heat can indicate that the inner loop is masking a high curve.

## Alerts

- `DaikinHeatingCurveRoomInputIneligible` requires every plant/heating gate to
  be positively true and then waits 15 minutes for the room source to recover.
- `DaikinHeatingCurveDiagnosisBlocked` watches armed diagnosis state 4 for 15
  minutes, independently of the specific missing witness.

Neither alert fires for the evaluator's normal idle/Cooling `HOLD` state. The
existing `DaikinEsp32NoData` alert remains responsible for a completely absent
domain stream.
