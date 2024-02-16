# pi cluster

### [NFS](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-nfs-mount-on-ubuntu-20-04-de)
#### Client
```
sudo apt update
sudo apt install nfs-common
```
#### Server
```
sudo apt update
sudo apt install nfs-kernel-server
sudo mkdir /nfs
sudo chown -R nobody:nogroup /nfs
```
#### NFS export config
```
sudo vim /etc/exports
/nfs 192.168.1.0/24(rw,sync,no_subtree_check)
```
#### NFS client mount
```
sudo mkdir /mnt/nfs
sudo mount <HOST_IP>:/nfs /mnt/nfs
```

## [k3s.io](https://k3s.io)

### [Enabling cgroups](https://rancher.com/docs/k3s/latest/en/advanced/#enabling-cgroups-for-raspbian-buster)
- append `cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory` to `/boot/cmdline.txt`
- *optional*: append `arm_64bit=1` to `/boot/config.txt` under `[all]` on 32-bit Raspberry Pi OS ([arm_64bit](https://www.raspberrypi.com/documentation/computers/config_txt.html#arm_64bit))

### Disable swap
```
sudo swapoff -a
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=0/' /etc/dphys-swapfile
```

### Master installation/upgrade
`ctrl+x ctrl+e`
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_EXEC="--disable servicelb --disable traefik"
export INSTALL_K3S_VERSION=$(curl -sL https://api.github.com/repos/k3s-io/k3s/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
curl -sfL https://get.k3s.io | sh - 
```

### Node installation/upgrade
On master `sudo cat /var/lib/rancher/k3s/server/node-token`
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION=$(curl -sL https://api.github.com/repos/k3s-io/k3s/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
export K3S_URL="https://192.168.1.4:6443"
export K3S_TOKEN="XXXX"
curl -sfL https://get.k3s.io | sh -
```

### [High availibility cluster](https://w-goutas.medium.com/set-up-a-kubernetes-cluster-in-minutes-41a0bd65ab93) installation
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_EXEC="--disable servicelb --disable traefik"
export INSTALL_K3S_VERSION=$(curl -sL https://api.github.com/repos/k3s-io/k3s/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
curl -sfL https://get.k3s.io | sh -s server --cluster-init --token 'secret'
```

### HA node installation
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_EXEC="--disable servicelb --disable traefik"
export INSTALL_K3S_VERSION=$(curl -sL https://api.github.com/repos/k3s-io/k3s/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
export K3S_TOKEN="secret"
curl -sfL https://get.k3s.io | sh -s server --server https://192.168.1.4:6443
```

### [Helm](https://helm.sh) [installation](https://helm.sh/docs/intro/install/)
`curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash`

#### Helm configuration
```
mkdir -p ~/.kube
kubectl config view --raw > ~/.kube/config
sudo chmod go-r ~/.kube/config
```

### [k9s](https://github.com/derailed/k9s) installation
```
K9S_VERSION=$(curl -sL https://api.github.com/repos/derailed/k9s/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
curl -sLO "https://github.com/derailed/k9s/releases/download/$K9S_VERSION/k9s_linux_arm.deb"
sudo dpkg -i k9s_linux_arm.deb
rm k9s_linux_arm.deb
```
