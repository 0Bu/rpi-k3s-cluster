# Installing [k3s](https://k3s.io) on [Raspberry Pi OS](https://www.raspberrypi.com/software/operating-systems/)

### Enable cgroups
- append `cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory` to `/boot/firmware/cmdline.txt`
- *optional*: append `arm_64bit=1` to `/boot/config.txt` under `[all]` on 32-bit Raspberry Pi OS ([arm_64bit](https://www.raspberrypi.com/documentation/computers/config_txt.html#arm_64bit))

### Disable swap (debian 13)
```
sudo swapon --show
sudo swapoff -a
sudo echo "zram-size = 0" >> /usr/lib/systemd/zram-generator.conf
```

## Dual stack installation
k3s docs: <https://docs.k3s.io/networking/basic-network-options#dual-stack-ipv4--ipv6-networking>

#### *Optional*: Router Advertisement Daemon
```
sudo apt install radvd
```

#### [radvd configuration](https://linux.die.net/man/5/radvd.conf)
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

### Enable systemd-network
```
sudo systemctl enable systemd-networkd
sudo systemctl restart systemd-networkd
```

## Master installation
```
sudo mkdir -p /etc/rancher/k3s
sudo vim /etc/rancher/k3s/config.yaml
```

```
write-kubeconfig-mode: "644"
disable:
  - servicelb
node-ip: "192.168.1.5,fd7c:3b4a:5f1d::5a"
cluster-cidr: "10.42.0.0/16,fd00:10:42::/56"
service-cidr: "10.43.0.0/16,fd00:10:43::/112"
flannel-ipv6-masq: true
```

`curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.35.0+k3s1" sh -`

### Node installation
Get master token
`sudo cat /var/lib/rancher/k3s/server/node-token`

```
sudo mkdir -p /etc/rancher/k3s
sudo vim /etc/rancher/k3s/config.yaml
```

```
server: "https://192.168.1.5:6443"
token: "TOKEN"
write-kubeconfig-mode: "644"
node-ip: "192.168.1.5,fd7c:3b4a:5f1d::5a"
```

`curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.35.0+k3s1" sh -`

## High availability cluster installation
k3s docs: <https://docs.k3s.io/datastore/ha-embedded>
```
sudo mkdir -p /etc/rancher/k3s
sudo vim /etc/rancher/k3s/config.yaml
```

```
cluster-init: true
token: "TOKEN"
write-kubeconfig-mode: "644"
disable:
  - servicelb
node-ip: "192.168.1.5,fd7c:3b4a:5f1d::5a"
cluster-cidr: "10.42.0.0/16,fd00:10:42::/56"
service-cidr: "10.43.0.0/16,fd00:10:43::/112"
flannel-ipv6-masq: true
```

`curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.35.0+k3s1" sh -`

### High availability node installation
```
sudo mkdir -p /etc/rancher/k3s
sudo vim /etc/rancher/k3s/config.yaml
```

```
server: https://192.168.1.5:6443
token: "TOKEN"
write-kubeconfig-mode: "644"
disable:
  - servicelb
node-ip: "192.168.1.15,fd7c:3b4a:5f1d::5b"
cluster-cidr: "10.42.0.0/16,fd00:10:42::/56"
service-cidr: "10.43.0.0/16,fd00:10:43::/112"
flannel-ipv6-masq: true
```

`curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.35.0+k3s1" sh -`

## Single stack installation
k3s docs: <https://docs.k3s.io/installation>
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.35.0+k3s1"
export INSTALL_K3S_EXEC="--disable servicelb"
curl -sfL https://get.k3s.io | sh -
```

### Node installation
On master `sudo cat /var/lib/rancher/k3s/server/node-token`
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.35.0+k3s1"
export K3S_URL="https://192.168.1.5:6443"
export K3S_TOKEN="TOKEN"
curl -sfL https://get.k3s.io | sh -
```

### [Helm](https://helm.sh) installation
`curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash`

#### Helm configuration
```
mkdir -p ~/.kube
kubectl config view --raw > ~/.kube/config
sudo chmod go-r ~/.kube/config
```

### [k9s](https://github.com/derailed/k9s) installation
```
curl -sLO "https://github.com/derailed/k9s/releases/download/v0.50.16/k9s_linux_arm.deb"
sudo dpkg -i k9s_linux_arm.deb
rm k9s_linux_arm.deb
```

