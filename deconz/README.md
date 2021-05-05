# deCONZ
- [deCONZ](https://github.com/dresden-elektronik/deconz-rest-plugin)
- [deCONZ Docker](https://github.com/marthoc/docker-deconz)

## Helm install
`helm install --create-namespace -n deconz deconz .`

## Helm upgrade
`helm upgrade -n deconz deconz .`

## Helm unintall
`helm uninstall -n deconz deconz`

## Generate sealed secret
```
kubectl create secret generic deconz-secret \
  --from-literal='vnc-password=<PASSWORD>' \
  --dry-run=client -o yaml \
  | kubeseal -o yaml -n deconz > sealed-secret.yaml
```

