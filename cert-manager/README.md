# [cert-manager](https://cert-manager.io)
- [GitHub](https://github.com/cert-manager/cert-manager)
- [Helm Chart](https://cert-manager.io/docs/installation/helm/)

## Helm install 
compare: [CRD considerations](https://cert-manager.io/docs/installation/helm/#crd-considerations)
```
helm install cert-manager .
```

## Helm uninstall
```
helm uninstall cert-manager
``` 

## Create sealed secret
```
kubectl create secret generic cloudflare-api-token --dry-run=client --from-literal=token=<...> -oyaml | kubeseal --controller-name sealed-secrets -oyaml
```

## Get public and private certificates
```
kubectl get secrets cloudflare-tls -o jsonpath='{.data.tls\.crt}' | base64 -d
kubectl get secrets cloudflare-tls -o jsonpath='{.data.tls\.key}' | base64 -d
```

