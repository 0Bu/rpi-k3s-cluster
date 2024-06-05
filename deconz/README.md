# [deCONZ](https://phoscon.de)
- [GitHub](https://github.com/dresden-elektronik/deconz-rest-plugin)
- [Docker image](https://github.com/deconz-community/deconz-docker)
- [Docker Hub](https://hub.docker.com/r/deconzcommunity/deconz)

## Helm install/upgrade
`helm upgrade --install deconz .`--set host=pi4a --set loadBalancerIPs=192.168.1.26

## Helm unintall
`helm uninstall deconz`

## Create sealed secret
`kubectl create secret generic deconz-vnc-password --dry-run=client --from-literal=vnc-password=<...> -oyaml | kubeseal --controller-name sealed-secrets -oyaml`
