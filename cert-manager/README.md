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

## Create sealed secret Cloudflare API token
```
kubectl create secret generic cloudflare-api-token --dry-run=client -oyaml --from-literal=token=... | kubeseal -oyaml
```

## Get public and private certificates
```
kubectl get secrets ingress-tls -o jsonpath='{.data.tls\.crt}' | base64 -d
kubectl get secrets ingress-tls -o jsonpath='{.data.tls\.key}' | base64 -d
```

