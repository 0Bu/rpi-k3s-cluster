# [Longhorn](https://longhorn.io)
- [GitHub](https://github.com/longhorn/longhorn)
- [Helm Chart](https://github.com/longhorn/longhorn/tree/master/chart)

## [Prerequisites](https://github.com/longhorn/longhorn/tree/master/chart#prerequisites)
```
sudo apt update
sudo apt install open-iscsi nfs-common
```

## [Helm installation](https://github.com/longhorn/longhorn/tree/master/chart#installation)
```
helm install --create-namespace --namespace longhorn-system longhorn .
```

## [Helm uninstallation](https://github.com/longhorn/longhorn/tree/master/chart#uninstallation)
```
kubectl -n longhorn-system patch -p '{"value": "true"}' --type=merge lhs deleting-confirmation-flag
helm uninstall longhorn -n longhorn-system
kubectl delete namespace longhorn-system
``` 

