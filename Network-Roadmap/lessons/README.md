# สารบัญบทเรียนฉบับละเอียด (Level 1–100)

> บทเรียนแต่ละบทอธิบายเนื้อหาของ Level นั้นอย่างละเอียด มีตัวอย่าง config, ข้อควรระวัง, cheat sheet และแบบทดสอบ 10 ข้อพร้อมเฉลย
> อ่านบทเรียนก่อน แล้วไปทำ **5 โปรเจค** ของ Level นั้นในไฟล์ Tier

> 🖨️ **ต้องการฉบับพิมพ์?** มีไฟล์ PDF ขนาด A4 พร้อมพิมพ์ใน [print/](../print/) (เช่น Level 1–6) หรือสร้างช่วงบทที่ต้องการเอง:
> `python3 scripts/build_print.py --from 7 --to 12` (ต้องมี Python package `markdown`, `pypdf` และ Node.js + Playwright)

## Tier 1 — พื้นฐานเครือข่าย (Level 1–10)
โปรเจคและแบบฝึก: [01-foundations.md](../01-foundations.md)

| Level | บทเรียน |
|---|---|
| 1 | [พื้นฐานเครือข่ายคอมพิวเตอร์](L01-network-basics.md) |
| 2 | [OSI Model 7 Layers](L02-osi-model.md) |
| 3 | [TCP/IP Model](L03-tcp-ip-model.md) |
| 4 | [สาย สื่อนำสัญญาณ และ Physical Layer](L04-cabling-physical.md) |
| 5 | [อุปกรณ์เครือข่าย](L05-network-devices.md) |
| 6 | [เลขฐาน 2 / 16 สำหรับงานเน็ตเวิร์ก](L06-binary-hex.md) |
| 7 | [MAC Address & Ethernet Frame](L07-mac-ethernet.md) |
| 8 | [IPv4 Addressing](L08-ipv4-addressing.md) |
| 9 | [Subnetting](L09-subnetting.md) |
| 10 | [VLSM, CIDR & Route Summarization](L10-vlsm-cidr-summarization.md) |

## Tier 2 — Protocol หลัก (Level 11–20)
โปรเจคและแบบฝึก: [02-core-protocols.md](../02-core-protocols.md)

| Level | บทเรียน |
|---|---|
| 11 | [ARP (Address Resolution Protocol)](L11-arp.md) |
| 12 | [ICMP, ping, traceroute](L12-icmp-ping-traceroute.md) |
| 13 | [TCP](L13-tcp.md) |
| 14 | [UDP & Port Numbers](L14-udp-ports.md) |
| 15 | [DHCP](L15-dhcp.md) |
| 16 | [DNS](L16-dns.md) |
| 17 | [NAT / PAT](L17-nat-pat.md) |
| 18 | [IPv6 พื้นฐาน](L18-ipv6-basics.md) |
| 19 | [IPv6 Addressing: SLAAC, DHCPv6, NDP](L19-ipv6-slaac-ndp.md) |
| 20 | [HTTP, HTTPS & TLS พื้นฐาน](L20-http-https-tls.md) |

## Tier 3 — เครื่องมือ, OS Networking & Troubleshooting (Level 21–30)
โปรเจคและแบบฝึก: [03-tools-and-troubleshooting.md](../03-tools-and-troubleshooting.md)

| Level | บทเรียน |
|---|---|
| 21 | [คำสั่งเครือข่ายพื้นฐานบน OS](L21-os-network-commands.md) |
| 22 | [Wireshark](L22-wireshark.md) |
| 23 | [tcpdump & CLI Capture](L23-tcpdump.md) |
| 24 | [Nmap & Network Discovery](L24-nmap-discovery.md) |
| 25 | [dig, curl, openssl, nc, iperf](L25-dig-curl-openssl-nc-iperf.md) |
| 26 | [Linux Networking Configuration](L26-linux-networking.md) |
| 27 | [Windows Networking & PowerShell](L27-windows-networking.md) |
| 28 | [ตั้ง Lab: Packet Tracer, GNS3, EVE-NG, Containerlab](L28-network-labs.md) |
| 29 | [Cisco IOS พื้นฐาน](L29-cisco-ios-basics.md) |
| 30 | [วิธีการ Troubleshoot อย่างเป็นระบบ](L30-troubleshooting-methodology.md) |

## Tier 4 — Switching (Level 31–40)
โปรเจคและแบบฝึก: [04-switching.md](../04-switching.md)

| Level | บทเรียน |
|---|---|
| 31 | [การทำงานของ Switch & MAC Address Table](L31-switch-mac-table.md) |
| 32 | [VLAN](L32-vlan.md) |
| 33 | [Trunk 802.1Q, DTP & VTP](L33-trunk-8021q.md) |
| 34 | [Inter-VLAN Routing](L34-inter-vlan-routing.md) |
| 35 | [Spanning Tree Protocol (STP 802.1D)](L35-stp.md) |
| 36 | [RSTP, MST & STP Toolkit](L36-rstp-mst-stp-toolkit.md) |
| 37 | [EtherChannel / Link Aggregation (LACP)](L37-etherchannel-lacp.md) |
| 38 | [Port Security & Access Control บน Switch](L38-port-security.md) |
| 39 | [CDP, LLDP & เอกสารเครือข่าย](L39-cdp-lldp-documentation.md) |
| 40 | [L3 Switching & Campus Design](L40-campus-design.md) |

## Tier 5 — Routing (Level 41–50)
โปรเจคและแบบฝึก: [05-routing.md](../05-routing.md)

| Level | บทเรียน |
|---|---|
| 41 | [Routing Table & Static Routing](L41-routing-table-static.md) |
| 42 | [Default Route, Floating Static & IP SLA](L42-default-floating-ipsla.md) |
| 43 | [แนวคิด Dynamic Routing](L43-dynamic-routing-concepts.md) |
| 44 | [RIP](L44-rip.md) |
| 45 | [OSPF Single Area](L45-ospf-single-area.md) |
| 46 | [OSPF Multi-Area & LSA](L46-ospf-multi-area.md) |
| 47 | [EIGRP](L47-eigrp.md) |
| 48 | [BGP พื้นฐาน](L48-bgp-basics.md) |
| 49 | [BGP Path Selection & Policy](L49-bgp-path-selection-policy.md) |
| 50 | [First Hop Redundancy (HSRP / VRRP / GLBP)](L50-fhrp-hsrp-vrrp.md) |

## Tier 6 — Wireless, Services, WAN & VPN (Level 51–60)
โปรเจคและแบบฝึก: [06-services-wireless-wan.md](../06-services-wireless-wan.md)

| Level | บทเรียน |
|---|---|
| 51 | [Wireless 802.11 พื้นฐาน](L51-wireless-basics.md) |
| 52 | [WLAN องค์กร: Controller, Design & Security](L52-wlan-enterprise.md) |
| 53 | [ACL (Access Control List)](L53-acl.md) |
| 54 | [QoS (Quality of Service)](L54-qos.md) |
| 55 | [NTP, Syslog, SNMP](L55-ntp-syslog-snmp.md) |
| 56 | [AAA: RADIUS & TACACS+](L56-aaa-radius-tacacs.md) |
| 57 | [WAN Technologies](L57-wan-technologies.md) |
| 58 | [Site-to-Site VPN (IPsec)](L58-ipsec-site-to-site.md) |
| 59 | [Remote Access VPN (SSL VPN, IPsec, WireGuard, OpenVPN)](L59-remote-access-vpn.md) |
| 60 | [SD-WAN & SASE](L60-sdwan-sase.md) |

## Tier 7 — Network Security (Level 61–70)
โปรเจคและแบบฝึก: [07-security.md](../07-security.md)

| Level | บทเรียน |
|---|---|
| 61 | [Security Fundamentals](L61-security-fundamentals.md) |
| 62 | [Firewall: Stateful, NGFW, iptables/nftables](L62-firewall-ngfw.md) |
| 63 | [Layer 2 Security](L63-layer2-security.md) |
| 64 | [IDS/IPS](L64-ids-ips.md) |
| 65 | [Cryptography & PKI สำหรับ Network Engineer](L65-crypto-pki.md) |
| 66 | [802.1X, NAC & Zero Trust](L66-8021x-nac-zero-trust.md) |
| 67 | [Segmentation, DMZ & Secure Architecture](L67-segmentation-dmz.md) |
| 68 | [Logging, SIEM & Visibility](L68-siem-logging.md) |
| 69 | [Penetration Testing สำหรับ Network (Authorized)](L69-pentest-authorized.md) |
| 70 | [Incident Response & DDoS Mitigation](L70-incident-response-ddos.md) |

## Tier 8 — Data Center, Virtualization & Cloud Networking (Level 71–80)
โปรเจคและแบบฝึก: [08-datacenter-cloud.md](../08-datacenter-cloud.md)

| Level | บทเรียน |
|---|---|
| 71 | [Load Balancing](L71-load-balancing.md) |
| 72 | [Proxy, Reverse Proxy, CDN & WAF](L72-proxy-cdn-waf.md) |
| 73 | [Data Center Design: Spine-Leaf](L73-dc-spine-leaf.md) |
| 74 | [VXLAN & EVPN](L74-vxlan-evpn.md) |
| 75 | [Virtualization Networking](L75-virtualization-networking.md) |
| 76 | [Container Networking (Docker)](L76-docker-networking.md) |
| 77 | [Kubernetes Networking](L77-kubernetes-networking.md) |
| 78 | [Cloud Networking (AWS VPC)](L78-cloud-aws-vpc.md) |
| 79 | [Hybrid & Multi-Cloud Connectivity](L79-hybrid-multicloud.md) |
| 80 | [Service Mesh, eBPF & Cloud-Native Networking](L80-service-mesh-ebpf.md) |

## Tier 9 — Network Automation & Operations (Level 81–90)
โปรเจคและแบบฝึก: [09-automation-operations.md](../09-automation-operations.md)

| Level | บทเรียน |
|---|---|
| 81 | [Python for Network Engineers](L81-python-for-network.md) |
| 82 | [Ansible for Network](L82-ansible-network.md) |
| 83 | [APIs: REST, NETCONF, RESTCONF, YANG, gNMI](L83-network-apis.md) |
| 84 | [Git, CI/CD & NetDevOps](L84-git-cicd-netdevops.md) |
| 85 | [Infrastructure as Code: Terraform](L85-terraform.md) |
| 86 | [Monitoring & Observability](L86-monitoring-observability.md) |
| 87 | [Flow Analysis: NetFlow, sFlow, IPFIX](L87-flow-analysis.md) |
| 88 | [SDN Concepts & Intent-Based Networking](L88-sdn-intent-based.md) |
| 89 | [Source of Truth & IPAM (NetBox)](L89-netbox-source-of-truth.md) |
| 90 | [Performance Testing & Tuning](L90-performance-testing.md) |

## Tier 10 — Expert, Architecture & Career (Level 91–100)
โปรเจคและแบบฝึก: [10-expert-career.md](../10-expert-career.md)

| Level | บทเรียน |
|---|---|
| 91 | [Advanced Troubleshooting ระดับองค์กร](L91-advanced-troubleshooting.md) |
| 92 | [Network Design Methodology](L92-network-design-methodology.md) |
| 93 | [High Availability & Disaster Recovery](L93-ha-dr.md) |
| 94 | [Capacity Planning, Cost & Vendor Management](L94-capacity-cost-vendor.md) |
| 95 | [Change Management, ITIL & Documentation](L95-change-itil-documentation.md) |
| 96 | [Multicast](L96-multicast.md) |
| 97 | [MPLS & Segment Routing (Service Provider)](L97-mpls-segment-routing.md) |
| 98 | [Networking for AI / HPC Data Centers](L98-ai-hpc-networking.md) |
| 99 | [Career Path, Certifications & Interview](L99-career-cert-interview.md) |
| 100 | [Final Capstone: Enterprise Network End-to-End](L100-final-capstone.md) |

⬅️ กลับไป [README หลัก](../README.md)
