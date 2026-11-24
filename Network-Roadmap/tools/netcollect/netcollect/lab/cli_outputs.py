"""Generate realistic Cisco IOS-XE 'show' outputs from a lab device description.

The text follows the real command layout closely enough for the ntc-templates
TextFSM parsers used by Netmiko (verified by the lab self-test).
"""
from __future__ import annotations

import ipaddress
from typing import Any

SHORT = {"GigabitEthernet": "Gi", "TenGigabitEthernet": "Te", "TwentyFiveGigE": "Twe", "Vlan": "Vl",
         "Port-channel": "Po", "Loopback": "Lo"}


def short_name(name: str) -> str:
    for long, short in SHORT.items():
        if name.startswith(long):
            return short + name[len(long):]
    return name


def _mask(prefix: int) -> str:
    return str(ipaddress.ip_network(f"0.0.0.0/{prefix}").netmask)


def show_version(dev: dict[str, Any]) -> str:
    v = dev["version"]
    serials = dev["serials"]
    model = dev["model"]
    lines = [
        f"Cisco IOS XE Software, Version {v}",
        f"Cisco IOS Software [Cupertino], Catalyst L3 Switch Software (CAT9K_IOSXE), Version {v}, "
        "RELEASE SOFTWARE (fc3)",
        "Technical Support: http://www.cisco.com/techsupport",
        "Copyright (c) 1986-2024 by Cisco Systems, Inc.",
        "Compiled Thu 25-Jan-24 12:00 by mcpre",
        "",
        "ROM: IOS-XE ROMMON",
        "BOOTLDR: System Bootstrap, Version 17.9.1r, RELEASE SOFTWARE (P)",
        "",
        f"{dev['name']} uptime is {dev.get('uptime_text', '2 weeks, 3 days, 4 hours, 12 minutes')}",
        "Uptime for this control processor is 2 weeks, 3 days, 4 hours, 14 minutes",
        "System returned to ROM by Reload Command",
        'System image file is "flash:packages.conf"',
        "Last reload reason: Reload Command",
        "",
        f"cisco {model} (X86) processor with 1419044K/6147K bytes of memory.",
        f"Processor board ID {serials[0]}",
        "2048K bytes of non-volatile configuration memory.",
        "8388608K bytes of physical memory.",
        "",
        "Base Ethernet MAC Address          : 70:0f:6a:00:00:01",
        f"Motherboard Serial Number          : {serials[0]}",
        f"Model Number                       : {model}",
        f"System Serial Number               : {serials[0]}",
        "",
        "Switch Ports Model              SW Version        SW Image              Mode",
        "------ ----- -----              ----------        ----------            ----",
    ]
    for i, _ in enumerate(serials, 1):
        star = "*" if i == 1 else " "
        lines.append(f"{star}    {i} 65    {model:<18} {v:<17} CAT9K_IOSXE           INSTALL")
    lines += ["", "Configuration register is 0x102", ""]
    return "\n".join(lines)


def show_ip_int_brief(dev: dict[str, Any]) -> str:
    lines = ["Interface              IP-Address      OK? Method Status                Protocol"]
    for i in dev["interfaces"]:
        ip = i["ip"].split("/")[0] if i.get("ip") else "unassigned"
        method = "NVRAM" if i.get("ip") else "unset"
        status = {"up": "up", "down": "down", "admin-down": "administratively down"}[i["status"]]
        proto = "up" if i["status"] == "up" else "down"
        lines.append(f"{i['name']:<23}{ip:<16}YES {method:<7}{status:<22}{proto}")
    return "\n".join(lines)


def show_interfaces(dev: dict[str, Any]) -> str:
    blocks = []
    for n, i in enumerate(dev["interfaces"], 1):
        status = {"up": "up", "down": "down", "admin-down": "administratively down"}[i["status"]]
        proto = "up" if i["status"] == "up" else "down"
        hw = "Ethernet SVI" if i["name"].startswith("Vlan") else "Gigabit Ethernet"
        mac = f"700f.6a00.{n:04x}"
        crc = int(i.get("crc", 0))
        duplex = i.get("duplex", "Full")
        speed = i.get("speed", "1000")
        b = [f"{i['name']} is {status}, line protocol is {proto} {'(connected)' if proto == 'up' else '(notconnect)'}",
             f"  Hardware is {hw}, address is {mac} (bia {mac})"]
        if i.get("description"):
            b.append(f"  Description: {i['description']}")
        if i.get("ip"):
            addr, plen = i["ip"].split("/")
            b.append(f"  Internet address is {addr}/{plen}")
        b += [
            f"  MTU 1500 bytes, BW {int(speed) * 1000 if str(speed).isdigit() else 1000000} Kbit/sec, DLY 10 usec,",
            "     reliability 255/255, txload 1/255, rxload 1/255",
            "  Encapsulation ARPA, loopback not set",
            "  Keepalive set (10 sec)",
            f"  {duplex}-duplex, {speed}Mb/s, media type is 10/100/1000BaseTX",
            "  input flow-control is on, output flow-control is unsupported",
            "  ARP type: ARPA, ARP Timeout 04:00:00",
            "  Last input 00:00:00, output 00:00:00, output hang never",
            "  Last clearing of \"show interface\" counters never",
            "  Input queue: 0/2000/0/0 (size/max/drops/flushes); Total output drops: 0",
            "  Queueing strategy: fifo",
            "  Output queue: 0/40 (size/max)",
            "  5 minute input rate 47000 bits/sec, 41 packets/sec",
            "  5 minute output rate 12000 bits/sec, 30 packets/sec",
            "     12503321 packets input, 987654321 bytes, 0 no buffer",
            "     Received 12345 broadcasts (1234 multicasts)",
            "     0 runts, 0 giants, 0 throttles",
            f"     {crc} input errors, {crc} CRC, 0 frame, 0 overrun, 0 ignored",
            "     0 watchdog, 1234 multicast, 0 pause input",
            "     0 input packets with dribble condition detected",
            "     11203321 packets output, 887654321 bytes, 0 underruns",
            "     0 output errors, 0 collisions, 1 interface resets",
            "     0 unknown protocol drops",
            "     0 babbles, 0 late collision, 0 deferred",
            "     0 lost carrier, 0 no carrier, 0 pause output",
            "     0 output buffer failures, 0 output buffers swapped out",
        ]
        blocks.append("\n".join(b))
    return "\n".join(blocks)


def show_ip_route(dev: dict[str, Any]) -> str:
    lines = [
        "Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP",
        "       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area ",
        "       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2",
        "       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP",
        "       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA",
        "       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2",
        "       ia - IS-IS inter area, * - candidate default, U - per-user static route",
        "       H - NHRP, G - NHRP registered, g - NHRP registration summary",
        "       o - ODR, P - periodic downloaded static route, l - LISP",
        "       a - application route",
        "       + - replicated route, % - next hop override, p - overrides from PfR",
        "       & - replicated local route overrides by connected",
        "",
    ]
    gw = dev.get("default_gateway")
    lines.append(f"Gateway of last resort is {gw} to network 0.0.0.0" if gw else "Gateway of last resort is not set")
    lines.append("")
    if gw:
        lines.append(f"S*    0.0.0.0/0 [1/0] via {gw}")
    for i in dev["interfaces"]:
        if i.get("ip") and i["status"] == "up":
            net = ipaddress.ip_interface(i["ip"]).network
            addr = i["ip"].split("/")[0]
            lines.append(f"C        {net} is directly connected, {i['name']}")
            lines.append(f"L        {addr}/32 is directly connected, {i['name']}")
    for r in dev.get("ospf_routes", []):
        lines.append(f"O        {r['prefix']} [110/{r.get('metric', 20)}] via {r['via']}, 01:12:44, {r['interface']}")
    return "\n".join(lines)


def show_ip_bgp_summary(dev: dict[str, Any]) -> str:
    peers = dev.get("bgp", [])
    if not peers:
        return "% BGP not active"
    lines = [
        f"BGP router identifier {dev['ip']}, local AS number {dev.get('bgp_as', 65010)}",
        "BGP table version is 12, main routing table version 12",
        "3 network entries using 744 bytes of memory",
        "",
        "Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd",
    ]
    for p in peers:
        state = str(p.get("state", "1"))
        up = "3d04h" if state.isdigit() else "never"
        lines.append(f"{p['neighbor']:<15} 4 {p['as']:>10}   20553   20561       12    0    0 {up:<8} {state}")
    return "\n".join(lines)


def show_ip_ospf_neighbor(dev: dict[str, Any]) -> str:
    rows = dev.get("ospf", [])
    lines = ["", "Neighbor ID     Pri   State           Dead Time   Address         Interface"]
    for r in rows:
        lines.append(f"{r['neighbor_id']:<15} {r.get('priority', 1):>3}   {r['state']:<15} 00:00:35    "
                     f"{r['address']:<15} {r['interface']}")
    return "\n".join(lines)


def show_standby_brief(dev: dict[str, Any]) -> str:
    rows = dev.get("hsrp", [])
    lines = ["                     P indicates configured to preempt.",
             "                     |",
             "Interface   Grp  Pri P State   Active          Standby         Virtual IP"]
    for r in rows:
        lines.append(f"{r['interface']:<11} {r['group']:<4} {r['priority']:<3} P {r['state']:<7} "
                     f"{r.get('active', 'local'):<15} {r.get('standby', 'unknown'):<15} {r['vip']}")
    return "\n".join(lines)


def show_processes_cpu(dev: dict[str, Any]) -> str:
    cpu = int(dev.get("cpu", 10))
    return (f"CPU utilization for five seconds: {cpu + 2}%/{max(cpu // 4, 1)}%; one minute: {cpu + 1}%; "
            f"five minutes: {cpu}%\n PID Runtime(ms)     Invoked      uSecs   5Sec   1Min   5Min TTY Process\n"
            "   1          10         100        100  0.00%  0.00%  0.00%   0 Chunk Manager")


COMMANDS = {
    "show version": show_version,
    "show ip interface brief": show_ip_int_brief,
    "show interfaces": show_interfaces,
    "show ip route": show_ip_route,
    "show ip bgp summary": show_ip_bgp_summary,
    "show ip ospf neighbor": show_ip_ospf_neighbor,
    "show standby brief": show_standby_brief,
    "show processes cpu": show_processes_cpu,
}


def run_command(dev: dict[str, Any], command: str) -> str | None:
    """Return command output, '' for accepted no-output commands, None for unknown commands."""
    cmd = " ".join(command.strip().split())
    if not cmd:
        return ""
    if cmd.startswith(("terminal ", "term ")) or cmd in ("enable",):
        return ""
    if "|" in cmd:                                  # simple "| include/exclude" support
        base, _, flt = cmd.partition("|")
        out = run_command(dev, base)
        if out is None:
            return None
        word, _, pattern = flt.strip().partition(" ")
        keep = (lambda l: pattern in l) if word.startswith("inc") else (lambda l: pattern not in l)
        return "\n".join(l for l in out.splitlines() if keep(l) or l.startswith("Interface"))
    func = COMMANDS.get(cmd)
    return func(dev) if func else None
