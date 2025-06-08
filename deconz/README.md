# [deCONZ](https://phoscon.de)
- [GitHub](https://github.com/dresden-elektronik/deconz-rest-plugin)
- [Docker image](https://github.com/deconz-community/deconz-docker)

## Helm install/upgrade
```
helm install deconz . \
--set host=pi4a \
--set loadBalancerIPs=192.168.1.26 \
--set device=/dev/ttyUSB0 \
--set vncPassword=deconz
```

## Helm unintall
```
helm uninstall deconz
```
