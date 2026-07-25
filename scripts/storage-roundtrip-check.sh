#!/bin/bash
# Storage round-trip integrity check -> node_exporter textfile collector.
#
# Writes known random data from RAM to disk, evicts it from the page cache and
# reads it back. A mismatch means the buffered read path silently returned wrong
# data — a failure class that SMART, PCIe AER, ext4 and dmesg are all blind to.
#
# Motivation: in July 2026 kernel 6.18.34 on a Pi 5 corrupted buffered reads
# (readahead >= 32 KB) with zero errors reported anywhere. Only PostgreSQL
# noticed, via its own data checksums. See scripts/README.md.
#
# The check validates itself: it compares the block device's read counter before
# and after, so a read served from cache cannot be mistaken for a clean result.
#
# Usage: storage-roundtrip-check.sh [device]     (default: nvme0n1)

set -uo pipefail

DEVICE="${1:-${DEVICE:-nvme0n1}}"
TEST_DIR="${TEST_DIR:-/var/tmp}"
SIZE_MB="${SIZE_MB:-2048}"
ROUNDS="${ROUNDS:-2}"
OUT_DIR="${OUT_DIR:-/var/lib/node_exporter/textfile_collector}"

OUT="${OUT_DIR}/storage_roundtrip.prom"
DST="${TEST_DIR}/.roundtrip-dst.$$"
STAT="/sys/block/${DEVICE}/stat"

cleanup() { rm -f "$DST"; }
trap cleanup EXIT INT TERM

# Sectors read by the device so far (field 3 of /sys/block/*/stat, 512 B units).
disk_read_bytes() { awk '{print $3 * 512}' "$STAT" 2>/dev/null || echo 0; }

# Emit metrics atomically — node_exporter must never see a half-written file.
emit() {
    local ok="$1" valid="$2" mismatches="$3" disk_bytes="$4" duration="$5" skip="$6"
    local now; now="$(date +%s)"
    mkdir -p "$OUT_DIR"
    cat > "${OUT}.tmp" <<EOF
# HELP node_storage_roundtrip_ok Buffered write-read cycle returned identical data (1 = ok, 0 = corruption detected).
# TYPE node_storage_roundtrip_ok gauge
node_storage_roundtrip_ok{device="${DEVICE}"} ${ok}
# HELP node_storage_roundtrip_valid Check was conclusive: reads really came from disk, not from cache (1 = trustworthy).
# TYPE node_storage_roundtrip_valid gauge
node_storage_roundtrip_valid{device="${DEVICE}"} ${valid}
# HELP node_storage_roundtrip_mismatches Number of rounds whose checksum differed from the source.
# TYPE node_storage_roundtrip_mismatches gauge
node_storage_roundtrip_mismatches{device="${DEVICE}"} ${mismatches}
# HELP node_storage_roundtrip_rounds Rounds executed in the last run.
# TYPE node_storage_roundtrip_rounds gauge
node_storage_roundtrip_rounds{device="${DEVICE}"} ${ROUNDS}
# HELP node_storage_roundtrip_bytes Payload size per round in bytes.
# TYPE node_storage_roundtrip_bytes gauge
node_storage_roundtrip_bytes{device="${DEVICE}"} $((SIZE_MB * 1024 * 1024))
# HELP node_storage_roundtrip_disk_read_bytes Bytes actually read from the device during verification.
# TYPE node_storage_roundtrip_disk_read_bytes gauge
node_storage_roundtrip_disk_read_bytes{device="${DEVICE}"} ${disk_bytes}
# HELP node_storage_roundtrip_skipped Run was skipped because preconditions were not met (1 = skipped).
# TYPE node_storage_roundtrip_skipped gauge
node_storage_roundtrip_skipped{device="${DEVICE}",reason="${skip}"} $([ -n "$skip" ] && echo 1 || echo 0)
# HELP node_storage_roundtrip_duration_seconds Wall-clock duration of the last run.
# TYPE node_storage_roundtrip_duration_seconds gauge
node_storage_roundtrip_duration_seconds{device="${DEVICE}"} ${duration}
# HELP node_storage_roundtrip_last_run_timestamp_seconds Unix timestamp of the last run.
# TYPE node_storage_roundtrip_last_run_timestamp_seconds gauge
node_storage_roundtrip_last_run_timestamp_seconds{device="${DEVICE}"} ${now}
EOF
    mv "${OUT}.tmp" "$OUT"
}

start="$(date +%s)"

[ -e "$STAT" ] || { emit 0 0 0 0 0 "no_such_device"; exit 1; }

avail_disk_mb=$(df -Pm "$TEST_DIR" | awk 'NR==2 {print $4}')
if [ "${avail_disk_mb:-0}" -lt $((SIZE_MB + 1024)) ]; then
    emit 0 0 0 0 $(( $(date +%s) - start )) "low_disk"; exit 0
fi

# Stream the payload straight to disk while hashing it in flight: no RAM staging,
# so the check also runs on a node whose memory is committed to the cluster. The
# hash covers what was handed to the kernel, so a corrupted *write* is caught too.
src_sum="$(head -c "${SIZE_MB}M" /dev/urandom | tee "$DST" | md5sum | awk '{print $1}')"
sync
if [ ! -s "$DST" ]; then
    emit 0 0 0 0 $(( $(date +%s) - start )) "source_write_failed"; exit 1
fi

mismatches=0
disk_bytes_total=0

# Write once, read repeatedly: the failure mode this guards against is in the
# read path, and re-reading costs no extra flash wear.
for _ in $(seq 1 "$ROUNDS"); do
    # Drop just this file from the page cache — far less disruptive than a global
    # drop_caches on a node that is also running the cluster.
    dd if="$DST" iflag=nocache count=0 status=none 2>/dev/null

    before="$(disk_read_bytes)"
    dst_sum="$(md5sum "$DST" | awk '{print $1}')"
    after="$(disk_read_bytes)"
    disk_bytes_total=$((disk_bytes_total + after - before))

    [ "$dst_sum" = "$src_sum" ] || mismatches=$((mismatches + 1))
done

# Verify the reads were genuine: at least half the payload must have come off the
# device. Otherwise the cache was not evicted and a "clean" result proves nothing.
expected=$((SIZE_MB * 1024 * 1024 * ROUNDS / 2))
valid=$([ "$disk_bytes_total" -ge "$expected" ] && echo 1 || echo 0)
ok=$([ "$mismatches" -eq 0 ] && echo 1 || echo 0)

emit "$ok" "$valid" "$mismatches" "$disk_bytes_total" $(( $(date +%s) - start )) ""
