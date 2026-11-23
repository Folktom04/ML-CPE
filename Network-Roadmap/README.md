# 🌐 Network Engineer Roadmap: Level 1–100

หลักสูตรเรียนงานเครือข่ายตั้งแต่ศูนย์จนถึงระดับ Architect รวมเนื้อหาที่ต้องรู้ในการทำงานจริง แต่ละ Level มี:

- **สิ่งที่ต้องรู้**: แนวคิด คำสั่ง และ config ตัวอย่าง
- **แบบทดสอบ 5 ข้อ**: เฉลยซ่อนอยู่ในส่วน "เฉลย" ให้คลิกเปิดหลังจากตอบเองแล้ว
- **5 โปรเจค**: ไล่ความยาก ⭐ (ง่าย) → ⭐⭐⭐ (ยาก)

รวม **100 Level · 500 คำถาม · 500 โปรเจค**

> 📖 **บทเรียนฉบับละเอียดทุก Level (1–100):** ดู **[สารบัญบทเรียน](lessons/README.md)**: อธิบายเนื้อหาแบบเข้าใจง่าย มีตัวอย่าง config, ข้อผิดพลาดที่พบบ่อย, cheat sheet และแบบทดสอบ 10 ข้อต่อบท (ในไฟล์ Tier แต่ละ Level ก็มีลิงก์ไปบทเรียนของ Level นั้น)

> 🎯 **เตรียมทำงานที่ ISC (isc-th.com)?** ดู **[ISC-Track](ISC-Track/README.md)**: Level 1–100 ที่จัดตามขอบเขตงานจริงของบริษัท ครอบคลุม Network, DC, Backup/DR, Security, HCI, Virtualization, Cloud, Mail, Big Data, HPC/AI, Support/MA, Outsourcing และ ISO 9001
>
> 🏢 **ต้องการเน้นงานบริษัท System Integrator?** ดู **[SI-Track](SI-Track/README.md)**: Level 1–100 ที่เน้น Data Center (Server, Storage SAN, HA Cluster), Cybersecurity (NGFW, Zero Trust Segmentation, เฝ้าระวังภัยคุกคาม), Cloud & HCI (HCI, Cloud Migration) และ Support 24x7 (ดูแลระบบฉุกเฉิน, Preventive Maintenance)

---

## 📚 สารบัญ

| Tier | Level | หัวข้อ | ไฟล์ | ระดับงาน |
|---|---|---|---|---|
| 1 | 1–10 | พื้นฐาน: OSI, TCP/IP, สาย, อุปกรณ์, IPv4, Subnetting, VLSM | [01-foundations.md](01-foundations.md) | นักศึกษา / Helpdesk |
| 2 | 11–20 | Protocol หลัก: ARP, ICMP, TCP, UDP, DHCP, DNS, NAT, IPv6, HTTP/TLS | [02-core-protocols.md](02-core-protocols.md) | Helpdesk / NOC |
| 3 | 21–30 | เครื่องมือ: Wireshark, tcpdump, nmap, Linux/Windows, Lab, Cisco IOS, Troubleshooting | [03-tools-and-troubleshooting.md](03-tools-and-troubleshooting.md) | NOC / Jr. Admin |
| 4 | 31–40 | Switching: VLAN, Trunk, STP/RSTP, EtherChannel, Port Security, Campus design | [04-switching.md](04-switching.md) | Network Admin (CCNA) |
| 5 | 41–50 | Routing: Static, OSPF, EIGRP, BGP, FHRP | [05-routing.md](05-routing.md) | Network Engineer (CCNA→CCNP) |
| 6 | 51–60 | Wireless, ACL, QoS, NTP/SNMP, AAA, WAN, IPsec, Remote VPN, SD-WAN | [06-services-wireless-wan.md](06-services-wireless-wan.md) | Network Engineer |
| 7 | 61–70 | Security: Firewall, L2 security, IDS/IPS, PKI, 802.1X/Zero Trust, SIEM, IR | [07-security.md](07-security.md) | Network Security Engineer |
| 8 | 71–80 | DC & Cloud: LB, CDN, Spine-Leaf, VXLAN/EVPN, Docker, Kubernetes, AWS, Hybrid | [08-datacenter-cloud.md](08-datacenter-cloud.md) | DC / Cloud Network Engineer |
| 9 | 81–90 | Automation: Python, Ansible, APIs, CI/CD, Terraform, Monitoring, NetFlow, SDN, NetBox | [09-automation-operations.md](09-automation-operations.md) | NetDevOps Engineer |
| 10 | 91–100 | Expert: Advanced TS, Design, HA/DR, Capacity, ITIL, Multicast, MPLS/SR, AI fabric, Career, Capstone | [10-expert-career.md](10-expert-career.md) | Senior / Architect |

---

## 🧭 วิธีเรียนให้ได้ผล

1. **เรียนตามลำดับ**: ทุก Level ใช้ความรู้จาก Level ก่อนหน้า (โดยเฉพาะ Tier 1–5)
2. **ทำแบบทดสอบก่อนเปิดเฉลย**: ต้องได้ 4/5 ข้อขึ้นไปจึงผ่าน Level
3. **ทำโปรเจคอย่างน้อย 3 จาก 5 ข้อ** ก่อนขึ้น Level ถัดไป และทำ ⭐⭐⭐ อย่างน้อย 1 ข้อในทุก Tier
4. **เก็บทุกอย่างลง Git**: config, script, diagram และรายงาน จะกลายเป็น portfolio (Level 99)
5. **ทุก Tier จบด้วย Capstone**: เป็นโปรเจคข้อ 5 ของ Level สุดท้ายใน Tier
6. **ทบทวนแบบเว้นระยะ**: ทุก 10 Level ให้กลับไปทำแบบทดสอบของ Tier ก่อนหน้าอีกรอบ

### ⏱️ ระยะเวลาโดยประมาณ (เรียน 10–15 ชม./สัปดาห์)

| ช่วง | ระยะเวลา | เป้าหมาย |
|---|---|---|
| Tier 1–3 | 2–3 เดือน | พร้อมงาน Helpdesk / NOC, สอบ Network+ |
| Tier 4–6 | 3–4 เดือน | พร้อมสอบ CCNA, งาน Network Admin |
| Tier 7–8 | 3–4 เดือน | งาน Network/Security/Cloud Engineer |
| Tier 9–10 | 3–6 เดือน | NetDevOps / Senior / เตรียม CCNP–CCIE |

---

## 🛠️ Lab ที่ต้องเตรียม (ฟรีเกือบทั้งหมด)

| เครื่องมือ | ใช้ใน | หมายเหตุ |
|---|---|---|
| Cisco Packet Tracer | Tier 1–6 | ฟรีผ่าน Cisco Networking Academy |
| GNS3 / EVE-NG Community | Tier 4–7, 10 | ต้องมี image (IOSv, vIOS-L2, CSR1000v) |
| Containerlab + FRRouting / Arista cEOS / Nokia SR Linux | Tier 5, 8–10 | เบา เหมาะกับ automation |
| Wireshark, tcpdump, nmap, iperf3 | ทุก Tier | |
| VirtualBox / Proxmox / KVM | Tier 3, 7, 8 | Linux, pfSense/OPNsense, Windows Server |
| Docker, kind/k3d | Tier 8–9 | |
| Python 3, Ansible, Terraform, Git | Tier 9–10 | |
| Cisco DevNet Sandbox, AWS Free Tier | Tier 6, 8, 9 | **ลบทรัพยากร cloud หลังทำทุกครั้ง** |

> แนะนำเครื่อง: RAM 16 GB ขึ้นไป (32 GB จะสบายกับ EVE-NG/GNS3), CPU ที่รองรับ virtualization

---

## ✅ ตารางติดตามความคืบหน้า

คัดลอกไปใช้ หรือติ๊ก `[x]` ในไฟล์นี้เมื่อผ่าน Level (แบบทดสอบ ≥ 4/5 และโปรเจค ≥ 3)

<details><summary>Tier 1–5 (Level 1–50)</summary>

- [ ] 1 Network & ประเภท · [ ] 2 OSI · [ ] 3 TCP/IP · [ ] 4 สาย/Physical · [ ] 5 อุปกรณ์
- [ ] 6 เลขฐาน · [ ] 7 MAC/Ethernet · [ ] 8 IPv4 · [ ] 9 Subnetting · [ ] 10 VLSM/CIDR
- [ ] 11 ARP · [ ] 12 ICMP · [ ] 13 TCP · [ ] 14 UDP/Ports · [ ] 15 DHCP
- [ ] 16 DNS · [ ] 17 NAT · [ ] 18 IPv6 · [ ] 19 SLAAC/NDP · [ ] 20 HTTP/TLS
- [ ] 21 OS commands · [ ] 22 Wireshark · [ ] 23 tcpdump · [ ] 24 nmap · [ ] 25 dig/curl/iperf
- [ ] 26 Linux net · [ ] 27 Windows net · [ ] 28 Lab setup · [ ] 29 Cisco IOS · [ ] 30 Troubleshooting
- [ ] 31 Switch/MAC · [ ] 32 VLAN · [ ] 33 Trunk · [ ] 34 Inter-VLAN · [ ] 35 STP
- [ ] 36 RSTP/MST · [ ] 37 EtherChannel · [ ] 38 Port security · [ ] 39 CDP/LLDP · [ ] 40 Campus design
- [ ] 41 Static · [ ] 42 Default/IP SLA · [ ] 43 Dynamic concepts · [ ] 44 RIP · [ ] 45 OSPF
- [ ] 46 OSPF multi-area · [ ] 47 EIGRP · [ ] 48 BGP · [ ] 49 BGP policy · [ ] 50 FHRP
</details>

<details><summary>Tier 6–10 (Level 51–100)</summary>

- [ ] 51 Wi-Fi basics · [ ] 52 WLAN enterprise · [ ] 53 ACL · [ ] 54 QoS · [ ] 55 NTP/Syslog/SNMP
- [ ] 56 AAA · [ ] 57 WAN · [ ] 58 IPsec · [ ] 59 Remote VPN · [ ] 60 SD-WAN/SASE
- [ ] 61 Sec fundamentals · [ ] 62 Firewall · [ ] 63 L2 security · [ ] 64 IDS/IPS · [ ] 65 PKI
- [ ] 66 802.1X/ZT · [ ] 67 Segmentation · [ ] 68 SIEM · [ ] 69 Pentest · [ ] 70 IR/DDoS
- [ ] 71 Load balancing · [ ] 72 Proxy/CDN/WAF · [ ] 73 Spine-leaf · [ ] 74 VXLAN/EVPN · [ ] 75 Virtualization
- [ ] 76 Docker · [ ] 77 Kubernetes · [ ] 78 AWS VPC · [ ] 79 Hybrid cloud · [ ] 80 Mesh/eBPF
- [ ] 81 Python · [ ] 82 Ansible · [ ] 83 APIs/YANG · [ ] 84 CI/CD · [ ] 85 Terraform
- [ ] 86 Monitoring · [ ] 87 NetFlow · [ ] 88 SDN · [ ] 89 NetBox · [ ] 90 Performance
- [ ] 91 Adv. TS · [ ] 92 Design · [ ] 93 HA/DR · [ ] 94 Capacity/Cost · [ ] 95 ITIL/Change
- [ ] 96 Multicast · [ ] 97 MPLS/SR · [ ] 98 AI fabric · [ ] 99 Career · [ ] 100 Capstone
</details>

---

## 📖 แหล่งเรียนเพิ่มเติม

- Cisco Networking Academy (CCNA), Jeremy's IT Lab (YouTube, ฟรี)
- *Computer Networking: A Top-Down Approach* (Kurose & Ross)
- *TCP/IP Illustrated Vol.1* (Stevens), *Network Warrior* (Gary Donahue)
- RFC ต้นฉบับ (rfc-editor.org), เอกสาร vendor (Cisco, Juniper, Arista)
- *Network Programmability and Automation* (O'Reilly)
- NetworkLessons, INE, KodeKloud (บางส่วนเสียเงิน)

> ⚠️ **จริยธรรม**: lab ด้าน security (scan, spoofing, attack) ให้ทำเฉพาะในเครือข่ายของตัวเอง หรือที่ได้รับอนุญาตเป็นลายลักษณ์อักษรเท่านั้น การเข้าถึงระบบผู้อื่นโดยไม่ได้รับอนุญาตผิด พ.ร.บ.คอมพิวเตอร์ฯ
