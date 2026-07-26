# [VictoriaMetrics](https://docs.victoriametrics.com/helm/victoria-metrics-k8s-stack/)
- [Helm Chart](https://github.com/VictoriaMetrics/helm-charts/tree/master/charts/victoria-metrics-k8s-stack)

## Helm install
```
helm install victoria-metrics .
```

## Helm unintall
```
helm uninstall victoria-metrics
``` 

## Alerting

```
VMRule (templates/vmrule-*.yaml)
  -> vmalert          evaluates the PromQL against VictoriaMetrics
    -> Alertmanager   deduplicates, groups, routes
      -> webhook      Home Assistant
      -> Grafana      shows firing alerts via the Alertmanager datasource
```

Grafana only *displays* these alerts — the rules are evaluated by vmalert, so
they keep working even if Grafana is down.

### Adding a new alert source

1. Copy `templates/vmrule-daikin.yaml` to `templates/vmrule-<domain>.yaml`.
2. Set a new `component` label (e.g. `solar`, `network`). Routing in
   `values.yaml` groups by `component` and needs no change.
3. Pick `severity`: `critical` (notifies immediately, repeats hourly),
   `warning` (30 s grouping, repeats every 12 h) or `info`.

Alert templates use Go syntax (`{{ $labels.instance }}`) which collides with
Helm's. Wrap those strings in backticks so Helm passes them through:

```yaml
summary: {{ `"Problem on {{ $labels.instance }}"` }}
```

### Home Assistant receiver

Alertmanager POSTs to an HA webhook. The webhook id is the only thing guarding
that endpoint, so the URL lives in the SealedSecret
`templates/sealed-secret-ha-webhook.yaml` and never in plain text here.

HA side — create an automation with a `webhook` trigger using the matching id:

```yaml
automation:
  - alias: Cluster alerts
    trigger:
      - platform: webhook
        webhook_id: <id from the sealed secret>
        allowed_methods: [POST]
        local_only: true
    action:
      - service: notify.notify
        data:
          title: >-
            {{ trigger.json.status | upper }}:
            {{ trigger.json.alerts[0].labels.alertname }}
          message: >-
            {{ trigger.json.alerts[0].annotations.summary }}
```

The payload is the standard Alertmanager webhook format: `status`
(`firing`/`resolved`), `alerts[]` with `labels` and `annotations`, `commonLabels`.
`send_resolved: true` is set, so recoveries arrive as well.

### Checking alerts

```bash
kubectl port-forward -n default svc/vmalert-vm 8080:8080          # rule status
kubectl port-forward -n default svc/vmalertmanager-vm 9093:9093   # active alerts
```

