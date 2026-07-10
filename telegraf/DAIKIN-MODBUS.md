# Daikin Altherma — Modbus integration (scaffold)

Prepared, **inactive** scaffold for the heat pump's Telegraf Modbus input
(Daikin Altherma 3 R: ERGA04-08E / ETBH12E / EKHWSP, Home Hub **EKRHH**).
While `daikin.enabled: false`, **nothing** is deployed — merging this PR does not
change the running cluster.

Related analysis project: `~/Projects/waermepumpe-vs-gas/` (metric names live in
`analyse/vergleich_run.py`, e.g. `daikin_energy_input`, `daikin_heat_output`).

## What already exists
- `templates/configmap-daikin.yaml` — ConfigMap `telegraf-modbus-daikin` with
  `daikin.conf` (Modbus input skeleton, registers are PLACEHOLDERS). Gated by
  `{{ if .Values.daikin.enabled }}`.
- `values.yaml` — `daikin.enabled: false` plus commented-out activation blocks
  (env `DAIKIN_MODBUS_CONTROLLER`, volume, mountPoint, `--config-directory`).

## Activation (after the heat pump is commissioned)

1. **Map the registers.** Fill the real values from the EKRHH / Daikin Modbus
   documentation into `templates/configmap-daikin.yaml` (slave_id, address, type, scale,
   byte_order, register type) and uncomment the `fields` lines. Clarify the connection:
   **Modbus TCP** (`tcp://<home-hub-ip>:502`) or **RTU/RS485** (`file:///dev/ttyUSB0` +
   baud/parity).
2. **Uncomment in values.yaml:** enable the four `# Daikin (scaffold)` blocks
   (env, `--config-directory /etc/telegraf/daikin.d`, volume, mountPoint) and set
   `DAIKIN_MODBUS_CONTROLLER`.
3. **Set `daikin.enabled: true`.**

> The Daikin only reports *estimated* energy values. For a reliable COP/SCOP figure, add a
> calibrated heat meter + a dedicated electricity meter (separate Modbus/S0 input, same
> pattern). See `waermepumpe-vs-gas/modbus-monitoring.md`.

## Testing — do the Modbus imports work?

The pattern is **already proven in production**: the FoxESS inverter runs over the same
`[[inputs.modbus]]` path (`configmap.yaml` -> VictoriaMetrics `foxess_*`). For the Daikin, verify:

1. **Check rendering (no cluster needed):**
   ```bash
   helm template telegraf ./telegraf --set daikin.enabled=true \
     -s templates/configmap-daikin.yaml
   ```
2. **Dry run against the unit** (before writing to VM): in `values.yaml` under
   `config.outputs` temporarily enable the `file` output (stdout) with `namepass = ["daikin"]`
   and `config.agent.debug: true`. Then read the pod logs:
   ```bash
   kubectl -n default logs deploy/telegraf -f | grep -i -E "daikin|modbus"
   ```
   Expected: no Modbus errors (timeouts / CRC / illegal address) and `daikin_*` lines in the log.
   On `illegal data address` -> fix register/offset/register type (holding vs input).
   On CRC/timeout -> check the connection (TCP IP/port or RTU baud/parity/slave_id).
3. **Arriving in VictoriaMetrics:**
   ```bash
   kubectl -n default exec deploy/grafana -- sh -c \
     "curl -s 'http://vmsingle-vm:8428/api/v1/query' --data-urlencode 'query=daikin_energy_input' -G"
   ```
4. **End-to-end:** in the WP project run `python3 analyse/vergleich_run.py --since 7` — the heat
   pump section now shows JAZ/COP instead of "no Modbus data yet".

## Afterwards
- Align the metric names in `waermepumpe-vs-gas/analyse/vergleich_run.py` with the real fields.
- Create a Grafana dashboard "Wärmepumpe" analogous to `ems-esp-heizung`.
- Merge `daikin.enabled: true` to main -> ArgoCD deploys the input.
