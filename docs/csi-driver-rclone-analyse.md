# Analyse: Einsatz von `csi-driver-rclone`

Bewertung von [veloxpack/csi-driver-rclone](https://github.com/veloxpack/csi-driver-rclone)
für den Einsatz im vorliegenden Raspberry-Pi-k3s-Cluster.

- **Stand der Analyse:** 2026-07-08
- **Untersuchte Version:** v0.4.11 (Release 2026-04-18)

---

## TL;DR – Empfehlung

> **Nicht empfohlen als allgemeine Storage-Schicht für dieses Cluster.**
>
> Die Workloads dieses Clusters sind ganz überwiegend **datenbank-/zustandsbehaftet**
> (PostgreSQL, Home-Assistant-SQLite, AdGuard, Grafana, VictoriaMetrics-TSDB, evcc).
> Genau diese Workloads sind das klassische Anti-Pattern für FUSE-gemountetes
> Cloud-/Objekt-Storage: fehlendes POSIX-Locking, keine atomaren Renames und
> potenzieller Datenverlust im VFS-Write-Cache führen zu **Datenkorruption**.
>
> Der bestehende Aufbau – **NFS für Live-Volumes + rclone-CronJob für verschlüsseltes
> Backup nach Google Drive** – löst die tatsächlichen Anforderungen bereits sauber und
> DB-konsistent. `csi-driver-rclone` löst ein Problem (live in Pods gemountete
> Cloud-Buckets), das dieses Cluster derzeit **nicht hat**, und bringt dafür einen
> privilegierten DaemonSet, spürbaren Overhead auf ARM und Korruptionsrisiken mit.
>
> **Sinnvoller Nischeneinsatz** wäre allenfalls ein *lesend* gemountetes Bucket für
> statische/append-only-Daten (Medien, Archive). Selbst dafür ist ein
> `rclone copy` per InitContainer/CronJob meist einfacher und sicherer.

---

## 1. Was ist `csi-driver-rclone`?

Ein Kubernetes **CSI-Treiber**, der [rclone](https://rclone.org) (als Go-Bibliothek,
kein externes Binary) einbindet, um über 50 Cloud-/Objekt-Storage-Backends
(Amazon S3, Google Cloud Storage, Azure Blob, Dropbox, SFTP, Google Drive …) als
**PersistentVolumes** direkt in Pods zu mounten.

| Merkmal | Ausprägung |
|---|---|
| Provisionierung | Dynamisch (StorageClass), statisch (PV) und ephemeral (Inline) |
| Architektur | Controller-`Deployment` + Node-`DaemonSet` + `CSIDriver` + `StorageClass` |
| Mount-Technik | FUSE (`fuse3` im Image) + rclone **VFS-Cache** |
| Node-Anforderung | FUSE-Support; Node-Plugin läuft **`privileged: true`** mit `SYS_ADMIN`, `hostPath` auf das Kubelet-Verzeichnis und **`mountPropagation: Bidirectional`** |
| Credentials | Kubernetes-Secrets (passt zum vorhandenen sealed-secrets-Muster) |
| Installation | Helm (`veloxpack.github.io/csi-driver-rclone` bzw. OCI-Chart) |
| Kubernetes | ≥ 1.20 |
| Images | Multi-Arch **`linux/amd64` + `linux/arm64`** (Release-Builds) |
| Reife | v0.**x** (0.4.11), Einzel-Anbieter, ~335 Stars, als „GA" beworben |

---

## 2. Ist-Zustand im Cluster (Kontext)

Aus dem Repository abgeleitet:

- **Live-Storage:** Zentraler **NFS-Server auf dem Master-Node** (`192.168.1.5`,
  Export `/nfs`). Apps binden per statischem `PersistentVolume` + `PVC`
  (`ReadWriteOnce`) auf NFS-Pfade (z. B. `evcc`, `home-assistant`, `postgresql`).
- **Backup:** `rclone`-**CronJob** (nächtlich 02:00 Europe/Berlin) mountet die
  NFS-Volumes **read-only** und `rclone sync` in ein **verschlüsseltes Google-Drive**
  (`crypt`-Remote). VictoriaMetrics wird über die Snapshot-API konsistent gesichert;
  die rclone-Config liegt als Sealed Secret.
- **Deployment:** **GitOps mit ArgoCD** (App-of-Apps), Renovate für Image-Updates.
- **Plattform:** Raspberry Pi, teils 64-bit (arm64), teils potenziell 32-bit
  (arm/v7 – siehe README-Hinweis `arm_64bit=1`).

**Kernbeobachtung:** Nahezu jede App ist DB-/zustandsbehaftet. Der bestehende Split
„lokales NFS für Live + rclone-Batch für Backup" ist bewusst und robust gewählt
(vgl. README-Notiz zur fsync-Latenz der DRAM-losen NVMe).

---

## 3. Vorteile (Pro)

| # | Vorteil | Relevanz für dieses Cluster |
|---|---|---|
| P1 | **ARM64-Images vorhanden** – Release-Builds decken `linux/arm64` ab | Läuft auf 64-bit-RPi-Nodes |
| P2 | **50+ Backends**, Secret-basierte Credentials | Passt zum sealed-secrets-Muster; S3/GDrive bereits im Einsatz |
| P3 | **GitOps-tauglich** (Helm/OCI-Chart) | Fügt sich in ArgoCD-Workflow ein |
| P4 | **Dynamische Provisionierung** via StorageClass | Pods könnten Cloud-Buckets ohne lokale Kapazität nutzen |
| P5 | **Kein externes rclone-Binary** – rclone als Go-Lib, ein Prozess | Kleinere Angriffsfläche als Sidecar-/Subprozess-Ansatz |
| P6 | **Konzeptuelle Nähe** – Cluster vertraut rclone + GDrive-crypt bereits | Geringe Einarbeitung ins rclone-Modell |
| P7 | **Ephemeral/Inline-Volumes** | Praktisch für kurzlebige Read-Zugriffe auf Buckets |

**Kurz:** Technisch sauber gebaut, GitOps- und ARM64-kompatibel, breite Backend-Auswahl.
Der Nutzen entsteht aber nur, wenn ein Workload einen **live gemounteten Cloud-Bucket**
tatsächlich braucht.

---

## 4. Nachteile & Risiken (Contra)

| # | Risiko | Schwere |
|---|---|---|
| C1 | **Cloud-/Objekt-Storage ist kein POSIX-FS** – kein File-Locking, keine atomaren Renames, keine partiellen Writes. **Datenbanken (PostgreSQL, SQLite in HA/evcc/AdGuard, Grafana, VM-TSDB) korrumpieren bzw. verweigern den Start.** | 🔴 Kritisch |
| C2 | **VFS-Write-Cache kann Datenverlust verursachen** – bei Node-/Pod-Ausfall gehen noch nicht committete Daten **ohne App-Benachrichtigung** verloren. rclone-VFS ist ausdrücklich **nicht für Kubernetes-Cluster designt.** | 🔴 Kritisch |
| C3 | **Privilegierter DaemonSet auf jedem Node** (`privileged`, `SYS_ADMIN`, `hostPath` Kubelet-Dir, bidirektionale Mount-Propagation) → deutlich größere Angriffsfläche als heutige statische NFS-PVs | 🟠 Hoch |
| C4 | **Performance auf RPi** – FUSE + VFS-Cache + Netzwerk-Roundtrips zur Cloud ⇒ hohe Latenz, CPU-Last auf dem Pi, Cache-Schreiblast auf SD/NVMe. Für DB-Workloads praktisch unbrauchbar (die README moniert bereits NVMe-fsync-Latenz – Cloud-FUSE ist um Größenordnungen schlechter) | 🟠 Hoch |
| C5 | **Nur `arm64`, kein `arm/v7`** – 32-bit-Raspberry-Pi-OS-Nodes werden nicht bedient; Node-Plugin scheduled dort nicht | 🟠 Hoch (falls 32-bit-Nodes existieren) |
| C6 | **Reife/Bus-Faktor** – v0.x, Einzel-Anbieter, ~335 Stars; jüngste Fixes wie „disable VFS reuse to prevent context canceled errors" zeigen Stabilitäts-Churn. Kein CNCF-/Community-Treiber | 🟡 Mittel |
| C7 | **Cloud-Quota/-Kosten bei Live-Mount** – Dauer-Mount = Dauer-API-Last. **Google Drive** ist als Live-Filesystem ungeeignet (Rate-Limits, 750 GB/Tag-Upload-Cap, Sperr-Risiko); **S3** verursacht Request-/Egress-Kosten | 🟡 Mittel |
| C8 | **Zusätzliche Betriebskomplexität** – Controller + DaemonSet + CSIDriver + StorageClass + RBAC + Monitoring statt eines einzelnen CronJobs | 🟡 Mittel |
| C9 | **Redundanz zum bestehenden Design** – das Backup-Problem ist bereits gelöst (nächtlicher, DB-konsistenter, verschlüsselter Sync). Der Treiber adressiert einen anderen, hier nicht vorhandenen Use-Case | 🟡 Mittel |

---

## 5. Eignung nach Workload (dieses Cluster)

| Workload | Storage-Charakter | Eignung für `csi-driver-rclone` |
|---|---|---|
| PostgreSQL | Datenbank, fsync-kritisch | ❌ **Nein** – Korruptionsgefahr (C1/C2) |
| Home Assistant | SQLite | ❌ **Nein** – SQLite auf FUSE/Objektstore = Korruption |
| AdGuard | Zustand/SQLite | ❌ **Nein** |
| Grafana | SQLite/State | ❌ **Nein** |
| VictoriaMetrics | TSDB, mmap/Locking | ❌ **Nein** |
| evcc | State-File/DB | ❌ **Nein** |
| Backup-Zielspeicher | Batch, append/rewrite | ⚠️ Möglich, aber CronJob-`sync` ist **einfacher & sicherer** |
| Statische/Medien-Daten (read-only) | append-only / immutable | ✅ **Einzig plausibler Fall** – lesend gemountetes Bucket |

---

## 6. ARM/Raspberry-Pi-spezifische Bewertung

- ✅ **arm64** wird in Release-Images gebaut → auf 64-bit-Nodes lauffähig.
- ❌ **arm/v7 (32-bit)** wird **nicht** publiziert. Falls Nodes noch 32-bit-Raspberry-Pi-OS
  fahren, läuft das Node-Plugin dort nicht (`nodeSelector`/Scheduling schlägt fehl).
- ⚠️ **Performance/Verschleiß:** FUSE-Mount + VFS-Cache erzeugen CPU-Last und
  Cache-Schreib-I/O auf dem lokalen Datenträger des Pi. In einem Homelab mit
  DRAM-loser NVMe (bereits als Latenz-Engpass dokumentiert) ist das ein
  zusätzlicher, unerwünschter Faktor.

---

## 7. Wann wäre der Einsatz vertretbar?

Nur wenn ein **künftiger** Workload folgende Merkmale erfüllt:

1. **Read-mostly / append-only / immutable** – keine In-place-Updates, keine DB.
2. Toleriert Latenz und eventuell fehlende POSIX-Semantik.
3. Braucht den Cloud-Bucket **live im Pod** (nicht nur als periodische Kopie).

Beispiele: read-only Auslieferung großer Medien-/Asset-Bibliotheken aus einem
S3-Bucket, Mounten eines Archivs zum einmaligen Restore.

Selbst dann sind **einfachere Alternativen** meist vorzuziehen:

- **InitContainer `rclone copy`** in ein `emptyDir`/lokales PV beim Pod-Start.
- **Bestehender rclone-CronJob** (Batch-Sync) – bereits vorhanden, DB-konsistent.
- Für Objekt-nativen Zugriff: die App direkt gegen die **S3-API** sprechen lassen
  (kein Filesystem-Layer nötig).

---

## 8. Fazit

| Kriterium | Bewertung |
|---|---|
| Technische Qualität des Treibers | Gut (sauberer CSI-Aufbau, Multi-Arch, GitOps-fähig) |
| Passung zu den **Workloads dieses Clusters** | **Schlecht** – fast alles ist DB/State |
| Sicherheits-/Betriebsprofil | Verschlechterung (privilegierter DaemonSet) |
| Mehrwert gegenüber Ist-Zustand | Gering – Backup ist bereits gelöst |
| **Gesamtempfehlung** | **Nicht umsetzen** als generelle Storage-Schicht; nur als eng begrenztes Read-only-Bucket erwägen |

**Bestehendes Setup beibehalten:** NFS für Live-PVs, rclone-CronJob für
verschlüsseltes Backup. `csi-driver-rclone` erst dann evaluieren, wenn ein konkreter,
read-mostly Cloud-Bucket-Use-Case entsteht – und ihn vorher isoliert (eigener
Namespace, Testvolume) auf ARM verifizieren.

---

## Quellen

- [veloxpack/csi-driver-rclone – GitHub](https://github.com/veloxpack/csi-driver-rclone)
- [Installations-Doku](https://github.com/veloxpack/csi-driver-rclone/blob/main/docs/install-rclone-csi-driver.md)
- [Veloxpack-Doku – Driver Parameters / Quick Start](https://www.veloxpack.io/docs/csi-driver-rclone)
- [DeepWiki – csi-driver-rclone](https://deepwiki.com/veloxpack/csi-driver-rclone)
- [rclone-Forum – CSI driver for rclone](https://forum.rclone.org/t/csi-driver-for-rclone/52847)
- [rclone VFS-Cache – Doku/Warnhinweise](https://rclone.org/commands/rclone_mount/#vfs-file-caching)
- Release-Build-Plattformen: `.github/workflows/docker-ghcr-release.yaml` (`linux/amd64,linux/arm64`)
- Node-DaemonSet-SecurityContext: `charts/templates/csi-rclone-node.yaml`
