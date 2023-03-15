# [deCONZ](https://phoscon.de)
- [GitHub](https://github.com/dresden-elektronik/deconz-rest-plugin)
- [Docker image](https://github.com/deconz-community/deconz-docker)
- [Docker Hub](https://hub.docker.com/r/deconzcommunity/deconz)

## [Add a label to a node](https://kubernetes.io/docs/tasks/configure-pod-container/assign-pods-nodes/)
`kubectl label nodes pi4a usb=conbee`

## Helm install/upgrade
`helm upgrade --install deconz .`

## Helm unintall
`helm uninstall deconz`

## Create sealed secret
`kubectl create secret generic deconz-vnc-password --dry-run=client --from-literal=vnc-password=<...> -oyaml | kubeseal --controller-name sealed-secrets -oyaml`
