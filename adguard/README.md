# [AdGuard](https://adguard.com/adguard-home.html)
- [GitHub](https://github.com/AdguardTeam/AdGuardHome)
- [Docker Hub](https://hub.docker.com/r/adguard/adguardhome)

## Helm install
```
helm upgrade -i adguard .
helm upgrade -i adguard-iot -f values-iot.yaml .
```

## Helm unintall
```
helm uninstall adguard
helm uninstall adguard-iot
``` 
