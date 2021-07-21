# deCONZ
- [deCONZ](https://github.com/dresden-elektronik/deconz-rest-plugin)
- [deCONZ Docker](https://github.com/marthoc/docker-deconz)

## [Add a label to a node](https://kubernetes.io/docs/tasks/configure-pod-container/assign-pods-nodes/)
`kubectl label nodes Pi4a usb=conbee`

## Helm install
`helm install --create-namespace -n deconz deconz .`

## Helm upgrade
`helm upgrade -n deconz deconz .`

## Helm unintall
`helm uninstall -n deconz deconz`

## Generate sealed secret
`ctrl+x ctrl+e`
```
kubectl create secret generic deconz-secret \
  --from-literal='vnc-password=<PASSWORD>' \
  --dry-run=client -o yaml \
  | kubeseal -o yaml -n deconz > templates/sealed-secret.yaml
```

