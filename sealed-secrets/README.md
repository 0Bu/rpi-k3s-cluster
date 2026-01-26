# [Sealed Secrets](https://sealed-secrets.netlify.app/)
- [Helm Chart](https://github.com/bitnami-labs/sealed-secrets#helm-chart)

## Helm install
```
helm install -n kube-system sealed-secrets . 
```

## Helm uninstall
```
helm uninstall -n kube-system sealed-secrets 
``` 

## Install kubeseal
```
curl -sL $(curl -sL https://api.github.com/repos/bitnami-labs/sealed-secrets/releases/latest \
| grep -oP '"browser_download_url":\s*"\K(https://.*?linux-arm\.tar\.gz)(?=")') \
| tar xzf - kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
rm kubeseal 
```

