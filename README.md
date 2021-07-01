# pi cluster

## Ubuntu configuration

### ssh
`ssh ubuntu:ubuntu@<IP>`

### Set default editor
`sudo update-alternatives --set editor /usr/bin/vim.basic`

### Create a new user
`sudo adduser oleg`

### Sudoers
```
sudo adduser oleg sudo
sudo visudo /etc/sudoers.d/90-cloud-init-users
	=> oleg ALL=(ALL) NOPASSWD: ALL
```
### Delete ubuntu user
`sudo userdel -r ubuntu`

### Disable welcome message
`sudo chmod -x /etc/update-motd.d/*`

### Change hostname
```
hostnamectl
sudo hostnamectl set-hostname pi4
```

### Disable systemd-resolved
[Installing on Ubuntu](https://github.com/pi-hole/docker-pi-hole#installing-on-ubuntu)
```
sudo sed -r -i.orig 's/#?DNSStubListener=yes/DNSStubListener=no/g' /etc/systemd/resolved.conf
sudo sh -c 'rm /etc/resolv.conf && ln -s /run/systemd/resolve/resolv.conf /etc/resolv.conf'
sudo systemctl restart systemd-resolved
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

### [Enabling cgroups](https://rancher.com/docs/k3s/latest/en/advanced/#enabling-cgroups-for-raspbian-buster)
Append `cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory` to `/boot/firmware/cmdline.txt`

### Master installation/upgrade
`ctrl+x ctrl+e`
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_EXEC=" --disable servicelb --disable traefik"
export INSTALL_K3S_VERSION="v1.21.2+k3s1"
curl -sfL https://get.k3s.io | sh -
```
### Node installation/upgrade
On master `sudo cat /var/lib/rancher/k3s/server/node-token`
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.21.2+k3s1"
export K3S_URL="https://192.168.1.4:6443"
export K3S_TOKEN="XXXX"
curl -sfL https://get.k3s.io | sh -
```
### [Helm](https://helm.sh) [installation](https://helm.sh/docs/intro/install/)
`curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash`

#### Helm configuration
```
kubectl config view --raw >~/.kube/config
sudo chmod go-r ~/.kube/config
```

### [Sealed-secrets](https://github.com/bitnami-labs/sealed-secrets) controller installation
```
$ kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.16.0/controller.yaml
```
#### kubeseal instalation
```
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.16.0/kubeseal-arm -O kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
rm kubeseal
```

### [k9s](https://github.com/derailed/k9s) installation
```
curl -sL https://github.com/derailed/k9s/releases/download/v0.24.13/k9s_Linux_arm.tar.gz | tar xz k9s
sudo install -m 755 k9s /usr/local/bin/k9s
rm k9s
```
