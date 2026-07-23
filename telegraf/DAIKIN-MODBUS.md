# Daikin Altherma — Modbus integration

Telegraf Modbus input for the heat pump (Daikin Altherma 3 R: ERGA04-08E /
ETBH12E / EKHWSP, Home Hub **EKRHH**). The registers are **mapped** from the
EKRHH installer reference guide `4P744838-1E`, section *"9.2 Modbus registers"*.

The input stays **inactive** while `daikin.enabled: false` (default) — merging
changes nothing in the running cluster. It is enabled once the heat pump is
installed and the connection to the Home Hub is verified.

Related analysis project: `~/Projects/waermepumpe-vs-gas/`
(`analyse/vergleich_run.py`).

## What exists

- `templates/configmap-daikin.yaml` — ConfigMap `telegraf-modbus-daikin` with
  `daikin.conf`. Registers mapped from the EKRHH docs, gated by
  `{{ if .Values.daikin.enabled }}`. `measurement = "daikin"` → metrics land in
  VictoriaMetrics as `daikin_<field>`.
- `values.yaml` — `daikin.enabled: false` plus commented-out activation blocks
  (env `DAIKIN_MODBUS_CONTROLLER`, `--config-directory /etc/telegraf/daikin.d`,
  volume, mountPoint).

## Addressing & data formats (EKRHH doc §9.2)

- **Offset vs. address**: the documented register *offset* is **1-based**, the
  Modbus PDU *address* is **0-based** → `address = offset − 1`. Telegraf sends
  the PDU address, so every `address` in the ConfigMap is `offset − 1`; the
  offset is in the trailing comment.
- **Register type**: telemetry lives in **input** registers (read-only, §9.2.2);
  setpoints/control in **holding** registers (R/W, §9.2.1). Telegraf only reads.
- **Data types** (§9.2, p.40) — all values are single 16-bit words, `byte_order = "AB"`:

  | Doc type | Meaning                    | Telegraf         |
  |----------|----------------------------|------------------|
  | Temp16   | signed, `/100` → °C        | `INT16`, `0.01`  |
  | Pow16    | signed, `/100` → kW        | `INT16`, `0.01`  |
  | Int16    | signed, no scaling         | `INT16`, `1.0`   |
  | Text16   | unsigned, 2 ASCII chars    | `UINT16` (raw)   |

- **Special return values** (§9.2.3) can appear on any register: `32767`
  unsupported, `32766` unavailable, `32765` wait-for-value. On a Temp16/Pow16
  these read as ≈ `327.6x` after scaling — filter them in Grafana/queries
  (e.g. drop values `> 300`).

## Mapped metrics

**All 36 input registers (§9.2.2) and all 23 holding registers (§9.2.1) are
read** — 59 fields total, in 8 request blocks.

Input registers (`daikin_*`):

- Status/operation: `abnormality`, `abnormality_code`, `abnormality_sub`,
  `circulation_pump`, `compressor`, `booster_heater`, `disinfection`, `defrost`,
  `hot_start`, `three_way_valve`, `operation_mode`, `dhw_operation`,
  `space_operation`.
- Sensors: `leaving_water_phe`, `leaving_water_buh`, `return_water`,
  `domestic_hot_water`, `outside_air`, `liquid_refrigerant`, `flow_rate` (L/min),
  `room_temperature`, `power_consumption` (kW), `dhw_upper`, `dhw_lower`.
- Setpoint limits (field-setting ranges): `limit_lwt_{heat,cool}_{main,add}_{lower,upper}`,
  `limit_room_{heat,cool}_{lower,upper}`.

Holding registers (`daikin_set_*` / `daikin_thermostat_*`, read for monitoring):
main + Add-zone leaving-water / room / DHW setpoints, operation mode, quiet mode,
weather-dependent mode + offsets, smart-grid mode, power limits, and the two
external thermostat inputs.

> Registers for features that aren't fitted return **special values** (§9.2.3),
> not Modbus errors, so reading everything is safe: the Add-zone `set_*_add` /
> `limit_*_add` registers read `32766` on single-zone systems, cooling registers
> read `32766` on heating-only setups, and `thermostat_main_input` /
> `thermostat_add_input` (holding 59/61) are **not operational** on Altherma 3 R
> indoor units (Micon ID 20002203) — expect `0`. Filter these out downstream
> (drop `> 300` after Temp16/Pow16 scaling, or `32765..32767` raw).

### ⚠️ Not available over EKRHH Modbus

The EKRHH Home Hub does **not** expose the metrics the analysis project
originally sketched. There are **no** registers for:

- cumulative **energy** counters (kWh in / heat out / DHW),
- **heat output**,
- **compressor modulation (%)** — only run on/off (`compressor`),
- **compressor start count**.

The only power/energy-related signal is the instantaneous **`power_consumption`**
(kW, input reg 51). Consequences:

- A **COP/SCOP** figure **cannot** be derived from Modbus alone (no heat-output
  register). Integrating `power_consumption` over time gives only *electrical*
  energy, not delivered heat.
- For a reliable COP/SCOP, add a calibrated **heat meter** + a dedicated
  **electricity meter** as a separate Modbus/S0 input (same pattern as FoxESS).
  See `waermepumpe-vs-gas/modbus-monitoring.md`.
- `analyse/vergleich_run.py` must be aligned to the real field names above; the
  `daikin_energy_input` / `daikin_heat_output` inputs it expects have no source.

## Activation (after commissioning)

1. **Set the controller.** In `values.yaml` uncomment `DAIKIN_MODBUS_CONTROLLER`
   and point it at the Home Hub — Modbus **TCP** `tcp://<home-hub-ip>:502`
   (port 802 for TLS) or **RTU/RS485** `file:///dev/ttyUSB0` (9600 8N1, then
   uncomment the serial params in `daikin.conf`). Confirm the `slave_id`
   (default `1`, set in the ONECTA app).
2. **Uncomment in `values.yaml`:** the env var, `--config-directory
   /etc/telegraf/daikin.d`, the volume and the mountPoint.
3. **Set `daikin.enabled: true`.**

## Testing

The `[[inputs.modbus]]` path is already proven in production (FoxESS →
`foxess_*`). For the Daikin:

1. **Render check (no cluster):**
   ```bash
   helm template telegraf ./telegraf --set daikin.enabled=true \
     -s templates/configmap-daikin.yaml
   ```
2. **Dry run against the unit** (before writing to VM): temporarily enable the
   `file` output (stdout) with `namepass = ["daikin"]` and `config.agent.debug: true`,
   then:
   ```bash
   kubectl -n default logs deploy/telegraf -f | grep -i -E "daikin|modbus"
   ```
   Expect no Modbus errors and `daikin_*` lines. `illegal data address` →
   check register/offset/register-type (holding vs input). CRC/timeout →
   check the connection (TCP IP/port or RTU baud/parity/slave_id).
3. **Arriving in VictoriaMetrics:**
   ```bash
   kubectl -n default exec deploy/grafana -- sh -c \
     "curl -s 'http://vmsingle-vm:8428/api/v1/query' --data-urlencode 'query=daikin_power_consumption' -G"
   ```

## Afterwards

- Align the metric names in `waermepumpe-vs-gas/analyse/vergleich_run.py` with
  the real fields above (and drop the unavailable energy/COP inputs, or feed them
  from the external meters).
- Create a Grafana dashboard "Wärmepumpe" analogous to `ems-esp-heizung`.
- Merge `daikin.enabled: true` to main → ArgoCD deploys the input.
