# [MetalLB](https://metallb.universe.tf/)

## [Installation](https://metallb.universe.tf/installation/)
```
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.9.6/manifests/namespace.yaml
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.9.6/manifests/metallb.yaml
# On first install only
kubectl create secret generic -n metallb-system memberlist --from-literal=secretkey="$(openssl rand -base64 128)"
```

## [Layer 2 Configuration](https://metallb.universe.tf/configuration/#layer-2-configuration)
```
kubectl apply -f config-map.yaml
```
