#!/usr/bin/env python3
"""
NetSage AI — Deterministic Rule Checker
========================================
Runs independently of the AI model. Scans a structured snapshot of the lab
network (interfaces, hosts, VLANs, DHCP pools, static routes) and flags
common Cisco-style config mistakes with 100% reproducible, rule-based logic.

Intended use in the NetSage AI pipeline:
  - Run BEFORE AI diagnosis, to hand the model pre-flagged evidence.
  - Run AFTER AI diagnosis, as an independent cross-check on the AI's
    root_cause — if the AI blames something this checker did not flag (or
    vice versa), that's a signal for the human reviewer to look closer.

Checks implemented:
  1. Duplicate IP addresses (host-vs-host, host-vs-gateway)
  2. Wrong / mismatched subnet masks within the same VLAN
  3. Gateway mismatch (host's configured gateway != router's real interface IP)
  4. Interfaces that are down / administratively down
  5. Missing VLANs (referenced by a port or sub-interface but never created)
  6. Missing static routes to networks named in the topology as reachable

Usage:
    python3 rule_checker.py            # runs the built-in demo lab snapshot
"""

from __future__ import annotations
import ipaddress
import json
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------
# Data model — a simplified structured snapshot of a Packet Tracer lab.
# In a real pipeline this would be produced by parsing 'show' command output;
# here it is provided directly so the checker's logic can be demonstrated
# and unit-tested independently of a text parser.
# --------------------------------------------------------------------------

@dataclass
class Interface:
    device: str
    name: str
    ip: Optional[str] = None
    mask: Optional[str] = None
    status: str = "up"           # up | down | administratively down
    vlan: Optional[int] = None   # for switch access ports
    mode: str = "routed"         # routed | access | trunk


@dataclass
class Host:
    name: str
    ip: str
    mask: str
    gateway: str
    vlan: int


@dataclass
class Route:
    device: str
    network: str
    mask: str
    next_hop: str


@dataclass
class VlanDB:
    device: str
    vlans: set = field(default_factory=set)


# --------------------------------------------------------------------------
# Demo lab snapshot (mirrors several cases from cases.csv: C001, C005, C006,
# C008, C009's neighbor C012, C017 and C004, to show real detections)
# --------------------------------------------------------------------------

def demo_lab_snapshot():
    interfaces = [
        Interface("R1", "Gi0/0.10", ip="192.168.10.1", mask="255.255.255.0", status="up"),
        Interface("R1", "Gi0/0.20", ip="192.168.20.1", mask="255.255.255.0", status="administratively down"),
        Interface("R1", "Gi0/0.30", ip="192.168.30.1", mask="255.255.255.0", status="up"),
        Interface("R1", "Gi0/0.40", ip="192.168.40.1", mask="255.255.255.0", status="up"),  # VLAN 40 never created on switch
        Interface("R1", "Serial0/0/0", ip="172.16.10.1", mask="255.255.255.252", status="up"),
        Interface("SW1", "Fa0/2", vlan=10, mode="access", status="up"),
        Interface("SW1", "Fa0/3", vlan=20, mode="access", status="up"),  # should be VLAN 10 -> mismatch case C001
    ]

    hosts = [
        Host("PC1", "192.168.10.50", "255.255.255.0", "192.168.10.1", vlan=10),
        Host("PC2", "192.168.10.51", "255.255.255.0", "192.168.10.1", vlan=10),
        Host("PC3", "192.168.30.55", "255.255.255.0", "192.168.30.254", vlan=30),  # wrong gateway -> C007
        Host("PC5", "192.168.10.1",  "255.255.255.0", "192.168.10.1", vlan=10),   # duplicate of gateway -> C008
        Host("PC6", "192.168.20.60", "255.255.255.255", "192.168.20.1", vlan=20),  # wrong mask -> should be /24
        Host("PC7", "192.168.20.61", "255.255.255.0", "192.168.20.1", vlan=20),   # correct mask peer, for comparison
    ]

    routes = [
        Route("R1", "192.168.10.0", "255.255.255.0", "connected"),
        Route("R1", "192.168.30.0", "255.255.255.0", "connected"),
        # 172.16.0.0/24 (server subnet reachable via R2) is intentionally MISSING -> C017
    ]

    vlan_dbs = [
        VlanDB("SW1", vlans={1, 10, 20, 30}),  # VLAN 40 missing -> C004
    ]

    # Networks the topology notes claim should be reachable from R1
    expected_reachable_networks = ["192.168.10.0/24", "192.168.20.0/24",
                                    "192.168.30.0/24", "172.16.0.0/24"]

    return interfaces, hosts, routes, vlan_dbs, expected_reachable_networks


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_duplicate_ips(hosts: list[Host], interfaces: list[Interface]) -> list[dict]:
    findings = []
    seen: dict[str, list[str]] = {}
    for h in hosts:
        seen.setdefault(h.ip, []).append(h.name)
    for iface in interfaces:
        if iface.ip:
            seen.setdefault(iface.ip, []).append(f"{iface.device}:{iface.name}")
    for ip, owners in seen.items():
        if len(owners) > 1:
            findings.append({
                "check": "duplicate_ip",
                "severity": "High",
                "detail": f"IP {ip} is claimed by more than one device: {', '.join(owners)}",
            })
    return findings


def check_wrong_masks(hosts: list[Host]) -> list[dict]:
    """Flags hosts whose mask doesn't match the majority mask seen for their VLAN."""
    findings = []
    by_vlan: dict[int, list[Host]] = {}
    for h in hosts:
        by_vlan.setdefault(h.vlan, []).append(h)
    for vlan, members in by_vlan.items():
        masks = [m.mask for m in members]
        common = max(set(masks), key=masks.count)
        for h in members:
            if h.mask != common:
                findings.append({
                    "check": "wrong_mask",
                    "severity": "Medium",
                    "detail": (f"{h.name} in VLAN {vlan} uses mask {h.mask}, "
                               f"which differs from the common mask {common} used by its peers."),
                })
    return findings


def check_gateway_mismatch(hosts: list[Host], interfaces: list[Interface]) -> list[dict]:
    findings = []
    router_ips = {iface.ip for iface in interfaces if iface.ip}
    # Build map of subnet -> actual router IP in that subnet
    subnet_gateway: dict[str, str] = {}
    for iface in interfaces:
        if iface.ip and iface.mask:
            net = ipaddress.ip_network(f"{iface.ip}/{iface.mask}", strict=False)
            subnet_gateway[str(net)] = iface.ip

    for h in hosts:
        try:
            host_net = ipaddress.ip_network(f"{h.ip}/{h.mask}", strict=False)
        except ValueError:
            continue
        actual_gw = subnet_gateway.get(str(host_net))
        if actual_gw and h.gateway != actual_gw:
            findings.append({
                "check": "gateway_mismatch",
                "severity": "Medium",
                "detail": (f"{h.name} is configured with gateway {h.gateway}, but the router's "
                           f"real interface in {host_net} is {actual_gw}."),
            })
    return findings


def check_interfaces_down(interfaces: list[Interface]) -> list[dict]:
    findings = []
    for iface in interfaces:
        if iface.status != "up":
            findings.append({
                "check": "interface_down",
                "severity": "Critical" if "administratively" in iface.status else "High",
                "detail": f"{iface.device}:{iface.name} is {iface.status}.",
            })
    return findings


def check_missing_vlans(interfaces: list[Interface], vlan_dbs: list[VlanDB]) -> list[dict]:
    findings = []
    switch_vlans: dict[str, set] = {db.device: db.vlans for db in vlan_dbs}
    # Sub-interfaces like Gi0/0.40 imply VLAN 40 should exist on the connected switch(es)
    for iface in interfaces:
        if "." in iface.name:
            try:
                implied_vlan = int(iface.name.split(".")[-1])
            except ValueError:
                continue
            for switch, vlans in switch_vlans.items():
                if implied_vlan not in vlans:
                    findings.append({
                        "check": "missing_vlan",
                        "severity": "High",
                        "detail": (f"{iface.device}:{iface.name} implies VLAN {implied_vlan}, "
                                   f"but VLAN {implied_vlan} does not exist on {switch}."),
                    })
        if iface.mode == "access" and iface.vlan is not None:
            for switch, vlans in switch_vlans.items():
                if iface.device == switch and iface.vlan not in vlans:
                    findings.append({
                        "check": "missing_vlan",
                        "severity": "High",
                        "detail": f"{iface.device}:{iface.name} is assigned to VLAN {iface.vlan}, which is not in the VLAN database.",
                    })
    return findings


def check_missing_routes(routes: list[Route], expected_networks: list[str]) -> list[dict]:
    findings = []
    known = {ipaddress.ip_network(f"{r.network}/{r.mask}") for r in routes}
    for net_str in expected_networks:
        net = ipaddress.ip_network(net_str)
        if net not in known:
            findings.append({
                "check": "missing_route",
                "severity": "High",
                "detail": f"No route found for expected network {net} — check for a missing static/dynamic route.",
            })
    return findings


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def run_all_checks():
    interfaces, hosts, routes, vlan_dbs, expected_networks = demo_lab_snapshot()

    all_findings = []
    all_findings += check_duplicate_ips(hosts, interfaces)
    all_findings += check_wrong_masks(hosts)
    all_findings += check_gateway_mismatch(hosts, interfaces)
    all_findings += check_interfaces_down(interfaces)
    all_findings += check_missing_vlans(interfaces, vlan_dbs)
    all_findings += check_missing_routes(routes, expected_networks)

    return all_findings


def print_report(findings: list[dict]):
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    findings_sorted = sorted(findings, key=lambda f: order.get(f["severity"], 9))

    print("=" * 72)
    print("NetSage AI — Rule Checker Report")
    print("=" * 72)
    if not findings_sorted:
        print("No deterministic rule violations found.")
        return
    for i, f in enumerate(findings_sorted, 1):
        print(f"[{i}] ({f['severity']}) {f['check']}")
        print(f"     {f['detail']}")
    print("-" * 72)
    counts = {}
    for f in findings_sorted:
        counts[f["check"]] = counts.get(f["check"], 0) + 1
    print("Summary by check type:", json.dumps(counts, indent=2))
    print(f"Total findings: {len(findings_sorted)}")


if __name__ == "__main__":
    findings = run_all_checks()
    print_report(findings)
