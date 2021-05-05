# AdGuard
- [AdGuard](https://github.com/AdguardTeam/AdGuardHome)
- [AdGuard Docker](https://hub.docker.com/r/adguard/adguardhome)

## Helm install
```
helm install --create-namespace -n adguard adguard .
helm install --create-namespace -n adguard-iot -f values-iot.yaml adguard .
```

## Helm unintall
```
helm uninstall -n adguard adguard
helm uninstall -n adguard-iot adguard
``` 
