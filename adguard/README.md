# AdGuard
- [AdGuard](https://github.com/AdguardTeam/AdGuardHome)
- [AdGuard Docker](https://hub.docker.com/r/adguard/adguardhome)

## Helm install
```
helm install adguard .
helm install --create-namespace -n adguard-iot -f values-iot.yaml adguard .
```

## Helm unintall
```
helm uninstall adguard
helm uninstall -n adguard-iot adguard
``` 
