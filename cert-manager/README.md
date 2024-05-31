# [cert-manager](https://cert-manager.io)
- [GitHub](https://github.com/cert-manager/cert-manager)
- [Helm Chart](https://cert-manager.io/docs/installation/helm/)

## Helm install 
compare: [CRD considerations](https://cert-manager.io/docs/installation/helm/#crd-considerations)
```
helm install cert-manager --set installCRDs=true .
```

## Helm upgrade
```
helm upgrade cert-manager . 
```

## Helm uninstall
```
helm uninstall cert-manager
``` 

## Extract certificate
```
kubectl get secrets self-signed-root-ca -o jsonpath='{.data.ca\.crt}' | base64 -d > ca.crt
kubectl get secrets self-signed-root-ca -o jsonpath='{.data.tls\.crt}' | base64 -d > tls.crt
kubectl get secrets self-signed-root-ca -o jsonpath='{.data.tls\.key}' | base64 -d > tls.key
```

## [Backup and Restore Resources](https://cert-manager.io/docs/devops-tips/backup/)
```
kubectl get --all-namespaces -oyaml issuer,clusterissuer,cert > backup.yaml
kubectl apply -f backup.yaml
```
