# [MetalLB](https://metallb.universe.tf/)

## [Installation](https://metallb.universe.tf/installation/#installation-with-helm)
```
helm repo add metallb https://metallb.github.io/metallb
helm install -n metallb --create-namespace metallb metallb/metallb
kubectl apply -f config.yaml
```
