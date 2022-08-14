# pi cluster

## Raspberry Pi OS configuration

### ssh
`ssh pi:raspberry@<IP>`

### Set default editor
```
sudo update-alternatives --config editor
sudo update-alternatives --set editor /usr/bin/vim.tiny
```

### Create a new user
`sudo adduser oleg`

### Sudoers
```
sudo adduser oleg sudo
sudo sh -c 'echo "oleg ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/000_oleg-nopasswd'
```
### Delete ubuntu user
`sudo userdel -r pi`

### Disable welcome message
`sudo sh -c 'echo "" > /etc/motd'`

### Change hostname
```
hostnamectl
sudo hostnamectl set-hostname pi4
```

### Disable LED
Edit /boot/config.txt
```
[pi4]
# Disable the PWR LED
dtparam=pwr_led_trigger=none
dtparam=pwr_led_activelow=off
# Disable the Activity LED
dtparam=act_led_trigger=none
dtparam=act_led_activelow=off
# Disable ethernet port LEDs
dtparam=eth_led0=4
dtparam=eth_led1=4
```

### NTP Server
```
sudo apt update
sudo apt install ntp
echo "restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap" >> /etc/ntp.conf
sudo /etc/init.d/ntp restart
```

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

## k3s
- [k3s.io](https://k3s.io)
- [Docs](https://rancher.com/docs/k3s/latest/en/quick-start/)
- [K3S on Raspberry Pi](https://www.puzzle.ch/de/blog/articles/2020/10/13/k3s-on-raspberry-pi)
- [High Availibility cluster](https://w-goutas.medium.com/set-up-a-kubernetes-cluster-in-minutes-41a0bd65ab93)
- [arm_64bit](https://www.raspberrypi.org/documentation/configuration/config-txt/boot.md)

### [Enabling cgroups](https://rancher.com/docs/k3s/latest/en/advanced/#enabling-cgroups-for-raspbian-buster)
Append `cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory` to `/boot/cmdline.txt`

Append `arm_64bit=1` to `/boot/config.txt` under `[all]`

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

### HA cluster installation
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
kubectl config view --raw >~/.kube/config
sudo chmod go-r ~/.kube/config
```

### [k9s](https://github.com/derailed/k9s) installation
```
K9S_VERSION=$(curl -sL https://api.github.com/repos/derailed/k9s/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
curl -sL "https://github.com/derailed/k9s/releases/download/$K9S_VERSION/k9s_Linux_arm.tar.gz" | tar xz k9s
sudo install -m 755 k9s /usr/local/bin/k9s
rm k9s
```
