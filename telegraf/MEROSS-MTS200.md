# Meross MTS200 — lokale Abfrage über Telegraf

Telegraf liest das WLAN-Thermostat **Meross MTS200** direkt im LAN aus (keine
Meross-Cloud, kein Home Assistant dazwischen) und schreibt die Werte über den
bestehenden `outputs.influxdb` nach VictoriaMetrics.

Die Integration ist **inaktiv**, solange `meross.enabled: false` (Default) —
gemergt ändert sie am laufenden Cluster nichts. Aktivierung: siehe unten.

## Warum nicht einfach `inputs.http`?

Meross-Geräte sprechen im LAN ein eigenes Protokoll: HTTP `POST` auf
`http://<ip>/config` mit einem JSON-Umschlag aus `header` und `payload`. Der
Header muss signiert sein:

```
sign = md5(messageId + device_key + timestamp)
```

`messageId` ist ein zufälliger 32-Zeichen-Hex-String, `timestamp` die aktuelle
Unix-Zeit. Genau das kann `inputs.http` nicht: der Plugin schickt nur einen
**statischen** Body, kein MD5 über einen frischen Zeitstempel. Deshalb steht ein
knapp 200 Zeilen langer Poller (reine Python-Standardbibliothek, offizielles
`python`-Image, Skript aus einer ConfigMap) dazwischen:

```
Telegraf inputs.http ──GET──▶ telegraf-meross-poller ──signierter POST──▶ MTS200
     │                         (baut Header + sign)        http://<ip>/config
     │◀──── payload (JSON) ────────────────────────────────────────────┘
     ▼
outputs.influxdb ──▶ vmsingle-vm:8428
```

Der Poller ist bewusst dumm: er gibt den `payload`-Teil der Geräteantwort
unverändert zurück. Parsen, Umbenennen und Skalieren macht Telegraf
(`templates/configmap-meross.yaml`), damit die Metrikdefinition dort liegt, wo
im Repo auch die Modbus-Register liegen.

Protokolldetails stammen aus [krahabb/meross_lan](https://github.com/krahabb/meross_lan)
(`merossclient/protocol/message.py`, `httpclient.py`) und aus den dortigen
Geräte-Traces (`emulator_traces/…mts200*.json.txt`, `…mts200b….csv`).

## Was das Gerät liefert

`GET Appliance.System.All` gibt den kompletten Zustand zurück; alles Relevante
steckt in `digest.thermostat` (Auszug aus einem echten MTS200-Trace):

```json
{"mode": [{"channel": 0, "onoff": 1, "mode": 4, "state": 0, "currentTemp": 210,
           "heatTemp": 200, "coolTemp": 190, "ecoTemp": 180, "manualTemp": 210,
           "warning": 0, "targetTemp": 210, "min": 50, "max": 350,
           "lmTime": 1674112153}],
 "windowOpened": [{"channel": 0, "status": 0, "detect": 1, "lmTime": 1674112153}]}
```

Ein Request pro Intervall genügt also für sämtliche Werte. `Appliance.System.Runtime`
(`{"runtime": {"signal": 100}}`) wird zusätzlich alle 5 Minuten für die
WLAN-Signalstärke abgefragt.

## Metriken in VictoriaMetrics

Alle Serien tragen `device="<name aus values.yaml>"` und `channel="0"`.
Temperaturen liefert das Gerät in **Zehntelgrad** (210 = 21,0 °C); der
`processors.scale`-Block rechnet mit `factor = 0.1` um.

| Metrik                                  | Quelle (JSON)  | Bedeutung |
|-----------------------------------------|----------------|-----------|
| `meross_mts200_temperature`             | `currentTemp`  | Ist-Temperatur (°C) |
| `meross_mts200_target_temp`             | `targetTemp`   | aktueller Sollwert (°C) |
| `meross_mts200_heat_temp`               | `heatTemp`     | Sollwert Preset *heat/comfort* (°C) |
| `meross_mts200_cool_temp`               | `coolTemp`     | Sollwert Preset *cool/night* (°C) |
| `meross_mts200_eco_temp`                | `ecoTemp`      | Sollwert Preset *eco/away* (°C) |
| `meross_mts200_manual_temp`             | `manualTemp`   | Sollwert Handbetrieb (°C) |
| `meross_mts200_onoff`                   | `onoff`        | Thermostat ein (1) / aus (0) |
| `meross_mts200_state`                   | `state`        | Heizkreis gerade aktiv (Relais, 0/1) |
| `meross_mts200_mode`                    | `mode`         | 0=heat, 1=cool, 2=eco, 3=auto (Zeitplan), 4=manual |
| `meross_mts200_warning`                 | `warning`      | 0=ok, 1=Überhitzung, 2=Fühler nicht verbunden |
| `meross_mts200_window_open`             | `windowOpened.status` | Fenster-offen erkannt (0/1) |
| `meross_mts200_window_detection_enabled`| `windowOpened.detect` | Erkennung aktiviert (0/1) |
| `meross_mts200_runtime_signal`          | `runtime.signal` | WLAN-Signal (%) |

`lmTime` (Zeitstempel der letzten Änderung) sowie `min`/`max` (Gerätekonstanten
5,0 / 35,0 °C) werden über `excluded_keys` verworfen — als Zeitreihe wertlos.

Die Mode-Codes sind aus `meross_lan` übernommen (`climate.py`,
`MTS200_MODE_*`); dort stehen sie unter dem Vorbehalt "inferred from a user
trace". Vor dem Bau eines Dashboards also einmal gegen das Display prüfen.

Beispiel-Queries:

```promql
meross_mts200_temperature{device="wohnzimmer"}
meross_mts200_target_temp{device="wohnzimmer"} - meross_mts200_temperature{device="wohnzimmer"}
avg_over_time(meross_mts200_state{device="wohnzimmer"}[1h])   # Heiz-Taktverhältnis
```

## Aktivierung

1. **Geräte-IP fixieren** (DHCP-Reservierung im Router). Der MTS200 muss aus
   dem Cluster-Netz per HTTP erreichbar sein.

2. **Device-Key besorgen.** Der Key gehört zum *Meross-Account*, nicht zum
   einzelnen Gerät — alle Geräte desselben Accounts teilen ihn. Quellen:
   - `meross_lan` in Home Assistant einrichten (holt den Key beim Login über
     die Meross-Cloud-API) und den Wert aus dem Config-Entry übernehmen,
   - oder [MerossIot](https://github.com/albertogeniola/MerossIot) (`meross_api_cli`),
   - oder `GET Appliance.Config.Key` bei einem noch nicht gekoppelten Gerät.

   Test von einem Rechner im LAN (`TS` und `SIGN` frisch berechnen):

   ```sh
   MID=$(head -c16 /dev/urandom | md5sum | cut -d' ' -f1)
   TS=$(date +%s)
   SIGN=$(printf '%s%s%s' "$MID" "$KEY" "$TS" | md5sum | cut -d' ' -f1)
   curl -s http://192.168.1.60/config -H 'Content-Type: application/json' -d "{
     \"header\": {\"messageId\":\"$MID\",\"namespace\":\"Appliance.System.All\",
                  \"method\":\"GET\",\"payloadVersion\":1,\"from\":\"MerossClient\",
                  \"timestamp\":$TS,\"timestampMs\":0,\"sign\":\"$SIGN\"},
     \"payload\": {}}"
   ```

   Antwortet das Gerät mit `{"error":{"code":5001,…}}`, passt der Key nicht.

3. **Key versiegeln** und nach `values.yaml` eintragen:

   ```sh
   echo -n "<device-key>" | kubeseal --raw --namespace default --name telegraf-meross
   ```

4. **`telegraf/values.yaml`** anpassen:

   ```yaml
   meross:
     enabled: true
     devices:
       - name: wohnzimmer
         host: 192.168.1.60
     sealedKey: "AgA…"
   ```

5. Mergen, ArgoCD synchronisiert. Danach laufen ein zusätzlicher Pod
   (`telegraf-meross-poller`) und die neuen Inputs im Telegraf-Pod.

## Prüfen und Debuggen

```sh
kubectl logs deploy/telegraf-meross-poller
kubectl port-forward deploy/telegraf-meross-poller 9110:9110
curl -s "localhost:9110/poll?host=192.168.1.60&namespace=Appliance.System.All" | jq .all.digest
```

Der Poller antwortet mit `502` und einer Klartextmeldung, wenn das Gerät nicht
erreichbar ist oder die Signatur ablehnt; Telegraf protokolliert das dann als
fehlgeschlagenen `inputs.http`-Scrape. Es werden in dem Fall **keine** Werte
geschrieben — es gibt also keine eingefrorenen Messwerte, sondern eine Lücke in
der Zeitreihe.

Sicherheitsnetz im Poller: die Methode ist fest auf `GET` verdrahtet und nur
lesende Namespaces stehen auf der Allowlist, dazu die konfigurierten Hosts.
Über den Endpunkt lässt sich das Thermostat also nicht verstellen.

## Grenzen und Fallstricke

- **Verschlüsselte Firmware.** Neuere Meross-Firmware kann die lokale
  HTTP-Kommunikation AES-verschlüsseln (Ability `Appliance.Encrypt.ECDHE`).
  Taucht dieser Namespace in `GET Appliance.System.Ability` auf, reicht der
  Klartext-POST nicht mehr und der Poller müsste den Handshake aus `meross_lan`
  nachbauen. Bei den bekannten MTS200-Firmwares (7.6.x) ist das nicht der Fall,
  obwohl `firmware.encrypt: 1` gemeldet wird.
- **Cloud-Bindung bleibt.** Lokales Auslesen ändert nichts daran, dass das Gerät
  weiterhin mit dem Meross-MQTT-Broker spricht. Wer das abstellt, verliert die
  App-Steuerung.
- **Polling, kein Push.** 30 s Intervall ist ein Kompromiss; das Gerät liefert
  keine Änderungsmeldungen über HTTP. Kürzere Intervalle belasten das
  WLAN-Modul des Thermostats spürbar.
- **Ein Poller für alle Geräte.** Mehrere Thermostate werden über
  `meross.devices` ergänzt, nicht über mehrere Deployments.

## Verworfene Alternativen

- **`inputs.http` mit fest einkodierter Signatur.** `messageId`, `timestamp`
  und `sign` einmal berechnen und statisch in den Body schreiben. Das käme ganz
  ohne Poller aus — funktioniert aber nur, falls die Firmware den Zeitstempel
  nicht auf Aktualität prüft. Ungetestet und ein stiller Ausfall, sobald eine
  Firmware das anzieht.
- **MQTT-Rebind auf den Cluster-Broker.** Das Gerät lässt sich auf einen
  eigenen Broker umbiegen (`Appliance.Config.Key` mit `server`/`port`), dann
  würde `inputs.mqtt_consumer` wie bei Shelly/EMS-ESP reichen. Der MTS200
  verlangt dafür aber TLS auf 8883; unser Mosquitto hört nur unverschlüsselt
  auf 1883, und die App-Steuerung wäre weg.
- **Umweg über Home Assistant.** `meross_lan` in HA plus Export nach
  VictoriaMetrics. Weniger Code, aber eine zusätzliche Abhängigkeit in einem
  Pfad, der sonst ohne HA auskommt — und die Metriken hingen an der
  HA-Verfügbarkeit.

## Dateien

- `templates/configmap-meross.yaml` — `inputs.http` + `processors.rename`/
  `processors.scale`; ConfigMap `telegraf-meross`, gemountet nach
  `/etc/telegraf/meross.d`. Wird immer gerendert, bleibt ohne
  `meross.enabled` aber leer.
- `templates/configmap-meross-poller.yaml` — das Poller-Skript.
- `templates/meross-poller-deployment.yaml`, `templates/meross-poller-service.yaml`
  — Poller-Pod und Service `telegraf-meross-poller:9110`.
- `templates/sealed-secret-meross.yaml` — SealedSecret `telegraf-meross`
  (Schlüssel `device-key`), gerendert sobald `meross.sealedKey` gesetzt ist.
- `values.yaml` — Block `meross:` plus Mount/`--config-directory`.
