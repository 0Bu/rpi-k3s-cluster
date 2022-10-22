# Dual-stack installation

### Router Advertisement Daemon installation
```
sudo apt update
sudo apt install -y radvd
```

### [radvd configuration](https://linux.die.net/man/5/radvd.conf)
`sudo vim /etc/radvd.conf`
```
interface eth0 {
   AdvSendAdvert on;
   MaxRtrAdvInterval 60;
   prefix fd::/64 {};
};
```

### Add static IPv6 ULA for RA, [dhcpcd](https://www.daemon-systems.org/man/dhcpcd.conf.5.html)
`sudo vim /etc/dhcpcd.conf` add `static ip6_address=fd::ff/64`

### [k3s dual-stack installation](https://docs.k3s.io/installation/network-options#dual-stack-installation)
```
export K3S_KUBECONFIG_MODE="644"
export INSTALL_K3S_EXEC="--disable servicelb --disable traefik --node-ip 192.168.1.4,fd::ff --cluster-cidr 10.42.0.0/16,fd42::/56 --service-cidr 10.43.0.0/16,fd43::/112 --flannel-ipv6-masq"
export INSTALL_K3S_VERSION=$(curl -sL https://api.github.com/repos/k3s-io/k3s/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
curl -sfL https://get.k3s.io | sh -
```
