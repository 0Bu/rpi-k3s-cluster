# [authentik](https://goauthentik.io)
- [Helm Chart](https://github.com/goauthentik/helm)
- [Documentation](https://docs.goauthentik.io)

## Helm install
```
helm install authentik .
```

## Helm uninstall
```
helm uninstall authentik
```

## Create sealed secret
```bash
kubectl create secret generic authentik-secrets --dry-run=client -oyaml \
  --from-literal=AUTHENTIK_SECRET_KEY=$(openssl rand -base64 36) \
  --from-literal=AUTHENTIK_POSTGRESQL__PASSWORD=$(openssl rand -base64 36) \
  | kubeseal -oyaml > templates/sealed-secret.yaml
```