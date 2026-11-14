# Installing [k3s](https://k3s.io) on [Raspberry Pi OS](https://www.raspberrypi.com/software/operating-systems/)

## Host tuning and GitOps

The network settings below use example addresses. Substitute your own subnets
and node addresses before applying them.

### Kubelet memory protection

Add `/var/lib/rancher/k3s/agent/etc/kubelet.conf.d/90-memory-protection.conf`.
Size the reserves for your node. This example reserves 2 GiB for the OS and
Kubernetes and sets a 512 MiB memory eviction threshold. [K3s kubelet configuration](https://docs.k3s.io/installation/configuration#kubelet-configuration-files)

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
systemReserved:
  memory: 512Mi
kubeReserved:
  memory: 1536Mi
evictionHard:
  memory.available: 512Mi
  imagefs.available: 5%
  nodefs.available: 5%
```

Restart k3s during maintenance. Check the node is `Ready` and verify the
effective settings at `/api/v1/nodes/<node>/proxy/configz`.

### Swap and host journal

- **Swap**. On Raspberry Pi OS with `rpi-swap`, set `Mechanism=none` under
  `[Main]` in `/etc/rpi/swap.conf.d/99-disable-swap.conf`. Reboot and check
  that `cat /proc/swaps` lists no devices.
- **Journal**. In `/etc/systemd/journald.conf.d/90-persistent.conf`, set
  `Storage=persistent`, `SystemMaxUse=128M`, and `RuntimeMaxUse=32M` under
  `[Journal]`. Restart `systemd-journald` and run `sudo journalctl --flush`.
  Use `sudo journalctl -k -b -1` to read the previous boot's kernel log.

### On-demand workloads

[KEDA](argocd/templates/keda.yaml) starts Grafana and the VictoriaMetrics and
VictoriaLogs MCP services on HTTP requests. Each scales from zero to one
replica and returns to zero after 180 seconds without requests. The HTTP
interceptor waits up to 60 seconds for readiness. Open streams and background
requests can keep a pod running. Grafana uses persistent storage, and
`vmalert` evaluates alerts independently.

Check replicas with `kubectl -n default get scaledobject,deploy` and request
Grafana's `/api/health` to test a cold start.

### Related configuration

- [VictoriaMetrics](victoria-metrics/values.yaml) sets the database resources,
  cache and query limits, and VMAgent resources.
- [Grafana](argocd/templates/grafana.yaml) and
  [Sealed Secrets](argocd/templates/sealed-secrets.yaml) use upstream Helm charts
  tracked by Renovate. [Back up the sealing keys](https://github.com/bitnami/sealed-secrets#how-can-i-do-a-backup-of-my-sealedsecrets) before rebuilding a cluster.
- **Forgejo** is disabled. Set `forgejo.enabled: true` in
  [argocd/values.yaml](argocd/values.yaml) to deploy it. Keep the retained volume
  and database for recovery. [PostgreSQL restore procedure](postgresql/README.md#restoring-another-database)

### Enable cgroups
- append `cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory` to `/boot/firmware/cmdline.txt`
- *optional*: append `arm_64bit=1` to `/boot/config.txt` under `[all]` on 32-bit Raspberry Pi OS ([arm_64bit](https://www.raspberrypi.com/documentation/computers/config_txt.html#arm_64bit))

## [NFS](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-nfs-mount-on-ubuntu-20-04)
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
/nfs 192.0.2.0/24(rw,async,no_subtree_check,no_root_squash)
```
An `async` export can lose pending writes during power loss.
[PostgreSQL backup and restore](postgresql/README.md#backup-and-restore)

```
sudo systemctl restart nfs-kernel-server
```

#### NFS client mount
```
sudo mkdir /mnt/nfs
sudo mount <HOST_IP>:/nfs /mnt/nfs
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
   prefix fd00:1234:5678::/64 {};
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
Address=fd00:1234:5678::10/64
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
node-ip: "192.0.2.10,fd00:1234:5678::10"
cluster-cidr: "10.244.0.0/16,fd00:244::/56"
service-cidr: "10.96.0.0/16,fd00:96::/112"
flannel-ipv6-masq: true
kubelet-arg:
  - "image-gc-high-threshold=70"
  - "image-gc-low-threshold=60"
```

```
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.37.2+k3s1" sh -
```

### Node installation
Get master token
`sudo cat /var/lib/rancher/k3s/server/node-token`

```
sudo mkdir -p /etc/rancher/k3s
sudo vim /etc/rancher/k3s/config.yaml
```

```
server: "https://192.0.2.10:6443"
token: "TOKEN"
write-kubeconfig-mode: "644"
node-ip: "192.0.2.11,fd00:1234:5678::11"
kubelet-arg:
  - "image-gc-high-threshold=70"
  - "image-gc-low-threshold=60"
```

```
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.37.2+k3s1" sh -
```

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
node-ip: "192.0.2.10,fd00:1234:5678::10"
cluster-cidr: "10.244.0.0/16,fd00:244::/56"
service-cidr: "10.96.0.0/16,fd00:96::/112"
flannel-ipv6-masq: true
kubelet-arg:
  - "image-gc-high-threshold=70"
  - "image-gc-low-threshold=60"
```

```
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.37.2+k3s1" sh -
```

### High availability node installation
```
sudo mkdir -p /etc/rancher/k3s
sudo vim /etc/rancher/k3s/config.yaml
```

```
server: https://192.0.2.10:6443
token: "TOKEN"
write-kubeconfig-mode: "644"
disable:
  - servicelb
node-ip: "192.0.2.11,fd00:1234:5678::11"
cluster-cidr: "10.244.0.0/16,fd00:244::/56"
service-cidr: "10.96.0.0/16,fd00:96::/112"
flannel-ipv6-masq: true
kubelet-arg:
  - "image-gc-high-threshold=70"
  - "image-gc-low-threshold=60"
```

```
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.37.2+k3s1" sh -
```

## Single stack installation
k3s docs: <https://docs.k3s.io/installation>
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.37.2+k3s1"
export INSTALL_K3S_EXEC="--disable servicelb --kubelet-arg image-gc-high-threshold=70 --kubelet-arg image-gc-low-threshold=60"
curl -sfL https://get.k3s.io | sh -
```

### Node installation
On master 
```
sudo cat /var/lib/rancher/k3s/server/node-token
```

```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_VERSION="v1.37.2+k3s1"
export INSTALL_K3S_EXEC="--kubelet-arg image-gc-high-threshold=70 --kubelet-arg image-gc-low-threshold=60"
export K3S_URL="https://192.0.2.10:6443"
export K3S_TOKEN="TOKEN"
curl -sfL https://get.k3s.io | sh -
```

### [Helm](https://helm.sh) installation
```
curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash
```

#### Helm configuration
```
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```
or
```
mkdir -p ~/.kube
kubectl config view --raw > ~/.kube/config
sudo chmod go-r ~/.kube/config
```

### [k9s](https://github.com/derailed/k9s) installation
```
curl -sLO "https://github.com/derailed/k9s/releases/download/v0.51.0/k9s_linux_arm.deb"
sudo dpkg -i k9s_linux_arm.deb
rm k9s_linux_arm.deb
```

