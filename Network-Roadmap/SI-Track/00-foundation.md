# Part 0 — พื้นฐาน Network ที่งาน SI ต้องใช้ (Level 1–20)

> Level เหล่านี้ใช้เนื้อหา แบบทดสอบ และโปรเจคจาก Roadmap หลัก (`../`) โดยเลือกเฉพาะเรื่องที่ใช้จริงในงาน Data Center, Security, Cloud/HCI และ Support
> **เกณฑ์ผ่าน:** ทำแบบทดสอบของ Level ต้นทางได้ ≥ 4/5 ข้อ และตอบ **SI Checkpoint** ได้

| SI Level | หัวข้อ | เรียนจาก (Roadmap หลัก) | SI Checkpoint: ใช้ในงานลูกค้าอย่างไร |
|---|---|---|---|
| 1 | OSI & TCP/IP | [L2, L3](../01-foundations.md) | อธิบายให้ลูกค้าฟังว่าปัญหาอยู่ layer ไหน |
| 2 | สาย, ไฟเบอร์, SFP, อุปกรณ์ | [L4, L5](../01-foundations.md) | เลือก SFP/สาย DAC/AOC สำหรับ server 25G ต่อ ToR ได้ถูก |
| 3 | IPv4, Subnetting, VLSM | [L8–L10](../01-foundations.md) | ทำ IP plan สำหรับ mgmt/vMotion/storage/VM network |
| 4 | ARP, ICMP, TCP, UDP | [L11–L14](../02-core-protocols.md) | รู้ port ที่ต้องเปิดให้ vCenter/Prism/iDRAC/backup |
| 5 | DHCP, DNS, NAT | [L15–L17](../02-core-protocols.md) | DNS forward/reverse ต้องถูกก่อนติดตั้ง vCenter/Nutanix |
| 6 | IPv6 | [L18, L19](../02-core-protocols.md) | ตอบได้ว่าระบบลูกค้ารองรับ IPv6 หรือไม่ |
| 7 | Wireshark, tcpdump, nmap, iperf | [L22–L25](../03-tools-and-troubleshooting.md) | พิสูจน์ปัญหาด้วย capture ก่อนโทษอุปกรณ์ |
| 8 | Linux & Windows networking | [L26, L27](../03-tools-and-troubleshooting.md) | ตั้ง NIC teaming/bond และ VLAN บน server |
| 9 | Lab & Cisco IOS | [L28, L29](../03-tools-and-troubleshooting.md) | ทำ lab จำลองก่อนเข้าหน้างานลูกค้า |
| 10 | Troubleshooting methodology | [L30](../03-tools-and-troubleshooting.md) | ถามคำถามคัดกรองก่อนลงมือแก้ทุกครั้ง |
| 11 | VLAN, Trunk, Inter-VLAN | [L32–L34](../04-switching.md) | ตั้ง trunk จาก ToR ไป ESXi/AHV host |
| 12 | STP, EtherChannel/LACP | [L35–L37](../04-switching.md) | ใส่ portfast edge ที่พอร์ต server; LACP vs active/standby |
| 13 | Static & default route | [L41, L42](../05-routing.md) | ตั้ง route ไป DR site และ backup network |
| 14 | OSPF | [L45, L46](../05-routing.md) | อ่าน routing ของลูกค้าเพื่อหาเส้นทาง traffic |
| 15 | BGP | [L48, L49](../05-routing.md) | ใช้ BGP เชื่อม cloud (VPN/Direct Connect/ExpressRoute) |
| 16 | HSRP/VRRP | [L50](../05-routing.md) | ทำ gateway สำรองให้ server farm |
| 17 | ACL & QoS | [L53, L54](../06-services-wireless-wan.md) | จำกัดการเข้าถึง management network |
| 18 | NTP, Syslog, SNMP, AAA | [L55, L56](../06-services-wireless-wan.md) | ส่ง log/SNMP เข้า monitoring ของทีม Support 24x7 |
| 19 | IPsec & Remote VPN | [L58, L59](../06-services-wireless-wan.md) | ตั้ง VPN สำหรับ remote support เข้าหาลูกค้า |
| 20 | Wireless enterprise | [L51, L52](../06-services-wireless-wan.md) | Survey และ handover Wi-Fi ลูกค้า |

## 5 โปรเจคปิด Part 0 (ทำก่อนขึ้น Level 21)

- ⭐ P1: ทำ **IP & VLAN plan ของ data center เล็ก**: Mgmt (iDRAC/iLO), Hypervisor mgmt, vMotion/Live Migration, Storage (iSCSI/NFS), VM networks, Backup และ DMZ
- ⭐⭐ P2: ทำ **ตาราง port/firewall requirement** ของ vCenter, ESXi, Nutanix Prism, Veeam, AD และ DNS โดยอ้างอิงเอกสาร vendor
- ⭐⭐ P3: ทำ **Lab ใน GNS3/Packet Tracer**: core switch 2 ตัว (HSRP + LACP) ต่อ ToR 2 ตัว ต่อ server 2 เครื่อง (trunk)
- ⭐⭐ P4: เขียน **Network pre-requisite checklist** ที่ต้องส่งให้ลูกค้าก่อนวันติดตั้ง (IP, VLAN, DNS, NTP, gateway และ firewall)
- ⭐⭐⭐ P5: **จำลองเคส Support**: "VM ข้าม host แล้ว ping ไม่ได้" ใน lab แล้วแก้ (สาเหตุคือ VLAN ไม่ได้ allow บน trunk) พร้อมเขียน incident report
