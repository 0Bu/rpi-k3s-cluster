# [Mosquitto](https://mosquitto.org)
- [mosquitto](https://github.com/eclipse/mosquitto)
- [mosquitto docker](https://hub.docker.com/_/eclipse-mosquitto)

## Helm install
```
helm install mosquitto .
```

## Helm unintall
```
helm uninstall mosquitto
```

## Persistence
Retained messages (e.g. Home Assistant MQTT discovery configs) are persisted to `/mosquitto/data` on an NFS-backed PV (`/nfs/mosquitto`), so they survive pod restarts and rescheduling.

Create the NFS directory once on the NFS server:
```
sudo mkdir /nfs/mosquitto
sudo chown -R nobody:nogroup /nfs/mosquitto
```

### Verify
```
kubectl rollout restart deployment mosquitto
kubectl rollout status deployment mosquitto
mosquitto_sub -h 192.168.1.27 -t 'homeassistant/#' -v -W 5
```
The retained discovery configs must still be delivered after the restart.
