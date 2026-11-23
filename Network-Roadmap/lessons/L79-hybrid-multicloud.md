# บทเรียน Level 79 — Hybrid & Multi-Cloud Connectivity (ฉบับละเอียด)

> อ่านจบแล้วจะ: เลือกวิธีเชื่อม on-prem กับ cloud (Site-to-Site VPN, Direct Connect/ExpressRoute/Interconnect) · ตั้ง IPsec VPN + BGP ไป AWS · ออกแบบ redundancy · จัดการ routing (AS path, prefix, MED, ข้อจำกัดจำนวน route) · Hybrid DNS · IP planning ข้าม cloud · multi-cloud networking · ความปลอดภัยและการแก้ปัญหา

---

## 1. Hybrid vs Multi-Cloud

| | ความหมาย | ตัวอย่าง |
|---|---|---|
| **Hybrid cloud** | on-premises + public cloud ทำงานร่วมกัน | ERP อยู่ DC, เว็บ/analytics อยู่ AWS |
| **Multi-cloud** | ใช้ cloud มากกว่า 1 เจ้า | แอปอยู่ AWS, Microsoft 365/Entra อยู่ Azure, BigQuery อยู่ GCP |

ความท้าทายด้าน network: **เชื่อมต่อ, routing, IP ไม่ชน, DNS, security policy ที่สม่ำเสมอ, visibility, ค่าใช้จ่าย**

---

## 2. วิธีเชื่อม On-Prem ↔ Cloud

| วิธี | การทำงาน | Bandwidth | Latency/ความเสถียร | เวลาติดตั้ง | ราคา |
|---|---|---|---|---|---|
| **Site-to-Site IPsec VPN** | อุโมงค์เข้ารหัสผ่านอินเทอร์เน็ต | ~1.25 Gbps ต่อ tunnel (AWS) — รวมหลาย tunnel ด้วย ECMP | ขึ้นกับอินเทอร์เน็ต ไม่แน่นอน | นาที–ชั่วโมง | ต่ำ |
| **Dedicated/Private connection** — AWS **Direct Connect**, Azure **ExpressRoute**, GCP **Cloud Interconnect** | วงจรส่วนตัวจาก DC/colocation/ผู้ให้บริการไปยัง cloud | 50 Mbps – 100 Gbps | **คงที่, latency ต่ำ** ไม่ผ่านอินเทอร์เน็ต | สัปดาห์–เดือน | สูงกว่า (port + วงจร + partner) แต่ค่า egress ต่อ GB ถูกกว่า |
| SD-WAN ขยายเข้า cloud | virtual edge ของ SD-WAN ใน VPC/vWAN | ตาม instance | ใช้หลาย underlay | เร็ว | license |

### Direct Connect / ExpressRoute — รูปแบบการเชื่อม
```
 [On-prem router] ── วงจร (MPLS/Metro Ethernet ของผู้ให้บริการ) ──► [Colocation / DX location]
                                                                    └── cross-connect ──► [AWS DX router]
 - Dedicated connection: port ของเราเอง (1/10/100G)
 - Hosted connection: ผ่าน partner (ขนาดเล็กกว่า)
 - ใช้ 802.1Q VLAN แยก Virtual Interface (VIF): Private VIF (ไป VPC/TGW ผ่าน DX Gateway), Transit VIF, Public VIF
 - ใช้ BGP บนแต่ละ VIF
```
⚠️ Direct Connect/ExpressRoute **ไม่เข้ารหัสโดยค่าเริ่มต้น** — ถ้าต้องการ ใช้ **MACsec** (บน port ที่รองรับ) หรือ IPsec VPN บน DX

---

## 3. Site-to-Site VPN ไป AWS (ตัวอย่างที่ใช้จริงบ่อย)

### องค์ประกอบ
```
 On-prem: [Customer Gateway device (firewall/router) public IP 198.51.100.10, ASN 65010]
                │  Tunnel 1 (169.254.10.0/30)       │  Tunnel 2 (169.254.11.0/30)
                ▼                                   ▼
 AWS:     [Virtual Private Gateway หรือ Transit Gateway, ASN 64512]  ← 2 endpoint คนละ AZ
```
- AWS ให้ **2 tunnel ต่อ VPN connection** (endpoint คนละ AZ) → **ต้องขึ้นทั้ง 2 tunnel**
- เลือก **dynamic routing (BGP)** ⭐ แทน static — failover อัตโนมัติ
- ดาวน์โหลด config ตัวอย่างตามยี่ห้อ (Cisco/Fortinet/Palo Alto/pfSense) จาก console

### ตัวอย่างฝั่ง Cisco IOS (ย่อ — ใช้ค่าจากไฟล์ที่ AWS ให้)
```
crypto ikev2 proposal AWS-PROP
 encryption aes-cbc-256
 integrity sha256
 group 14
crypto ikev2 policy AWS-POL
 proposal AWS-PROP
crypto ikev2 keyring AWS-KR
 peer AWS-T1
  address 52.x.x.1
  pre-shared-key <PSK จากไฟล์ config>
crypto ikev2 profile AWS-PROF
 match identity remote address 52.x.x.1 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local AWS-KR
 dpd 10 3 on-demand
crypto ipsec transform-set AWS-TS esp-aes 256 esp-sha256-hmac
 mode tunnel
crypto ipsec profile AWS-IPSEC
 set transform-set AWS-TS
 set pfs group14
 set ikev2-profile AWS-PROF
interface Tunnel1
 ip address 169.254.10.2 255.255.255.252
 ip mtu 1436
 ip tcp adjust-mss 1379                 ! สำคัญ: กันปัญหา MTU (Level 52)
 tunnel source GigabitEthernet0/0
 tunnel destination 52.x.x.1
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile AWS-IPSEC
router bgp 65010
 neighbor 169.254.10.1 remote-as 64512
 neighbor 169.254.10.1 timers 10 30
 address-family ipv4
  network 10.0.0.0 mask 255.255.0.0     ! ประกาศ on-prem (ต้องมีใน routing table)
  neighbor 169.254.10.1 activate
  neighbor 169.254.10.1 prefix-list FROM-AWS in
  maximum-paths 2                       ! ECMP 2 tunnel (เมื่อใช้ TGW)
ip prefix-list FROM-AWS seq 10 permit 10.20.0.0/16 le 24
```
- อย่าลืม **route propagation** ใน route table ของ VPC (หรือ TGW route table) ให้ subnet รู้ route กลับ on-prem
- ตรวจ SG ของ instance ให้รับจาก CIDR ของ on-prem

---

## 4. ออกแบบ Redundancy

```
 ระดับพื้นฐาน:   1 router + VPN 2 tunnel
 ดีขึ้น:         2 router on-prem (คนละ ISP) × VPN ละ 2 tunnel
 Enterprise:     Direct Connect (หลัก) + Site-to-Site VPN (สำรอง)
 Critical:       DX 2 วงจร 2 location (คนละ device/ผู้ให้บริการ) + VPN สำรอง
                 (AWS เรียก "Maximum Resiliency")
```
### ควบคุมเส้นทางหลัก/สำรองด้วย BGP (Level 55)
| ต้องการ | ทำ |
|---|---|
| **ขาออกจาก on-prem** ใช้ DX เป็นหลัก | **Local Preference** สูงกว่าสำหรับ route ที่รับจาก DX |
| **ขาเข้าจาก AWS** ใช้ DX เป็นหลัก | AWS ชอบ DX มากกว่า VPN อยู่แล้ว (เมื่อ prefix เท่ากัน) · ใช้ **AS-path prepend** บน VPN หรือประกาศ **prefix ที่เจาะจงกว่า** บน DX · BGP community ของ AWS |
| Active/active สองวงจร DX | ECMP (prefix และ AS path เท่ากัน) |
⚠️ ระวัง **asymmetric routing** (ไปทาง DX กลับทาง VPN) → stateful firewall ตัด session
**BFD** บน DX เพื่อ failover เร็ว · ทดสอบ failover จริงตามรอบ (ถอดวงจร/ปิด BGP) — DR ที่ไม่เคยทดสอบ = ไม่มี

### ข้อจำกัดที่ต้องรู้
- จำนวน route ที่ประกาศเข้า AWS ต่อ BGP session มีจำกัด (เช่น **100 route บน VPN/Private VIF**) — เกินแล้ว session ล่ม → **summarize** ก่อนประกาศ
- Azure ExpressRoute ก็มีข้อจำกัดจำนวน prefix ที่คล้ายกัน — ตรวจเอกสารล่าสุด

---

## 5. Hybrid DNS — ส่วนที่มักถูกลืมแต่ทำให้ใช้งานไม่ได้

ผู้ใช้ on-prem ต้อง resolve ชื่อใน cloud และ server ใน cloud ต้อง resolve ชื่อ on-prem (`corp.local`, AD)
```
 On-prem DNS (AD) ── conditional forwarder: aws.corp.example → Route 53 Resolver INBOUND endpoint IP (10.20.5.10/11)
 VPC ── Resolver OUTBOUND endpoint + Forwarding rule: corp.local → 10.0.0.53, 10.0.0.54 (DC ของ on-prem)
```
- Azure: **Private DNS Resolver** (inbound/outbound) · GCP: Cloud DNS forwarding/peering
- **Private endpoint DNS** (privatelink.blob.core.windows.net, vpce DNS): on-prem ต้อง forward โซนเหล่านั้นไปยัง resolver ของ cloud ไม่เช่นนั้นจะได้ public IP แทน private IP
- DNS ต้องผ่าน tunnel → อนุญาต UDP/TCP 53 ใน SG/firewall ทั้งสองฝั่ง

---

## 6. IP Address Planning ข้าม Hybrid/Multi-Cloud

```
 10.0.0.0/12    On-prem (DC, สาขา)
 10.16.0.0/12   AWS   (ต่อ region/บัญชี: /16 ต่อ VPC)
 10.32.0.0/12   Azure
 10.48.0.0/12   GCP
 100.64.0.0/10  (บางองค์กรใช้สำหรับ Pod CIDR/ส่วนที่ไม่ต้อง route ข้ามกัน)
```
- **ห้ามชน** — หลังเชื่อมแล้วแก้ยากมาก · ใช้ **IPAM** กลาง (NetBox, AWS VPC IPAM, Infoblox)
- ออกแบบให้ **summarize ได้** (ประกาศเป็นก้อนใหญ่ — ช่วยเรื่องจำกัดจำนวน route)
- ถ้าชนแล้ว (ควบรวมบริษัท/ลูกค้า): NAT (ซับซ้อน), PrivateLink, หรือย้าย IP

---

## 7. Multi-Cloud Networking

### วิธีเชื่อม cloud กับ cloud
| วิธี | หมายเหตุ |
|---|---|
| **ผ่าน on-prem/colocation** (hub ที่ DC) | ใช้วงจรที่มีอยู่ แต่ latency/backhaul |
| **Cloud exchange/NaaS** (Equinix Fabric, Megaport) | ต่อ virtual cross-connect ไปหลาย cloud จากจุดเดียว เร็ว ยืดหยุ่น |
| **IPsec VPN ระหว่าง cloud** (AWS TGW ↔ Azure VPN GW) | ง่าย ถูก แต่ผ่านอินเทอร์เน็ต |
| **Multi-cloud network platform** (Aviatrix, Alkira, Prosimo) | control plane รวม, segmentation/visibility สม่ำเสมอ |
| **Cross-cloud interconnect** ที่ผู้ให้บริการทำร่วมกัน (เช่น GCP Cross-Cloud Interconnect, Oracle–Azure) | ตรวจความพร้อมใน region |

### ความท้าทาย
- **Security policy คนละภาษา** (SG vs NSG vs GCP firewall) → ใช้ IaC (Terraform) + policy as code, หรือ NGFW ยี่ห้อเดียวกันในทุก cloud
- **Visibility** — flow log คนละรูปแบบ → รวมเข้า SIEM/observability กลาง
- **Egress cost** ข้าม cloud แพง → วาง data ใกล้ compute
- ทักษะทีม — ต้องรู้หลาย cloud

---

## 8. Security ใน Hybrid

- แบ่ง **routing domain** (TGW route table/VRF) — Dev ไม่ควรเข้าถึง Prod on-prem
- **Inspection:** บังคับ traffic hybrid ผ่าน firewall (inspection VPC/hub VNet หรือ firewall on-prem)
- กรอง route ที่รับ/ส่ง (prefix-list) ป้องกันการประกาศ default route หรือ prefix ผิดพลาด
- เข้ารหัสบน private link ตามความจำเป็น (MACsec/IPsec)
- Zero trust: ZTNA สำหรับผู้ใช้เข้าแอปใน cloud แทนการเปิดทั้งเครือข่าย (Level 60/66)
- Log: VPN/BGP state, flow logs, DNS logs → SIEM; แจ้งเตือนเมื่อ tunnel/BGP ล่ม

---

## 9. Troubleshooting

| อาการ | ตรวจ |
|---|---|
| Tunnel ไม่ขึ้น (IKE) | public IP/NAT-T (UDP 500/4500), PSK, proposal ไม่ตรง (encryption/DH/lifetime), firewall ISP |
| Tunnel ขึ้นแต่ BGP ไม่ขึ้น | IP inside tunnel (169.254.x.x/30) ผิด, ASN ผิด, ACL บล็อก TCP 179 |
| BGP ขึ้นแต่ ping ไม่ได้ | ไม่ได้ประกาศ prefix (ไม่อยู่ใน RIB), ไม่ได้เปิด **route propagation** ใน VPC route table, SG/NSG, firewall on-prem |
| Tunnel ขึ้นลงเป็นระยะ | DPD, ไม่มี traffic (idle timeout) → ใช้ BGP keepalive หรือ SLA probe |
| แอปช้า/ค้าง โอนไฟล์ไม่ได้ | MTU/MSS (ตั้ง `ip tcp adjust-mss 1379`) |
| ใช้เส้น VPN แทน DX | Local pref/AS path/prefix length, BGP ของ DX ล่ม |
| resolve ชื่อไม่ได้ข้ามฝั่ง | conditional forwarder/resolver rule, SG ของ resolver endpoint |
```
show crypto ikev2 sa ; show crypto ipsec sa | i pkts|peer
show ip bgp summary ; show ip bgp neighbors 169.254.10.1 advertised-routes
ping 10.20.10.15 source Loopback0 df-bit size 1400
# AWS: VPN connection → Tunnel details (status, BGP routes received) · CloudWatch TunnelState
```

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Direct Connect เข้ารหัสอยู่แล้ว | ไม่เข้ารหัสโดยค่าเริ่มต้น — ใช้ MACsec/IPsec |
| ตั้ง VPN แค่ tunnel เดียวพอ | AWS ให้ 2 tunnel (2 AZ) ใช้ทั้งคู่ + BGP |
| BGP ขึ้นแล้วใช้งานได้ทันที | ต้องเปิด route propagation และ security group/firewall ด้วย |
| ประกาศ route เท่าไรก็ได้ | มีจำกัด (เช่น 100) — summarize |
| DNS จัดการทีหลังได้ | ไม่มี hybrid DNS แอปจำนวนมากใช้ไม่ได้ |

---

## 11. Cheat Sheet

```
Hybrid = on-prem + cloud · Multi-cloud = หลาย provider
VPN (เร็ว ถูก ผ่านเน็ต ~1.25G/tunnel) vs DX/ExpressRoute/Interconnect (private, เสถียร, ไม่เข้ารหัส default)
AWS VPN: 2 tunnel/2 AZ · BGP · 169.254.x.x/30 · MSS 1379 · route propagation
Redundancy: DX + VPN backup → DX ×2 location · BFD · ทดสอบ failover
BGP: local-pref (ขาออก) · prepend / more specific (ขาเข้า) · ระวัง asymmetric · จำกัดจำนวน route → summarize
Hybrid DNS: Resolver inbound/outbound + conditional forwarder · privatelink zones
IPAM: on-prem / AWS / Azure / GCP แยก supernet ไม่ชน
Multi-cloud: colo/cloud exchange (Equinix/Megaport) · VPN · Aviatrix/Alkira · IaC/policy เดียว
```

---

## 12. แบบทดสอบ 10 ข้อ

1. Hybrid cloud กับ multi-cloud ต่างกันอย่างไร
2. เปรียบเทียบ Site-to-Site VPN กับ Direct Connect (4 ด้าน)
3. ทำไม AWS VPN มี 2 tunnel และควรใช้ routing แบบใด
4. ทำไมต้องตั้ง TCP MSS บน tunnel interface
5. BGP ขึ้นแล้วแต่ instance ใน VPC ping on-prem ไม่ได้ ตรวจอะไร
6. ต้องการให้ traffic ขาเข้าจาก AWS ใช้ DX เป็นหลักและ VPN เป็นสำรอง ทำได้อย่างไร
7. ผลของการประกาศ route เกินจำนวนที่ AWS กำหนดคืออะไร ป้องกันอย่างไร
8. อธิบายการทำ hybrid DNS ระหว่าง AD on-prem กับ AWS
9. ทำไมการวางแผน IP ข้าม cloud สำคัญ
10. ทางเลือกในการเชื่อม AWS กับ Azure มีอะไรบ้าง

<details><summary><b>เฉลย</b></summary>

1. Hybrid = on-prem ทำงานร่วมกับ public cloud; multi-cloud = ใช้ cloud หลายเจ้า
2. VPN ผ่านอินเทอร์เน็ต ติดตั้งเร็ว ราคาต่ำ bandwidth/latency ไม่แน่นอน เข้ารหัส; DX เป็นวงจรส่วนตัว เสถียร bandwidth สูง ติดตั้งนาน ราคาสูงกว่า ไม่เข้ารหัสโดยค่าเริ่มต้น
3. Endpoint อยู่คนละ AZ เพื่อ redundancy — ใช้ BGP (dynamic) ให้ failover อัตโนมัติ
4. Overhead ของ IPsec ทำให้ packet ใหญ่เกิน MTU — ปรับ MSS ให้ TCP ส่ง segment ที่พอดี ป้องกันแอปค้าง
5. On-prem ประกาศ prefix จริงไหม, route propagation ใน VPC route table (หรือ TGW route table), SG/NACL, firewall on-prem, route กลับ
6. AWS ชอบ DX อยู่แล้วเมื่อ prefix เท่ากัน; เสริมด้วย AS-path prepend บน VPN หรือประกาศ prefix ที่เจาะจงกว่าบน DX (และ local pref ฝั่งเราสำหรับขาออก)
7. BGP session อาจถูกปิด/ล่ม — summarize prefix ก่อนประกาศ และใช้ prefix-list/maximum-prefix
8. On-prem DNS ตั้ง conditional forwarder ของโดเมน cloud ไปยัง Route 53 Resolver inbound endpoint; ใน VPC ใช้ outbound endpoint + forwarding rule สำหรับ corp.local ไปยัง DNS ของ AD (และเปิด port 53)
9. IP ที่ชนกันทำให้ route ไม่ได้หลังเชื่อมต่อ และแก้ภายหลังยากมาก — ต้อง summarize ได้เพื่อลดจำนวน route
10. ผ่าน on-prem/colocation, cloud exchange (Equinix Fabric/Megaport), IPsec VPN ระหว่าง cloud, multi-cloud network platform (Aviatrix/Alkira), cross-cloud interconnect
</details>

---

➡️ ต่อไป: **Level 80 — Service Mesh, eBPF & Cloud-Native Networking**
