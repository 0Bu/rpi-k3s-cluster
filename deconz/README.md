# [deCONZ](https://phoscon.de)
- [deCONZ](https://github.com/dresden-elektronik/deconz-rest-plugin)
- [deCONZ Docker](https://github.com/deconz-community/deconz-docker)
- [deCONZ Docker Hub](https://hub.docker.com/r/deconzcommunity/deconz)

## [Add a label to a node](https://kubernetes.io/docs/tasks/configure-pod-container/assign-pods-nodes/)
`kubectl label nodes pi4a usb=conbee`

## Helm install
`helm install deconz --set vnc.mode=1 --set vnc.password='<PASSWORD>' .`

## Helm upgrade
`helm upgrade -i deconz . --reuse-values`

## Helm unintall
`helm uninstall deconz`

