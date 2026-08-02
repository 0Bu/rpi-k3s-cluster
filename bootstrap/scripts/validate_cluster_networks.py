#!/usr/bin/env python3
"""Reject unsafe or overlapping dual-stack cluster network declarations."""

from __future__ import annotations

import ipaddress
import pathlib
import sys
import urllib.parse

import yaml


def fail(message: str) -> None:
    raise SystemExit(f"network validation failed: {message}")


def networks(values: dict[str, object], key: str) -> list[ipaddress._BaseNetwork]:
    result = [ipaddress.ip_network(str(value)) for value in values[key]]
    if {network.version for network in result} != {4, 6}:
        fail(f"{key} must contain exactly one IPv4 and one IPv6 network")
    return result


def main() -> None:
    inventory_path = pathlib.Path(sys.argv[1])
    values_path = pathlib.Path(sys.argv[2])
    inventory = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))["all"]
    values = yaml.safe_load(values_path.read_text(encoding="utf-8"))

    children = inventory["children"]
    servers = children["k3s_servers"]["hosts"]
    agents = children["k3s_agents"]["hosts"]
    hosts = servers | agents
    expected_nodes = set(values["cluster_expected_nodes"])

    if len(servers) != 1 or set(servers) != {values["cluster_server_host"]}:
        fail("inventory must contain exactly the declared server")
    if not agents or set(hosts) != expected_nodes:
        fail("inventory hosts must exactly match cluster_expected_nodes")

    protected = {ipaddress.ip_address(value) for value in values["protected_ipv4_addresses"]}
    lan = ipaddress.ip_network(values["k3s_lan_ipv6_cidr"])
    if lan.version != 6 or lan.prefixlen != 64:
        fail("k3s_lan_ipv6_cidr must be the declared IPv6 /64")

    seen_v4: set[ipaddress._BaseAddress] = set()
    seen_v6: set[ipaddress._BaseAddress] = set()
    for hostname, host in hosts.items():
        address4 = ipaddress.ip_address(host["expected_ipv4"])
        address6 = ipaddress.ip_address(host["expected_ipv6"])
        if host["expected_hostname"] != hostname:
            fail(f"hostname mismatch for {hostname}")
        if address4 in protected:
            fail(f"protected production address used by {hostname}")
        if address6 not in lan:
            fail(f"{hostname} IPv6 address is outside {lan}")
        if address4 in seen_v4 or address6 in seen_v6:
            fail("node addresses must be unique")
        seen_v4.add(address4)
        seen_v6.add(address6)

    pod_networks = networks(values, "k3s_cluster_cidrs")
    service_networks = networks(values, "k3s_service_cidrs")
    declared = pod_networks + service_networks
    for index, first in enumerate(declared):
        for second in declared[index + 1 :]:
            if first.version == second.version and first.overlaps(second):
                fail(f"{first} overlaps {second}")
    for network in declared:
        if network.version == 6 and network.overlaps(lan):
            fail(f"cluster network {network} overlaps node LAN {lan}")

    pod6 = next(network for network in pod_networks if network.version == 6)
    service6 = next(network for network in service_networks if network.version == 6)
    mask6 = int(values["k3s_node_cidr_mask_size_ipv6"])
    if not pod6.prefixlen < mask6 <= 120:
        fail("IPv6 per-node mask must be narrower than the pod network")
    if service6.prefixlen > 112:
        fail("IPv6 Service CIDR must not be narrower than /112")

    dns_addresses = [ipaddress.ip_address(value) for value in values["k3s_cluster_dns"]]
    if {address.version for address in dns_addresses} != {4, 6}:
        fail("cluster DNS must contain one address per family")
    for address in dns_addresses:
        family_services = [network for network in service_networks if network.version == address.version]
        if not any(address in network for network in family_services):
            fail(f"DNS address {address} is outside its Service CIDR")

    api_host = urllib.parse.urlparse(values["cluster_api_url"]).hostname
    if api_host != values["cluster_server_ipv4"]:
        fail("cluster_api_url must use the declared server IPv4")
    if ipaddress.ip_address(values["cluster_server_ipv6"]) not in lan:
        fail("cluster server IPv6 must belong to the node LAN")

    print(
        f"validated server={next(iter(servers))} agents={','.join(sorted(agents))} "
        f"lan={lan} pods={','.join(map(str, pod_networks))} "
        f"services={','.join(map(str, service_networks))}"
    )


if __name__ == "__main__":
    main()
