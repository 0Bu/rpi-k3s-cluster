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
   prefix fd::/64 {};
};
```

### Add static IPv6 ULA
`sudo vim /etc/network/interfaces.d/ipv6-static`
add
```
auto eth0
iface eth0 inet6 static
    address fd00:5::1
    netmask 64
```

### [k3s dual-stack installation](https://docs.k3s.io/installation/network-options#dual-stack-installation)
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_EXEC="--disable servicelb --disable traefik --node-ip 192.168.1.5,fd00:5::1 --cluster-cidr 10.42.0.0/16,fd10::/56 --service-cidr 10.43.0.0/16,fd20::/112 --flannel-ipv6-masq"
export INSTALL_K3S_VERSION=$(curl -sL https://api.github.com/repos/k3s-io/k3s/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
curl -sfL https://get.k3s.io | sh -
```
