# Migration: `victoria-metrics-single` → `victoria-metrics-k8s-stack`

Stand: 2026-04-28

## Ausgangslage

| Komponente | Chart | Version | Pfad / Service |
|---|---|---|---|
| VictoriaMetrics | `victoria-metrics-single` (wrapped) | 0.35.0 | Service `victoria-metrics-server:8428`, Ingress `victoria-metrics.burau.dev`, `vm.burau.dev` |
| Prometheus | `prometheus-community/prometheus` (wrapped) | 29.3.0 | Ingress `prometheus.burau.dev`, alertmanager + pushgateway disabled |
| Telegraf | wrapped | — | schreibt Line-Protocol nach `http://victoria-metrics-server:8428` |
| Grafana | wrapped | — | Datasources via API verwaltet (nicht im Chart) |

NFS Shares:
- `192.168.1.5:/nfs/victoria-metrics` → PV/PVC `victoria-metrics`, 20Gi, RWX, Retain
- `192.168.1.5:/nfs/prometheus` → PV/PVC `prometheus`, 20Gi, RWX, Retain

ArgoCD Applications: [argocd/templates/victoria-metrics.yaml](argocd/templates/victoria-metrics.yaml) (enthält bereits vorbereitete `ignoreDifferences` für den k8s-stack — Webhook-CA und Validation-Secret), [argocd/templates/prometheus.yaml](argocd/templates/prometheus.yaml).

## Ziel

- Eine kombinierte Bereitstellung über `victoria-metrics-k8s-stack` mit `vmsingle` (TSDB) + `vmagent` (Scraper) + `vm-operator` (CRDs).
- `vmagent` ersetzt den Prometheus-Server vollständig — gleicher Scrape-Mechanismus, Remote-Write direkt in `vmsingle`, kein separates Prometheus-PV mehr.
- Bestehende NFS-Daten von `/nfs/victoria-metrics` werden weiter genutzt → keine Datenmigration, kein Re-Import.
- Prometheus-Chart inklusive ArgoCD-App und NFS-Verzeichnis wird entfernt.

## Architektur Ist → Soll

```
IST:                                    SOLL:
                                        
telegraf ──► vm-server:8428             telegraf ──► vmsingle-<rel>:8429
                                                               ▲
prometheus ─► /nfs/prometheus           vmagent  ──┘ (remoteWrite)
(scraped: kubelet,                         scraped: gleiche Targets
 kube-state-metrics,                        per VMServiceScrape /
 node-exporter, …)                          VMPodScrape CRs
                                        
grafana datasource:                     grafana datasource:
  Prometheus → prometheus-server          Prometheus → vmsingle-<rel>:8429
  Prometheus → vm-server:8428             (eine einzige Quelle)
```

## Datenkompatibilität

`vmsingle` und `victoria-metrics-single` verwenden dasselbe Binary und denselben On-Disk-Format. Default Mount-Pfad in beiden Charts ist `/storage`. Die bestehende NFS-Freigabe kann unverändert weiterverwendet werden, sofern:

1. Der Mount-Pfad im neuen Pod auf `/storage` zeigt (Default des CR `VMSingle`).
2. Die `existingClaim`-PVC `victoria-metrics` in den `VMSingle`-CR übernommen wird (Stack erstellt sonst per `volumeClaimTemplates` eine neue PVC).
3. Der alte StatefulSet/Deployment vor dem ersten Start der neuen Pods gestoppt ist (NFS RWX wäre zwar mehrfach mountbar, aber paralleler Schreibzugriff durch zwei `vmsingle`-Instanzen muss strikt vermieden werden).

## Migrationsschritte

### 1. Vorbereitung — neuer Helm-Wrapper

`victoria-metrics/Chart.yaml` umstellen:

```yaml
dependencies:
  - name: victoria-metrics-k8s-stack
    alias: victoria-metrics
    version: "<aktuell>"   # via `helm search repo vm/victoria-metrics-k8s-stack`
    repository: https://victoriametrics.github.io/helm-charts/
```

`victoria-metrics/Chart.lock` neu generieren via `helm dependency update ./victoria-metrics`.

### 2. `victoria-metrics/values.yaml` neu schreiben

Wichtige Punkte:

- `vmsingle.spec.storage` mit `existingClaim` referenziert die bestehende PVC.
- `vmsingle.spec.retentionPeriod: "100y"` (Format des CR akzeptiert „100y", siehe vm-operator Doku).
- `vmagent` aktivieren, alle Default-Scrapes (kubelet, kube-apiserver, kube-state-metrics, node-exporter, coredns) belassen — diese decken den bisherigen Prometheus-Scope ab.
- `vmalert`, `alertmanager`: deaktivieren (so wie aktuell bei Prometheus auch).
- `prometheus-node-exporter` und `kube-state-metrics`: enable (bisher implizit über Prometheus-Chart vorhanden, ggf. prüfen ob aus dem prometheus-Chart deployed).
- Ingress für `vmsingle` analog zur jetzigen Konfiguration (`victoria-metrics.burau.dev`, `vm.burau.dev`, Traefik HTTPS-Redirect-Middleware, Secret `ingress-tls`).
- `crds.enabled: true` (Operator-CRDs).
- `grafana.enabled: false` (eigener Grafana-Chart bleibt bestehen).

Skizze:

```yaml
nfs:
  server: 192.168.1.5
  path: /nfs/victoria-metrics

victoria-metrics:
  crds:
    enabled: true
  victoria-metrics-operator:
    enabled: true

  vmsingle:
    enabled: true
    spec:
      retentionPeriod: "100y"
      storage:
        existingClaim: victoria-metrics   # bestehende PVC
        # optional: Selector falls existingClaim nicht reicht
      extraArgs:
        # falls nötig: search.maxQueryDuration etc.
      ingress:
        enabled: true
        ingressClassName: traefik
        annotations:
          traefik.ingress.kubernetes.io/router.middlewares: default-https-redirect@kubernetescrd
        hosts:
          - victoria-metrics.burau.dev
          - vm.burau.dev
        tls:
          - secretName: ingress-tls
            hosts:
              - victoria-metrics.burau.dev
              - vm.burau.dev

  vmagent:
    enabled: true
    spec:
      replicaCount: 1
      # remoteWrite wird automatisch auf vmsingle gesetzt

  vmalert:
    enabled: false
  alertmanager:
    enabled: false
  vmauth:
    enabled: false

  kube-state-metrics:
    enabled: true
  prometheus-node-exporter:
    enabled: true

  grafana:
    enabled: false
```

> Prüfen: Der Default Service-Name für VMSingle ist je nach Chart-Version
> `vmsingle-<release>` oder `<release>-victoria-metrics-k8s-stack`.
> Vor Telegraf-Umstellung mit `kubectl get svc` verifizieren.

### 3. PV/PVC behalten

[victoria-metrics/templates/pv.yaml](victoria-metrics/templates/pv.yaml) und [victoria-metrics/templates/pvc.yaml](victoria-metrics/templates/pvc.yaml) bleiben unverändert. Die PVC `victoria-metrics` wird im `VMSingle`-CR via `existingClaim` referenziert. `persistentVolumeReclaimPolicy: Retain` ist bereits gesetzt — Daten überleben auch versehentliches Löschen der PVC.

### 4. Telegraf-Output umstellen

[telegraf/values.yaml:9](telegraf/values.yaml:9):

```yaml
- name: VICTORIA_METRICS_URL
  value: "http://vmsingle-victoria-metrics:8429"   # Service-Namen final verifizieren
```

VictoriaMetrics akzeptiert Prometheus-, InfluxDB-, OpenTSDB-Eingang auf demselben Port. Die `outputs.influxdb`-Sektion in Telegraf bleibt unverändert.

### 5. Prometheus-Scrapes auf vmagent umziehen

Der `vmagent` aus dem k8s-stack scrapt per Default via `VMServiceScrape`/`VMPodScrape`-CRs:

- kubelet
- kube-apiserver
- kube-controller-manager / scheduler / etcd (k3s: oft nicht erreichbar — beobachten, ggf. deaktivieren)
- coredns
- kube-state-metrics
- node-exporter

Damit ist die bisherige Default-Abdeckung des Prometheus-Charts gleichwertig oder besser. Eigene Scrapes (falls in Prometheus zusätzliche `extraScrapeConfigs` definiert wären) müssten als zusätzliche `VMServiceScrape` nachgezogen werden — im aktuellen [prometheus/values.yaml](prometheus/values.yaml) sind keine vorhanden.

### 6. Grafana-Datasources anpassen

Die existierenden Prometheus-Datasources (eine für Prometheus, eine für VictoriaMetrics) konsolidieren auf eine einzige, die auf den neuen `vmsingle`-Service zeigt. Ablauf wie in [CLAUDE.md](CLAUDE.md) beschrieben:

```bash
kubectl -n default exec -i deployment/grafana -- sh -c \
  'curl -s http://admin:admin@localhost:3000/api/datasources'
# Prometheus-Datasource auf URL des vmsingle-Service umstellen,
# Datasource „Prometheus" (alt, prometheus-server) entfernen.
```

Alle Dashboards, die bereits PromQL via VictoriaMetrics-Datasource nutzen, sind ohne Änderung kompatibel. Dashboards, die explizit die alte Prometheus-Datasource referenzieren (UID), müssen auf die neue Datasource-UID umgemappt werden.

### 7. ArgoCD Application umbenennen / belassen

[argocd/templates/victoria-metrics.yaml](argocd/templates/victoria-metrics.yaml) referenziert weiterhin `path: victoria-metrics` — kann unverändert bleiben.

`ignoreDifferences` aktualisieren (Platzhalter `<fullname>`/`<k8s-stack-namespace>` durch tatsächliche Werte ersetzen, sonst sind die Regeln wirkungslos):

```yaml
ignoreDifferences:
  - group: ""
    kind: Secret
    name: victoria-metrics-victoria-metrics-k8s-stack-validation
    namespace: default
    jsonPointers:
      - /data
  - group: admissionregistration.k8s.io
    kind: ValidatingWebhookConfiguration
    name: victoria-metrics-victoria-metrics-k8s-stack-admission
    jqPathExpressions:
      - '.webhooks[]?.clientConfig.caBundle'
```

CRDs: Falls ArgoCD `ServerSideApply` benötigt, `syncOptions: ServerSideApply=true` ergänzen.

### 8. Prometheus entfernen

Reihenfolge wichtig — erst nachdem `vmagent` läuft und Daten liefert:

1. [argocd/templates/prometheus.yaml](argocd/templates/prometheus.yaml) löschen → ArgoCD prunt das Prometheus-Deployment.
2. Verzeichnis `prometheus/` löschen ([prometheus/Chart.yaml](prometheus/Chart.yaml), [prometheus/values.yaml](prometheus/values.yaml), [prometheus/templates/pv.yaml](prometheus/templates/pv.yaml), [prometheus/templates/pvc.yaml](prometheus/templates/pvc.yaml), [prometheus/Chart.lock](prometheus/Chart.lock), [prometheus/README.md](prometheus/README.md)).
3. PV `prometheus` ist `Retain` → bleibt nach PVC-Löschung mit Status `Released` zurück. Manuell entfernen:
   ```bash
   kubectl delete pv prometheus
   ```
4. NFS-Daten auf dem Server löschen (manuell, bewusst):
   ```bash
   ssh 192.168.1.5 'sudo rm -rf /nfs/prometheus/*'
   ```
   (Verzeichnis selbst belassen oder ebenfalls entfernen.)
5. DNS/Ingress `prometheus.burau.dev` außer Betrieb nehmen, falls nicht von Traefik dynamisch verwaltet.

## Cutover-Reihenfolge (am Cluster)

1. **Backup absichern**
   - NFS-Snapshot bzw. `tar` von `/nfs/victoria-metrics` (Read-Only Snapshot bevorzugt).
   - InfluxDB-Backup (separate Datenpfade, aber Standard-Hygiene laut [CLAUDE.md](CLAUDE.md)).
2. **Helm-Templates lokal validieren**
   ```bash
   helm dependency update ./victoria-metrics
   helm template victoria-metrics ./victoria-metrics > /tmp/vm-stack.yaml
   yamllint /tmp/vm-stack.yaml
   kubectl apply --dry-run=client -f /tmp/vm-stack.yaml
   ```
3. **Alten VM-Pod stoppen** (kurzes Schreibfenster) — vor dem Sync, damit der NFS-Mount sauber an den neuen Pod übergeht:
   ```bash
   kubectl scale deployment victoria-metrics-server --replicas=0
   ```
4. **Commit + Push**: neue `victoria-metrics`-Werte; Prometheus-Verzeichnis und ArgoCD-App noch nicht entfernen.
5. **ArgoCD Sync** → Operator + CRDs + `vmsingle` + `vmagent` werden installiert. Prüfen:
   ```bash
   kubectl get vmsingle,vmagent -A
   kubectl logs -l app.kubernetes.io/name=vmsingle
   ```
   `vmsingle`-Pod muss die NFS-PVC erfolgreich mounten und die bestehenden Daten lesen.
6. **Telegraf umstellen** ([telegraf/values.yaml](telegraf/values.yaml)) → commit/push → ArgoCD-Sync → Datenfluss in Grafana validieren (Lücke = Cutover-Dauer Schritt 3–6).
7. **Grafana-Datasources** konsolidieren.
8. **Verifizieren**: Dashboards laden, PromQL gegen vmsingle, Telegraf-Inputs erscheinen, vmagent-Targets `up{}==1`.
9. **Prometheus entfernen** (Schritt 8 oben).

## Risiken / offene Punkte

- **Service-Namensschema**: Der finale Service-Name (`vmsingle-...` vs. `<release>-victoria-metrics-k8s-stack`) muss vor Telegraf-Umstellung aus `helm template` abgeleitet werden. Sonst Datenlücke in Telegraf.
- **PVC-Reuse**: Wenn der `VMSingle`-CR keine `existingClaim`-Option im aktuellen Chart-Schema bietet, Workaround mit `volumeClaimTemplates` + statischer PV-Zuordnung über `volumeName`/`selector` (PV-Label setzen).
- **CRD-Lifecycle**: `crds.enabled: true` lässt Helm CRDs verwalten. Bei späteren Upgrades muss ArgoCD CRDs respektieren (`ServerSideApply=true`, `Replace=true` ggf. nicht).
- **ARM64**: vm-operator und vmagent sind als arm64-Images verfügbar — vor Sync mit `kubectl describe pod` prüfen, dass kein `exec format error` auftritt.
- **k3s-spezifische Scrapes**: `kube-controller-manager`, `kube-scheduler`, `kube-etcd` laufen im k3s-Server-Prozess und exponieren Metriken nicht standardmäßig. Falls vmagent diese Targets meldet, in den Stack-Values deaktivieren (`kubeControllerManager.enabled: false` etc., analog zu kube-prometheus-stack).
- **Retention-Format**: VMSingle CR akzeptiert „100y" — falls nicht, auf `1200mo` oder `36500d` ausweichen.

## Rollback

Solange Prometheus-Chart und altes VM-Deployment nicht gelöscht sind, ist Rollback ein einfaches `git revert` der Commits. Nach Schritt 9 (Prometheus-NFS-Daten gelöscht) ist nur noch das Wiederherstellen des Prometheus-Charts möglich, nicht jedoch der historischen Prometheus-Daten — diese werden allerdings ohnehin durch die VM-Daten ersetzt.

## Geschätzter Aufwand

- Implementierung Werte / Templating: 1–2 h
- Cutover + Verifikation: 30–60 min Wartungsfenster
- Aufräumen Prometheus + DNS: 15 min
