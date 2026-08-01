# FoxESS H3 Smart — Modbus integration

Telegraf reads the FoxESS H3 Smart through the cluster-local evcc Modbus proxy
at `tcp://evcc:502`, logical device/slave ID `247`. evcc owns and serializes the
physical inverter connection; Telegraf must not open five independent direct
connections to the inverter. The mapping follows FoxESS *Modbus definition
V1.05.04.00*, tables 3-3 through 3-6. All configured registers are documented
`RO`; Telegraf uses FC03 only and has no write path.

## Polling priorities

The original input read all 57 fields every 10 seconds. VictoriaMetrics showed
that power-flow values changed almost every sample, while totals and inventory
values changed orders of magnitude less often. The configuration therefore
uses five independent inputs:

| Priority | Interval | Fields | Purpose |
|----------|----------|--------|---------|
| P0 safety | 10 s | 12 | Inverter/BMS status, off-grid state and alarm/fault bitfields |
| P1 power | 10 s | 24 | CT1, inverter/load phase power, PV1 and inverter-side battery data |
| P2 health | 30 s | 16 | Grid quality, inverter temperature and BMS operating data |
| P3 energy | 60 s | 8 | Monotonic lifetime energy counters |
| P4 inventory | 5 min | 4 | Export availability, SOH, FCC and design energy |

All previous 57 metric names remain unchanged. Seven safety metrics were added:

- `foxess_inverter_status_3` — protocol register 39065/39066, including the
  off-grid bit.
- `foxess_battery_bms_fault_1` through `_fault_6` — registers 37626–37631.

Every request explicitly sets `optimization = "none"`, so Telegraf never fills
gaps with reserved or otherwise unselected registers. Per-input
`collection_jitter` spreads the Modbus traffic.

## Expected load

Based on Telegraf's current request partitioning, the tiered configuration keeps
the fast operational signals while reducing the steady-state load approximately
as follows:

| Measure | Before | Tiered |
|---------|-------:|-------:|
| Existing field samples/day | 492,480 | 309,312 |
| All field samples/day | 492,480 | 369,792 |
| Modbus transactions/day | 241,920 | 130,752 |
| Holding-register words/day | 768,960 | 571,680 |

The seven additional P0 fields intentionally trade a small amount of the saving
for better fault coverage. Even with them included, field samples fall by about
25%, transactions by 46%, and read register words by 26%.

## Reload behavior

The upstream Telegraf chart hashes only its primary ConfigMap. The values file
therefore carries the SHA-256 of the rendered FoxESS `modbus.conf` as a pod
annotation, which forces a rollout when the mapping changes. Telegraf also runs
with `--watch-config poll --watch-interval 10s` so projected ConfigMap updates
are reloaded if an annotation update is accidentally missed.

When editing `templates/configmap.yaml`, update
`telegraf.podAnnotations.checksum/foxess-modbus-config` to the SHA-256 of the
rendered `modbus.conf`.

## Validation

Before merging:

1. `helm lint ./telegraf`
2. Render and parse `modbus.conf` with Telegraf's config checker.
3. Assert five inputs, 13 request definitions and 64 unique fields.
4. Compare the 57 established field names with the previous revision.
5. Run all five inputs read-only against `tcp://evcc:502`; a direct parallel
   test against the inverter is invalid because of its TCP-client limit.

After ArgoCD sync:

1. Confirm the application revision and a new Telegraf pod.
2. Check startup logs for aliases `foxess_safety`, `foxess_power`,
   `foxess_health`, `foxess_energy` and `foxess_inventory` without Modbus errors.
3. Confirm all 64 metrics in VictoriaMetrics and verify their sample cadence.
