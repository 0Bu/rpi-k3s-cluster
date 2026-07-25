# Host scripts

Scripts that run on the cluster node itself (not in Kubernetes) and feed metrics
back into VictoriaMetrics via the node_exporter textfile collector.

## storage-roundtrip-check

Detects **silent data corruption** in the buffered read path: writes a known
random payload to disk, evicts it from the page cache, reads it back and compares
checksums.

### Why this exists

In July 2026 kernel `6.18.34+rpt-rpi-2712` on this Pi 5 returned corrupted data
for buffered reads whenever readahead was ≥ 32 KB. Every diagnostic layer was
blind to it — NVMe SMART (`media_errors 0`), NVMe self-test, PCIe AER, ext4,
`dmesg` and node_exporter all reported a healthy system. Only PostgreSQL noticed,
because it verifies its own pages (`data_checksums=on`). Before the cause was
found, a mainboard, an FFC cable and an NVMe HAT had been replaced for nothing.

This check closes that blind spot: it is the only monitor here that verifies data
actually survives the write-read cycle.

### How it works

- Streams `SIZE_MB` of random data to `TEST_DIR`, hashing it in flight — no RAM
  staging, so it also runs when the node's memory is committed to the cluster.
- Writes once, reads `ROUNDS` times. The failure mode is in the read path, and
  re-reading costs no extra flash wear.
- Evicts only its own file from the page cache (`dd iflag=nocache`) instead of a
  global `drop_caches`, which would disrupt the running cluster.
- **Validates itself**: compares the block device read counter before and after.
  A read served from cache cannot be mistaken for a clean result — that would
  make the check worse than useless.

### Metrics

| Metric | Meaning |
|---|---|
| `node_storage_roundtrip_ok` | 1 = data survived intact, 0 = corruption detected |
| `node_storage_roundtrip_valid` | 1 = reads genuinely came from disk (result is trustworthy) |
| `node_storage_roundtrip_mismatches` | number of rounds that differed |
| `node_storage_roundtrip_disk_read_bytes` | bytes actually read from the device |
| `node_storage_roundtrip_skipped` | 1 = run skipped, `reason` label says why |
| `node_storage_roundtrip_duration_seconds` | wall-clock duration |
| `node_storage_roundtrip_last_run_timestamp_seconds` | when it last ran |

Alert on `valid == 1 and ok == 0` (real corruption). Also alert on
`valid == 0` or a stale `last_run_timestamp` — an unnoticed broken check is how
this class of failure stays invisible.

### Install

```bash
sudo install -m 0755 storage-roundtrip-check.sh /usr/local/bin/
sudo install -m 0644 storage-roundtrip-check.{service,timer} /etc/systemd/system/
sudo mkdir -p /var/lib/node_exporter/textfile_collector
sudo systemctl daemon-reload
sudo systemctl enable --now storage-roundtrip-check.timer
```

Runs daily at 03:23 (±10 min), ~2 GB written per run, ~20 s. The node_exporter
side (textfile collector flag and host mount) is configured in
`victoria-metrics/values.yaml`.

### Tuning

`DEVICE`, `TEST_DIR`, `SIZE_MB`, `ROUNDS` and `OUT_DIR` are environment
overrides. Keep `SIZE_MB` at 2048: the 6.18 bug reproduced reliably at 2 GB but
never at 1 GB, so a smaller payload risks false confidence.
