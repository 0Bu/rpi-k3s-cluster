# Dual-stack installation

### Router Advertisement Daemon installation
```
sudo apt install radvd
```

### [radvd configuration](https://linux.die.net/man/5/radvd.conf)
`sudo vim /etc/radvd.conf`
```
interface eth0 {
   AdvSendAdvert on;
   prefix fd7c:3b4a:5f1d::/64 {};
};
```

### Add static IPv6 ULA
check the link `ip link` and create
`sudo vim /etc/systemd/network/10-eth0-static-ipv6.network`
```
[Match]
Name=eth0

[Network]
IPv6AcceptRA=yes
Address=fd7c:3b4a:5f1d::5a/64
```

### [k3s dual-stack installation](https://docs.k3s.io/installation/network-options#dual-stack-installation)
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.35.0+k3s1"
export INSTALL_K3S_EXEC="--disable servicelb --node-ip 192.168.1.5,fd7c:3b4a:5f1d::5a --cluster-cidr 10.42.0.0/16,fd00:10:42::/56 --service-cidr 10.43.0.0/16,fd00:10:43::/112 --flannel-ipv6-masq"
curl -sfL https://get.k3s.io | sh -
```

### Master token
`sudo cat /var/lib/rancher/k3s/server/node-token`

### Node installation
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.35.0+k3s1"
export INSTALL_K3S_EXEC="--node-ip 192.168.1.11,fd7c:3b4a:5f1d:4b"
export K3S_URL="https://192.168.1.5:6443"
export K3S_TOKEN="..."
curl -sfL https://get.k3s.io | sh -
```

## [High Availability Cluster Installation](https://docs.k3s.io/datastore/ha-embedded)
```
export K3S_CLUSTER_INIT=true
export K3S_TOKEN=SECRET
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.35.0+k3s1"
export INSTALL_K3S_EXEC="--disable servicelb --node-ip 192.168.1.5,fd7c:3b4a:5f1d::5a --cluster-cidr 10.42.0.0/16,fd00:10:42::/56 --service-cidr 10.43.0.0/16,fd00:10:43::/112 --flannel-ipv6-masq"
curl -sfL https://get.k3s.io | sh -
```

### High Availability Node Installation
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.35.0+k3s1"
export K3S_TOKEN=SECRET
curl -sfL https://get.k3s.io | sh -s server --server https://192.168.1.5:6443
```
