# Installing [k3s](https://k3s.io) on [Raspberry Pi OS](https://www.raspberrypi.com/software/operating-systems/)

## Production settings on `pi5a`

`pi5a` is the single production k3s node. Argo CD manages the applications and
their routes. The kubelet, swap, and journal settings below are host drop-ins.
Reapply them when rebuilding the node.

### Kubelet memory protection

Create `/var/lib/rancher/k3s/agent/etc/kubelet.conf.d/90-memory-protection.conf`
with the following contents. [K3s kubelet configuration](https://docs.k3s.io/installation/configuration#kubelet-configuration-files)

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

The reservations account for 2 GiB of host and Kubernetes memory when
scheduling pods. The kubelet starts reclaiming resources when its available
memory falls below 512 MiB. The two filesystem thresholds retain the existing
5% settings. The k3s service configuration also starts image garbage collection
at 70% usage and targets 60%. [Kubernetes node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)

Restart k3s in a maintenance window to apply the drop-in. The API is briefly
unavailable on this single-node cluster. After the restart, check the effective
settings and node conditions.

```sh
sudo systemctl restart k3s
sudo k3s kubectl wait --for=condition=Ready node/pi5a --timeout=120s
sudo k3s kubectl get --raw /api/v1/nodes/pi5a/proxy/configz \
  | jq '.kubeletconfig | {systemReserved, kubeReserved, evictionHard}'
sudo k3s kubectl describe node pi5a
```

### Swap and host journal

Create `/etc/rpi/swap.conf.d/99-disable-swap.conf` to disable the Raspberry Pi
OS swap generator's swap setup, including zram. Schedule a reboot to apply it
on a freshly configured host. The generator also schedules removal of the old
swap backing file. See `man 5 swap.conf` on Raspberry Pi OS.

```ini
[Main]
Mechanism=none
```

Create `/etc/systemd/journald.conf.d/90-persistent.conf` to retain kernel and
service logs across reboots. The persistent journal is capped at 128 MiB and
the runtime journal at 32 MiB. [systemd journal configuration](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html)

```ini
[Journal]
Storage=persistent
SystemMaxUse=128M
RuntimeMaxUse=32M
```

Restart journald and flush its runtime journal to disk. Verify the persistent
journal and check that `/proc/swaps` contains only its header and that the zram
units are inactive.

```sh
sudo systemctl restart systemd-journald
sudo journalctl --flush
sudo journalctl --directory=/var/log/journal --list-boots
sudo journalctl --disk-usage
cat /proc/swaps
systemctl show -p Id -p ActiveState \
  dev-zram0.swap systemd-zram-setup@zram0.service rpi-zram-writeback.timer
```

After a future reboot, use `sudo journalctl -k -b -1` to inspect the previous
boot's kernel log.

### HTTP workloads that start on demand

The Argo CD root chart declares KEDA, the HTTP Add-on, and all three workloads
in [argocd/templates/keda.yaml](argocd/templates/keda.yaml). The single-node
installation runs one HTTP interceptor and one external scaler. Traefik
forwards HTTPS requests to the interceptor, which waits up to 60 seconds for
the backend to become ready before forwarding the first request. Each workload
scales from zero to one replica and returns to zero after 180 seconds without
traffic. An open connection or periodic client requests can keep it running.
[KEDA HTTP scaling](https://keda.sh/http-add-on/0.16/concepts/scaling/)

| Workload | HTTPS endpoint |
| --- | --- |
| Grafana | `https://grafana.burau.dev/` |
| VictoriaMetrics MCP | `https://mcp-vm.burau.dev/mcp` |
| VictoriaLogs MCP | `https://mcp-logs.burau.dev/mcp` |

Grafana keeps dashboards and settings on its existing NFS claim. It uses a
single pod with the `Recreate` strategy. The upstream Helm release, data
sources, NFS volume and claim, and sealed admin credentials are defined in
[argocd/templates/grafana.yaml](argocd/templates/grafana.yaml). Renovate tracks
the Helm versions in the Grafana, KEDA, and Sealed Secrets Argo CD Applications. Keep alert
evaluation in `vmalert` and delivery in Alertmanager so alerts continue while
Grafana is idle. The VictoriaMetrics and VictoriaLogs databases and their
ingestion paths run independently of the MCP pods. MCP clients may need to
initialize a new session after a pod scales down.

To verify a Grafana cold start, first confirm `spec.replicas` is zero, then
request `/api/health`. A cold start returns `X-KEDA-HTTP-Cold-Start: true` and
Grafana should report `"database": "ok"`. For MCP, send an `initialize` request
to `/mcp` with an MCP client. Check the replica counts again after the cooldown.

```sh
kubectl -n default get applications keda keda-add-ons-http grafana victoria-metrics victoria-logs
kubectl -n default get scaledobject grafana victoria-metrics-mcp victoria-logs-mcp
kubectl -n default get deployment grafana victoria-metrics-mcp victoria-logs-mcp
curl --fail --silent --show-error --include --max-time 65 https://grafana.burau.dev/api/health
```

For Grafana admin password recovery, start the pod through its HTTPS endpoint
and follow the [Grafana CLI reset procedure](https://grafana.com/docs/grafana/latest/administration/cli/#reset-admin-password).
Update the sealed admin credentials in the Application when rotating the password.

### VictoriaMetrics resources and retired workloads

The VictoriaMetrics database has matching requests and limits of 1.2 CPU cores
and 1500 MiB of RAM and uses the `victoria-metrics-storage` PriorityClass. Its
cache budget is 600 MiB. It allows two concurrent search requests, with a
192 MiB query memory budget and a limit of 1,572,864 unique time series per
query. `vmagent` uses streaming scrape parsing, a 50m CPU request with no CPU
limit, and a 500 MiB memory limit. [VictoriaMetrics chart settings](victoria-metrics/values.yaml)

Forgejo and its Actions runner were retired from the production Argo CD root.
The Forgejo chart remains available for recovery. The retained NFS volume holds
the repository and package files, and the shared PostgreSQL instance retains
the Forgejo database. [Forgejo deployment and restore notes](forgejo/README.md)

### Sealed Secrets

The [Sealed Secrets Application](argocd/templates/sealed-secrets.yaml) installs
the upstream Helm chart in `kube-system`. Its controller is named
`sealed-secrets-controller`, which is the default name expected by `kubeseal`.
The controller stores its sealing keys as Secrets in that namespace. Back up
all keys to protected storage and restore them before starting the controller
on a replacement cluster. [Sealed Secrets installation and key recovery](https://github.com/bitnami/sealed-secrets#how-can-i-do-a-backup-of-my-sealedsecrets)

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
/nfs 192.168.1.0/24(rw,async,no_subtree_check,no_root_squash)
```
The `async` export reduces initialization time on the DRAM-less NVMe, where
`fsync` latency was measured at around 370 ms and synchronous initialization
took over 15 minutes. A power loss can discard pending writes. PostgreSQL
creates a daily logical backup. [PostgreSQL backup and restore](postgresql/README.md#backup-and-restore)
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
server: "https://192.168.1.5:6443"
token: "TOKEN"
write-kubeconfig-mode: "644"
node-ip: "192.168.1.5,fd7c:3b4a:5f1d::5a"
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
node-ip: "192.168.1.5,fd7c:3b4a:5f1d::5a"
cluster-cidr: "10.42.0.0/16,fd00:10:42::/56"
service-cidr: "10.43.0.0/16,fd00:10:43::/112"
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
server: https://192.168.1.5:6443
token: "TOKEN"
write-kubeconfig-mode: "644"
disable:
  - servicelb
node-ip: "192.168.1.15,fd7c:3b4a:5f1d::5b"
cluster-cidr: "10.42.0.0/16,fd00:10:42::/56"
service-cidr: "10.43.0.0/16,fd00:10:43::/112"
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
export K3S_URL="https://192.168.1.5:6443"
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

