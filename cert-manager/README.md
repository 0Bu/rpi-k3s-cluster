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

## Extract certificate
```
kubectl get secrets selfsigned-secret -o jsonpath='{.data.tls\.crt}' | base64 -d > rpi-k3s-root.crt
```

## [Backup and Restore Resources](https://cert-manager.io/docs/devops-tips/backup/)
```
kubectl get --all-namespaces -oyaml issuer,clusterissuer,cert > backup.yaml
kubectl apply -f backup.yaml
```

## Installing self signed certificates in iOS
[Trust manually installed certificate profiles in iOS](https://support.apple.com/en-us/102390)

