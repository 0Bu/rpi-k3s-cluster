# deCONZ
- [deCONZ](https://github.com/dresden-elektronik/deconz-rest-plugin)
- [deCONZ Docker](https://github.com/deconz-community/deconz-docker)

## [Add a label to a node](https://kubernetes.io/docs/tasks/configure-pod-container/assign-pods-nodes/)
`kubectl label nodes pi4a usb=conbee`

## Helm install
`helm install deconz --set vnc.mode=1 --set vnc.password='<PASSWORD>' .`

## Helm upgrade
`helm upgrade deconz .`

## Helm unintall
`helm uninstall deconz`

