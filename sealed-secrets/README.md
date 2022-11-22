# [Sealed Secrets](https://sealed-secrets.netlify.app/)
- [Helm Chart](https://github.com/bitnami-labs/sealed-secrets#helm-chart)

## Helm install
```
helm upgrade -i -n kube-system sealed-secrets . 
```

## Helm uninstall
```
helm uninstall -n kube-system sealed-secrets 
``` 

## Install kubeseal
```
curl -sL 'https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.19.2/kubeseal-0.19.2-linux-arm.tar.gz' | tar xz kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
rm kubeseal
```

