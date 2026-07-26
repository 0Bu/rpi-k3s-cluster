# Postmortem: Ausfall der PostgreSQL-Backups — stille Datenkorruption auf pi5a

**Zeitraum:** 22.07.2026 bis 26.07.2026
**Auswirkung:** Nächtliche PostgreSQL-Backups zwei Tage lang defekt; Home-Assistant-Datenbank teilweise unlesbar; ~114 Zeilen Sensorhistorie verloren
**Ursache:** Kernel-Bug ([raspberrypi/linux#7496](https://github.com/raspberrypi/linux/issues/7496)) — keine Hardware war jemals defekt
**Preis der Fehldiagnose:** Ein Mainboard, ein Flachbandkabel und ein NVMe-HAT umsonst getauscht

---

## Zusammenfassung

Der CronJob `postgresql-backup` lieferte keine Dumps mehr. Was wie eine
Datenbankkorruption aussah, war eine Kernel-Regression in
`6.18.34+rpt-rpi-2712`: Lesevorgänge von der NVMe lieferten *gültige Daten aus dem
falschen Puffer*. Sämtliche Diagnoseschichten — SMART, NVMe-Self-Test, PCIe-AER,
ext4, dmesg, node_exporter — meldeten durchgehend ein kerngesundes System. Nur
PostgreSQL bemerkte den Fehler, weil es seine Datenseiten mit eigenen Prüfsummen
absichert.

Die Untersuchung dauerte vier Tage und kostete drei Hardwareteile, bevor sie bei
Software ankam. Der eine Test, der von Anfang an in die richtige Richtung gewiesen
hätte — gepufferte Lesevorgänge gegen `O_DIRECT` zu vergleichen — dauerte zwei
Minuten, als er endlich lief.

---

## Auswirkung

| | |
|---|---|
| Backups | Kein gültiger Dump am 21. und 22.07. (letzter guter: 20.07., 23:44) |
| Home Assistant | Lesefehler auf `states` / `statistics`; Recorder teilweise gestört |
| Dauerhafter Datenverlust | ~114 Zeilen in `states` (0,003 %), dazu ~3 Seiten `statistics`, die unsere eigene voreilige Reparatur zerstört hat |
| Off-site-Backups | **Nicht betroffen** — alle Google-Drive-Kopien verifiziert intakt |
| Ausfallzeit | Keine; das Cluster lief durchgehend |

---

## Zeitverlauf

| Wann | Was |
|---|---|
| **20.07., 11:00** | `postgresql-0` bricht unsauber ab (Exit 255). Rückblickend ein Symptom, keine Ursache. |
| **20.07., 23:44** | Letzter erfolgreicher Dump. |
| **21.07., 18:53** | Erstes `invalid page in block …` im PostgreSQL-Log. |
| **21.07., 22:00** | Backup-Job stirbt mitten im Dump, hinterlässt ein 45-MB-`.tmp`-Fragment. |
| **22.07.** | Untersuchung beginnt. Die korrupten Seiten scheinen zwischen Lesevorgängen zu *wandern*. In-Place-Reparatur mit `VACUUM FULL` + `zero_damaged_pages` — **dabei werden 3 gesunde Seiten zerstört**. Backups laufen für ein paar Stunden wieder. |
| **23.07.** | Korruption kehrt auf frisch geschriebenen Dateien zurück. Alle lokalen Dumps scheitern nun an `gunzip -t`. Hardwareverdacht. PCIe Gen 3 → Gen 2: Fehlerrate sinkt um ~10×, hört aber nicht auf. |
| **24.07.** | SMART sauber, Self-Test bestanden. `O_DIRECT`-Lesevorgänge erweisen sich als bit-stabil, während gepufferte scheitern — der erste harte Hinweis weg vom Laufwerk. pi5b (gleiches SSD-Modell, älterer Kernel) testet fehlerfrei. |
| **25.07.** | Flachbandkabel getauscht — keine Änderung. Mainboard getauscht — keine Änderung. NVMe-HAT getauscht — keine Änderung. Readahead-Abhängigkeit entdeckt, Kernel mit pi5b verglichen, Downgrade auf 6.12.75 → **30 GB ohne einen einzigen Fehler**. |
| **26.07.** | Web-Recherche identifiziert den exakten Upstream-Bug — längst gemeldet und behoben. |

---

## Der Weg zur Lösung

### Das irreführende Symptom

Die korrupten Blöcke *wanderten*. Ein Scan fand 23 beschädigte Seiten in
`statistics`; `VACUUM FULL` nullte anschließend drei völlig andere, und die
ursprünglichen 23 lasen sich wieder sauber. Seiten, die im Log fehlschlugen,
waren Minuten später fehlerfrei.

Das wurde konsequent — und falsch — als sporadischer Hardwaredefekt gedeutet.
Tatsächlich ist es die Signatur eines korrupten *Transports*: Die Daten auf der
Platte waren die ganze Zeit in Ordnung.

### Der teuerste Fehler

`cp` + `drop_caches` + `md5sum` wurde als Hardwaretest behandelt. Das ist er
nicht — er beansprucht ausschließlich den gepufferten Lesepfad. Jede daraus
gezogene Schlussfolgerung über SSD, Kabel, HAT und Board war unbegründet.

Ein zweiter Fehler verschärfte das: Nach der Umstellung auf Gen 2 wurde ein
einzelner sauberer 512-MB-Durchlauf als „verifiziert behoben" gemeldet. Die
Fehlerrate war lediglich um den Faktor 10 gefallen, und die Stichprobe war viel zu
klein, um das zu erkennen. Der Nutzer hat auf diese Entwarnung hin gehandelt.

### Was den Fall tatsächlich knackte

Drei Beobachtungen, nach Aussagekraft geordnet:

1. **`O_DIRECT`-Lesevorgänge waren immer korrekt.** Gepuffert schreiben und mit
   `O_DIRECT` lesen lieferte exakt die Quell-Prüfsumme — Beweis, dass die Bytes
   auf der Platte intakt waren und nur der gepufferte Lesepfad log.
2. **Eine harte Readahead-Schwelle.** `blockdev --setra` ≤ 32 Sektoren (16 KB) war
   sauber, ≥ 64 Sektoren (32 KB) scheiterte jedes Mal. Hardwaredefekte haben keine
   derart scharfen Schwellen.
3. **Ein funktionierendes Referenzsystem.** pi5b läuft mit demselben SSD-Modell
   unter Kernel 6.12.75 und versagte nie. Der Vergleich von `/proc/cmdline` und
   `uname -r` zwischen beiden hätte am ersten Tag stattfinden müssen — er fand am
   vierten statt.

### Unterwegs ausgeschlossen

RAM (die tmpfs-Quelle behielt durchgehend ihre Prüfsumme), NVMe-SMART
(`media_errors: 0`), NVMe-Self-Test (bestanden), PCIe-AER (null Fehler), ext4
(`clean` — prüft ohnehin nur Metadaten, nie Dateiinhalte), Unterspannung
(`throttled=0x0`), Temperatur, HMB (Abschalten änderte nichts) und
`iommu_dma_numa_policy`. Die nächtlichen OOM-Kills im dmesg waren AdGuardHome an
seinem eigenen 128-MB-Limit — eine unabhängige falsche Fährte.

---

## Ursache

Der Upstream-Commit `f0887e2a52d4` („nvme-pci: create common sgl unmapping
helper", 6.18-Merge-Window) vertauschte die Argumente `sg_list` und `sge` beim
Aufruf von `nvme_free_sgls()` aus `nvme_unmap_data()`. Beide Parameter haben
denselben Typ, der Compiler beanstandete es daher nicht.

Die Folge: Es wird die falsche DMA-Region freigegeben. Auf Systemen mit
IOMMU/SWIOTLB — der Pi 5 gehört dazu — wird die IOVA einer noch aktiven Anfrage
freigegeben und wiederverwendet, sodass eine andere Anfrage auf derselben
Geräteadresse landet. Die zurückgelieferten Bytes sind echte, gültige Daten, nur
eben aus dem falschen Puffer. Die Raspberry-Pi-Maintainer haben das mit `bgrep`
belegt: Die korrupten 64-Byte-Gruppen waren wortwörtliche Kopien von anderen,
8-KB-ausgerichteten Offsets derselben Datei.

**Auslöser ist der SGL-Support des Laufwerks, nicht der Readahead.** Laufwerke,
die `sgls != 0` melden, nehmen den defekten Pfad:

```
$ sudo nvme id-ctrl /dev/nvme0 | grep sgls
sgls : 0x70001          # unsere BIWIN — betroffen
```

Laufwerke mit `sgls : 0` (etwa Crucial P5 Plus) sind immun — deshalb blieb der Bug
anderswo weitgehend unbemerkt.

Die gefundene Readahead-Schwelle ist ein *Nebeneffekt*: Der rpi-2712-Kernel nutzt
16-KB-Seiten, ein Readahead ≤ 16 KB ergibt also genau ein physisches Segment, und
`nvme_pci_setup_data()` nimmt eine PRP-Abkürzung, die den defekten SGL-Pfad
umgeht. **`blockdev --setra 32` ist deshalb kein sicherer Workaround.**

Behoben durch `a54afbc8a213` („nvme-pci: DMA unmap the correct regions in
nvme_free_sgls"), erstmals veröffentlicht in v6.19-rc8, von Raspberry Pi nach
`rpi-6.18.y` übernommen ([PR #7500](https://github.com/raspberrypi/linux/pull/7500))
und via `rpi-update` ab Kernel 6.18.38 ausgeliefert. **Nicht nach stable 6.18.y
zurückportiert und mit Stand 25.07.2026 nicht im apt-Repository** — dort ist
6.18.34 weiterhin das neueste Paket.

---

## Behebung

1. **Kernel auf 6.12.75 zurückgestuft** (lokal bereits installiert). Boot-Images in
   `/boot/firmware/` ausgetauscht, Originale als `*.bak-6.18.34` aufbewahrt, und
   `linux-image-rpi-2712` / `-v8` auf `apt-mark hold` gesetzt, damit ein Upgrade
   den Fehler nicht klammheimlich zurückbringt.
2. **Verifiziert:** 15 Durchgänge × 2 GB = 30 GB mit Standard-Readahead, keine
   einzige Abweichung. Unter 6.18.34 scheiterte derselbe Test zu 100 %.
3. **`states` repariert:** exakt 2 dauerhaft beschädigte Seiten (26172, 45176 von
   74.924) mit `zero_damaged_pages` bereinigt — diesmal legitim, weil der
   Transportpfad zuvor nachweislich sauber war und der Schaden stabil statt
   wandernd. Kosten: ~114 von 4,34 Mio. Zeilen (0,003 %).
4. **PCIe bleibt auf Gen 2** — `dtparam=pciex1_gen=3` bleibt unabhängig davon
   draußen; Gen 3 ist auf dem Pi 5 nicht validiert.

Rückweg auf 6.18 später: `sudo rpi-update` (≥ 6.18.38) oder auf ein apt-Paket
≥ 6.18.38+rpt warten — danach die 2-GB-Verifikation erneut fahren, bevor man ihm
vertraut.

---

## Was tatsächlich verloren ging

Nichts Wesentliches, und weniger als befürchtet. Die Google-Drive-Kopien waren
durchgehend intakt — ironischerweise *gerade weil* `rclone sync` Größe und mtime
statt Prüfsummen vergleicht, sodass die scheinbar korrupten lokalen Dateien nie
über die guten hochgeladen wurden. Auch die lokalen Dumps waren nie beschädigt;
sie ließen sich lediglich nicht korrekt lesen, solange der Bug aktiv war.

Der einzige echte Verlust war selbst verursacht: ~3 Seiten `statistics`, genullt
von einer Reparatur, die auf Phantom-Korruption zielte.

---

## Lehren

1. **Zuerst gepuffert gegen `O_DIRECT` testen.** Das trennt Kernel/Page-Cache von
   Gerät/Medium in zwei Minuten und hätte drei Hardwaretausche erspart.
2. **Wandernde Fehler sind nie das Medium.** Dieselbe Datei, bei jedem Lesevorgang
   eine andere Prüfsumme — das bedeutet Transport oder Software, nicht Flash.
3. **`cp` + `drop_caches` ist kein Hardwaretest.** Er misst genau einen Pfad.
4. **Ein sauberer Durchlauf beweist nichts.** Verifikation braucht mehrere GB *und*
   mehrere Wiederholungen, samt Prüfung von Exit-Code und Dateigröße. Eine um den
   Faktor 10 gesunkene Fehlerrate sieht bei kleinen Stichproben exakt wie eine
   Behebung aus.
5. **Früh gegen ein funktionierendes Gegenstück vergleichen.** `uname -r` und
   `/proc/cmdline` zwischen pi5a und pi5b war der entscheidende Hinweis und kostete
   nichts.
6. **Nach bekannten Bugs suchen, bevor man die Hardware beschuldigt.** Das Issue
   war offen, diagnostiziert und von den Upstream-Maintainern behoben — eine Woche
   bevor wir anfingen, Teile zu tauschen.
7. **Niemals `zero_damaged_pages`, bevor der Transportpfad ausgeschlossen ist.** Es
   zerstört gesunde Daten, wenn die Korruption gar nicht real ist.

---

## Folgemaßnahmen

**Erledigt:** Ein [Storage-Round-Trip-Check](../scripts/README.md) läuft nun
nächtlich und exportiert `node_storage_roundtrip_*`. Er schreibt eine bekannte
Nutzlast, verdrängt sie aus dem Page-Cache, liest sie zurück und vergleicht — der
einzige Wächter hier, der überprüft, ob Daten den Round-Trip tatsächlich
überleben. Er validiert sich selbst über den Read-Counter des Blockgeräts, sodass
eine aus dem Cache bediente Lesung sich nicht als sauberes Ergebnis ausgeben kann.

**Erledigt:** Alerting wurde aktiviert (vmalert + Alertmanager → Home Assistant,
sichtbar in Grafana). Es war abgeschaltet, weil es niemand nutzte; eine Metrik, die
niemand ansieht, ist keine Absicherung. Die Alerts decken echte Korruption ab —
und ebenso den Fall, dass der Check selbst veraltet oder nicht mehr aussagekräftig
ist.

**Offen:** pi5b läuft weiterhin 6.12.75 und darf ebenfalls nicht auf 6.18.34
aktualisiert werden. Beide Nodes sollten auf ≥ 6.18.38 wechseln, sobald es in apt
ankommt.
