# Postmortem: PostgreSQL backups failing — silent data corruption on pi5a

**Date:** 2026-07-22 to 2026-07-26
**Impact:** Nightly PostgreSQL backups broken for 2 days; Home Assistant database
partly unreadable; ~114 rows of sensor history lost
**Root cause:** Kernel bug ([raspberrypi/linux#7496](https://github.com/raspberrypi/linux/issues/7496)) — no hardware was ever faulty
**Cost of misdiagnosis:** A mainboard, an FFC cable and an NVMe HAT replaced for nothing

---

## Summary

The `postgresql-backup` CronJob stopped producing dumps. What looked like database
corruption turned out to be a kernel regression in `6.18.34+rpt-rpi-2712`: reads
from the NVMe returned *valid data from the wrong buffer*. Every diagnostic layer
we had — SMART, NVMe self-test, PCIe AER, ext4, dmesg, node_exporter — reported a
perfectly healthy system throughout. Only PostgreSQL noticed, because it verifies
its own pages with checksums.

The investigation took four days and replaced three pieces of hardware before
arriving at software. The single test that would have pointed the right way from
the start — comparing buffered reads against `O_DIRECT` — took two minutes when it
was finally run.

---

## Impact

| | |
|---|---|
| Backups | No valid dump 2026-07-21 and 2026-07-22 (last good: 07-20 23:44) |
| Home Assistant | Read errors on `states` / `statistics`; recorder partly failing |
| Permanent data loss | ~114 rows in `states` (0.003%), plus ~3 pages of `statistics` destroyed by our own premature repair |
| Off-site backups | **Unaffected** — all Google Drive copies verified intact |
| Downtime | None; the cluster kept running throughout |

---

## Timeline

| When | What |
|---|---|
| **07-20 11:00** | `postgresql-0` terminates uncleanly (exit 255). In hindsight: a symptom, not a cause. |
| **07-20 23:44** | Last successful dump. |
| **07-21 18:53** | First `invalid page in block …` in the PostgreSQL log. |
| **07-21 22:00** | Backup job dies mid-dump, leaves a 45 MB `.tmp` fragment. |
| **07-22** | Investigation starts. Corrupt pages appear to *move* between reads. In-place repair with `VACUUM FULL` + `zero_damaged_pages` — **this destroyed 3 healthy pages**. Backups work again for a few hours. |
| **07-23** | Corruption returns on freshly written files. All local dumps now fail `gunzip -t`. Hardware suspected. PCIe Gen 3 → Gen 2: error rate drops ~10×, but does not stop. |
| **07-24** | SMART clean, self-test passes. `O_DIRECT` reads found bit-stable while buffered reads fail — first hard evidence pointing away from the drive. pi5b (same SSD model, older kernel) tests clean. |
| **07-25** | FFC cable replaced — no change. Mainboard replaced — no change. NVMe HAT replaced — no change. Readahead dependency discovered; kernel compared against pi5b; downgrade to 6.12.75 → **30 GB with zero errors**. |
| **07-26** | Web research identifies the exact upstream bug, already fixed. |

---

## How we got there

### The misleading symptom

The corrupt blocks *moved*. A scan found 23 damaged pages in `statistics`;
`VACUUM FULL` then zeroed three entirely different ones, and the original 23 read
back fine. Pages that failed in the log read cleanly minutes later.

This was read consistently and wrongly as flaky hardware. It is in fact the
signature of a corrupted *transport*: the data on disk was fine all along.

### The most expensive mistake

`cp` + `drop_caches` + `md5sum` was treated as a hardware test. It is not — it
exercises only the buffered read path. Every conclusion drawn from it about the
SSD, the cable, the HAT and the board was unfounded.

A second error compounded it: after the Gen 2 change, a single clean 512 MB run
was reported as "verified fixed". The error rate had merely dropped by 10×, and
the sample was far too small to detect that. The user acted on that all-clear.

### What actually cracked it

Three observations, in order of decisiveness:

1. **`O_DIRECT` reads were always correct.** Writing buffered and reading with
   `O_DIRECT` returned the exact source checksum — proving the bytes on disk were
   intact and only the buffered read path was lying.
2. **A hard readahead threshold.** `blockdev --setra` ≤ 32 sectors (16 KB) was
   clean; ≥ 64 sectors (32 KB) failed every time. Hardware faults do not have
   crisp thresholds like that.
3. **A working reference system.** pi5b runs the *same* SSD model with kernel
   6.12.75 and never failed. Comparing `/proc/cmdline` and `uname -r` between the
   two should have happened on day one; it happened on day four.

### Ruled out along the way

RAM (tmpfs source checksum stayed stable throughout), NVMe SMART
(`media_errors: 0`), NVMe self-test (passed), PCIe AER (zero errors), ext4
(`clean` — it only checksums metadata, never file contents), undervoltage
(`throttled=0x0`), temperature, HMB (disabling it changed nothing), and
`iommu_dma_numa_policy`. The nightly OOM kills in dmesg were AdGuardHome hitting
its own 128 MB limit — an unrelated red herring.

---

## Root cause

Upstream commit `f0887e2a52d4` ("nvme-pci: create common sgl unmapping helper",
6.18 merge window) swapped the `sg_list` and `sge` arguments in the call to
`nvme_free_sgls()` from `nvme_unmap_data()`. Both parameters have the same type,
so the compiler did not object.

The result is that the wrong DMA region gets unmapped. On systems using an
IOMMU/SWIOTLB — the Pi 5 among them — the IOVA of a still-active request is
released and reused, so another request lands at the same device address. The
bytes that come back are real, valid data, just from the wrong buffer. Raspberry
Pi maintainers demonstrated this with `bgrep`: the corrupted 64-byte groups were
verbatim copies from other 8 KB-aligned offsets of the same file.

**The trigger is the drive's SGL support, not readahead.** Drives advertising
`sgls != 0` take the broken path:

```
$ sudo nvme id-ctrl /dev/nvme0 | grep sgls
sgls : 0x70001          # our BIWIN — affected
```

Drives reporting `sgls : 0` (e.g. Crucial P5 Plus) are immune, which is why the
bug went largely unnoticed elsewhere.

The readahead threshold we found is a *side effect*: the rpi-2712 kernel uses
16 KB pages, so readahead ≤ 16 KB yields exactly one physical segment and
`nvme_pci_setup_data()` takes a PRP shortcut that bypasses the broken SGL path.
**`blockdev --setra 32` is therefore not a safe workaround.**

Fixed upstream by `a54afbc8a213` ("nvme-pci: DMA unmap the correct regions in
nvme_free_sgls"), first released in v6.19-rc8, cherry-picked by Raspberry Pi into
`rpi-6.18.y` ([PR #7500](https://github.com/raspberrypi/linux/pull/7500)) and
shipped via `rpi-update` from kernel 6.18.38. **Not backported to stable 6.18.y,
and as of 2026-07-25 not in the apt repository** — 6.18.34 is still the newest
package there.

---

## Resolution

1. **Kernel downgraded to 6.12.75** (already installed locally). Boot images in
   `/boot/firmware/` swapped, originals kept as `*.bak-6.18.34`, and
   `linux-image-rpi-2712` / `-v8` put on `apt-mark hold` so an upgrade cannot
   silently reintroduce it.
2. **Verified:** 15 rounds × 2 GB = 30 GB with default readahead, zero mismatches.
   Under 6.18.34 the same test failed 100% of the time.
3. **`states` repaired:** exactly 2 permanently damaged pages (26172, 45176 of
   74,924) cleared with `zero_damaged_pages` — legitimate this time, because the
   transport path had been proven clean first and the damage was stable rather
   than moving. Cost: ~114 rows of 4.34 M (0.003%).
4. **PCIe left at Gen 2** — `dtparam=pciex1_gen=3` stays out regardless; Gen 3 is
   not validated on the Pi 5.

To return to 6.18 later: `sudo rpi-update` (≥ 6.18.38) or wait for an apt package
≥ 6.18.38+rpt — then re-run the 2 GB verification before trusting it.

---

## What was actually lost

Nothing that mattered, and less than feared. The Google Drive copies were intact
the whole time — ironically *because* `rclone sync` compares size and mtime rather
than checksums, so the corrupted-looking local files were never uploaded over the
good ones. The local dumps were never damaged either; they simply could not be
read correctly while the bug was active.

The only real loss was self-inflicted: ~3 pages of `statistics`, zeroed by a
repair aimed at phantom corruption.

---

## Lessons

1. **Test buffered vs. `O_DIRECT` first.** It separates kernel/page-cache from
   device/medium in two minutes and would have saved three hardware swaps.
2. **Moving errors are never the medium.** Same file, different checksum each
   read, means transport or software — not flash.
3. **`cp` + `drop_caches` is not a hardware test.** It measures one path only.
4. **One clean run proves nothing.** Verification needs multiple GB *and* repeated
   rounds, checking exit codes and file sizes. A 10× reduced error rate looks
   exactly like a fix at small sample sizes.
5. **Compare against a working peer early.** `uname -r` and `/proc/cmdline` between
   pi5a and pi5b was the decisive clue and cost nothing.
6. **Search for known bugs before blaming hardware.** The issue had been open,
   diagnosed and fixed by upstream maintainers a week before we started swapping
   parts.
7. **Never run `zero_damaged_pages` before the transport path is cleared.** It
   destroys healthy data when the corruption is not real.

---

## Follow-up

**Done:** a [storage round-trip check](../scripts/README.md) now runs nightly and
exports `node_storage_roundtrip_*`. It writes a known payload, evicts it from the
page cache, reads it back and compares — the only monitor here that verifies data
actually survives the round trip. It validates itself against the block device
read counter, so a read served from cache cannot masquerade as a clean result.

**Done:** alerting was enabled (vmalert + Alertmanager → Home Assistant, visible in
Grafana). It had been switched off because nothing consumed it; a metric nobody
looks at is not a safeguard. Alerts cover real corruption *and* the check going
stale or inconclusive.

**Open:** pi5b still runs 6.12.75 and must not be upgraded to 6.18.34 either. Both
nodes should move to ≥ 6.18.38 once it reaches apt.
