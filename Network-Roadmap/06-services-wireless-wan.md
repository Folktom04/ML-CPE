# Tier 6 — Wireless, Services, WAN & VPN (Level 51–60)

> เป้าหมายของ Tier: ดูแล Wi-Fi องค์กร, บริการพื้นฐาน (ACL/QoS/NTP/SNMP/AAA) และเชื่อมสาขาด้วย WAN/VPN/SD-WAN

---

## Level 51 — Wireless 802.11 พื้นฐาน

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L51-wireless-basics.md](lessons/L51-wireless-basics.md)

**สิ่งที่ต้องรู้**
- มาตรฐาน: 802.11n (Wi-Fi 4), ac (5), ax (6/6E), be (7)
- ย่าน 2.4 GHz (channel ไม่ทับ 1/6/11), 5 GHz (DFS), 6 GHz
- Channel width 20/40/80/160/320 MHz, MIMO/MU-MIMO, OFDMA
- RSSI (dBm), SNR, noise floor, co-channel interference, adjacent-channel interference
- SSID/BSSID/ESSID, beacon, probe, association, roaming (802.11k/v/r)
- Half-duplex medium, CSMA/CA

**แบบทดสอบ**
1. channel 2.4 GHz ที่ไม่ทับกันคือ
2. RSSI -65 dBm vs -80 dBm อันไหนดีกว่า เหมาะกับงานไหน
3. ทำไม channel 160 MHz ไม่เหมาะกับออฟฟิศหนาแน่น
4. 802.11r ช่วยอะไร
5. DFS คืออะไร

<details><summary>เฉลย</summary>

1. 1, 6, 11
2. -65 ดีกว่า; เป้าหมาย VoIP/วิดีโอ ≥ -67 dBm
3. channel ว่างน้อย → co-channel interference สูง
4. Fast BSS transition — roaming เร็ว (VoIP)
5. Dynamic Frequency Selection: ต้องหลบเรดาร์ในบาง channel 5 GHz
</details>

**5 โปรเจค**
- ⭐ P1: สแกน Wi-Fi รอบบ้าน (WiFi Analyzer/`nmcli dev wifi`) ทำตาราง channel usage
- ⭐⭐ P2: Heatmap บ้าน/ห้องเรียนด้วย Ekahau HeatMapper/NetSpot (free)
- ⭐⭐ P3: Wireshark monitor mode ดู beacon/probe/auth/assoc
- ⭐⭐ P4: เปรียบเทียบ throughput 2.4 vs 5 GHz ที่ระยะต่าง ๆ ด้วย iperf3
- ⭐⭐⭐ P5: สคริปต์ Python เก็บ RSSI/SNR ทุกนาทีขณะเดิน → วาดกราฟ roaming events

---

## Level 52 — WLAN องค์กร: Controller, Design & Security

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L52-wlan-enterprise.md](lessons/L52-wlan-enterprise.md)

**สิ่งที่ต้องรู้**
- Autonomous AP vs Controller-based (WLC, CAPWAP UDP 5246/5247) vs Cloud-managed (Meraki, Mist, Aruba Central)
- Local mode vs FlexConnect
- Security: WPA2-Personal (PSK), WPA2/WPA3-Enterprise (802.1X + RADIUS), WPA3-SAE, OWE (Enhanced Open)
- Guest: captive portal, client isolation, bandwidth limit
- Site survey: predictive, passive, active; capacity planning (clients/AP)
- RRM, band steering, minimum data rate

**แบบทดสอบ**
1. ทำไมองค์กรไม่ควรใช้ PSK เดียวทั้งบริษัท
2. WPA3-SAE ป้องกันอะไรที่ WPA2-PSK ป้องกันไม่ได้
3. FlexConnect ใช้เมื่อไร
4. ปิด data rate ต่ำ (1/2/5.5/11 Mbps) ช่วยอะไร
5. ขั้นตอน site survey ที่ถูกต้อง

<details><summary>เฉลย</summary>

1. คนลาออกต้องเปลี่ยนรหัสทุกคน, ไม่รู้ว่าใครเป็นใคร → ใช้ 802.1X
2. Offline dictionary attack จาก handshake (มี forward secrecy)
3. AP สาขาที่อยากให้ traffic ออกในสาขาเอง ไม่ tunnel กลับ WLC
4. ลด airtime ของ beacon/client ไกล ๆ, ช่วย roaming
5. เก็บ requirement → predictive → ติดตั้ง → post-install validation survey
</details>

**5 โปรเจค**
- ⭐⭐ P1: Packet Tracer WLC + 2 AP + 2 SSID (Corp/Guest)
- ⭐⭐ P2: WPA2-Enterprise ด้วย FreeRADIUS + AP บ้าน (ถ้ารองรับ) หรือ hostapd
- ⭐⭐ P3: Predictive design ชั้นสำนักงาน 100 คน (จำนวน AP, channel plan)
- ⭐⭐ P4: Guest Wi-Fi captive portal ด้วย OpenWrt/pfSense
- ⭐⭐⭐ P5: เขียน Wireless design document ฉบับเต็ม (requirements, survey, SSID, security, roaming, QoS)

---

## Level 53 — ACL (Access Control List)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L53-acl.md](lessons/L53-acl.md)

**สิ่งที่ต้องรู้**
- Standard (src only, วางใกล้ปลายทาง), Extended (src/dst/proto/port, วางใกล้ต้นทาง)
- Named ACL, sequence number, implicit deny ท้ายสุด
- Wildcard mask (inverse), `host`, `any`
- Inbound vs outbound, one ACL per interface/direction/protocol
- ACL ใช้ในที่อื่น: NAT, route-map, VTY, QoS class-map
- Stateless — ต้องคิดถึง return traffic (หรือใช้ `established`/reflexive/firewall)

```
ip access-list extended GUEST-IN
 10 permit udp any any eq 53
 20 deny ip any 10.0.0.0 0.255.255.255
 30 permit ip any any
interface vlan 50
 ip access-group GUEST-IN in
```

**แบบทดสอบ**
1. wildcard ของ 172.16.32.0/20
2. ACL ที่ไม่มี permit เลยผลคืออะไร
3. extended ACL ควรวางที่ไหน
4. จำกัดการ SSH เข้าอุปกรณ์ทำอย่างไร
5. ACL กับ stateful firewall ต่างกันอย่างไร

<details><summary>เฉลย</summary>

1. 0.0.15.255
2. block ทุกอย่าง (implicit deny)
3. ใกล้ต้นทางให้มากที่สุด
4. standard ACL ที่ `line vty` ด้วย `access-class X in`
5. ACL ดูทีละ packet ไม่จำ session; firewall จำ state อนุญาต return traffic อัตโนมัติ
</details>

**5 โปรเจค**
- ⭐ P1: ACL lab 10 ข้อกำหนด (เช่น HR เข้า payroll ได้คนเดียว)
- ⭐⭐ P2: VTY ACL + management VLAN
- ⭐⭐ P3: Python ตรวจ ACL ว่า packet X ผ่านไหม (simulate first-match)
- ⭐⭐ P4: หา rule ซ้ำซ้อน/shadowed ใน ACL ยาว ๆ ด้วยสคริปต์
- ⭐⭐⭐ P5: แปลง policy matrix (Excel) → ACL config อัตโนมัติ + test ด้วย nmap

---

## Level 54 — QoS

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L54-qos.md](lessons/L54-qos.md)

**สิ่งที่ต้องรู้**
- ปัญหา: delay, jitter, loss; VoIP ต้องการ delay < 150ms, jitter < 30ms, loss < 1%
- Classification & Marking: DSCP (EF 46 voice, AF41 video, CS6 network control), CoS 802.1p
- Queuing: FIFO, WFQ, CBWFQ, LLQ (priority queue)
- Congestion avoidance: WRED; Policing vs Shaping
- Trust boundary, MQC (class-map / policy-map / service-policy)
- QoS มีผลเมื่อเกิด congestion เท่านั้น

```
class-map match-any VOICE
 match dscp ef
policy-map WAN-OUT
 class VOICE
  priority percent 20
 class class-default
  fair-queue
policy-map SHAPE
 class class-default
  shape average 50000000
  service-policy WAN-OUT
interface g0/0
 service-policy output SHAPE
```

**แบบทดสอบ**
1. DSCP ของ voice
2. Policing กับ Shaping ต่างกัน
3. ทำไมต้อง shape ก่อน queue บนลิงก์ WAN ที่ ISP จำกัด bandwidth
4. Trust boundary ควรอยู่ที่ไหน
5. ทำไม QoS ไม่ช่วยเมื่อลิงก์ไม่เต็ม

<details><summary>เฉลย</summary>

1. EF (46)
2. Policing ทิ้ง/remark ส่วนเกิน; Shaping buffer แล้วค่อยส่ง (เพิ่ม delay)
3. เพื่อให้ queue เกิดที่ router เรา (ควบคุมได้) ไม่ใช่ที่ ISP (ทิ้งแบบสุ่ม)
4. ที่ access switch/IP phone ใกล้ edge ที่สุดที่เชื่อถือได้
5. ไม่มี queue ให้จัดลำดับ
</details>

**5 โปรเจค**
- ⭐⭐ P1: LLQ สำหรับ voice บน WAN จำลอง (GNS3)
- ⭐⭐ P2: Linux `tc` HTB + fq_codel จำกัด bandwidth ต่อ class
- ⭐⭐ P3: ทดสอบ VoIP quality (MOS) ภายใต้ congestion ก่อน/หลัง QoS
- ⭐⭐ P4: แก้ bufferbloat ในบ้านด้วย SQM (OpenWrt) วัดด้วย waveform bufferbloat test
- ⭐⭐⭐ P5: ออกแบบ QoS policy องค์กร 8-class end-to-end (marking map, ตารางทุก hop)

---

## Level 55 — NTP, Syslog, SNMP

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L55-ntp-syslog-snmp.md](lessons/L55-ntp-syslog-snmp.md)

**สิ่งที่ต้องรู้**
- NTP (UDP 123), stratum, ทำไมเวลาสำคัญ (log correlation, cert, Kerberos), NTP authentication, chrony
- Syslog severity 0–7 (Emergency → Debug) "Every Awesome Cisco Engineer Will Need Ice cream Daily"
- SNMP v1/v2c (community) vs v3 (authPriv), MIB/OID, GET/WALK/TRAP, port 161/162
- Streaming telemetry (gNMI) แทน SNMP ในระบบใหม่

```
ntp server 10.0.0.1 prefer
logging host 10.0.0.50
logging trap informational
service timestamps log datetime msec localtime
snmp-server group NMS v3 priv
snmp-server user nms NMS v3 auth sha AuthPass priv aes 128 PrivPass
```

**แบบทดสอบ**
1. Syslog severity 4 คืออะไร
2. ทำไมควรใช้ SNMPv3
3. ดึง interface table ด้วย snmpwalk
4. เวลาไม่ตรงกันระหว่างอุปกรณ์ส่งผลอะไร
5. stratum 16 หมายถึง

<details><summary>เฉลย</summary>

1. Warning
2. มี authentication + encryption (v2c ส่ง community เป็น plain text)
3. `snmpwalk -v3 -l authPriv -u nms -a SHA -A ... -x AES -X ... host IF-MIB::ifTable`
4. วิเคราะห์ log ข้ามเครื่องไม่ได้, cert/Kerberos fail
5. ไม่ sync (unsynchronized)
</details>

**5 โปรเจค**
- ⭐ P1: ตั้ง chrony server ภายใน + ให้ทุก VM/router sync
- ⭐⭐ P2: rsyslog/syslog-ng รวม log จากอุปกรณ์ทั้งหมด แยกไฟล์ตาม host
- ⭐⭐ P3: Python (pysnmp/easysnmp) poll ifHCInOctets ทุก 1 นาที คำนวณ bandwidth
- ⭐⭐ P4: SNMP trap receiver (snmptrapd) + แจ้งเตือน link down
- ⭐⭐⭐ P5: gNMI streaming telemetry จาก Arista cEOS/SR Linux → Telegraf → InfluxDB

---

## Level 56 — AAA: RADIUS & TACACS+

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L56-aaa-radius-tacacs.md](lessons/L56-aaa-radius-tacacs.md)

**สิ่งที่ต้องรู้**
- Authentication, Authorization, Accounting
- RADIUS (UDP 1812/1813, encrypt เฉพาะ password, ใช้กับ network access/802.1X/VPN)
- TACACS+ (TCP 49, encrypt ทั้ง payload, แยก AuthN/AuthZ, command authorization — ใช้กับ device admin)
- Server: Cisco ISE, Aruba ClearPass, FreeRADIUS, Microsoft NPS, tac_plus
- Local fallback account ต้องมีเสมอ

```
aaa new-model
aaa authentication login default group tacacs+ local
aaa authorization exec default group tacacs+ local
aaa accounting commands 15 default start-stop group tacacs+
```

**แบบทดสอบ**
1. ใช้ TACACS+ หรือ RADIUS สำหรับ admin login อุปกรณ์ เพราะอะไร
2. RADIUS ใช้ port อะไร
3. ทำไมต้องมี `local` ต่อท้าย
4. Accounting มีประโยชน์อะไร
5. NPS คืออะไร

<details><summary>เฉลย</summary>

1. TACACS+ — command authorization ละเอียด + encrypt ทั้ง packet
2. 1812 (auth), 1813 (accounting)
3. เมื่อ server ล่ม ยังเข้าอุปกรณ์ได้
4. Audit ว่าใครทำอะไรเมื่อไร
5. Network Policy Server — RADIUS ของ Windows Server
</details>

**5 โปรเจค**
- ⭐⭐ P1: FreeRADIUS + router login ด้วย RADIUS
- ⭐⭐ P2: tac_plus (TACACS+) + command authorization (helpdesk ใช้ได้แค่ show)
- ⭐⭐ P3: เชื่อม FreeRADIUS กับ AD/LDAP
- ⭐⭐ P4: Accounting log → dashboard ว่าใครแก้ config อะไร
- ⭐⭐⭐ P5: ระบบ RADIUS HA 2 ตัว + ทดสอบ failover + เอกสาร

---

## Level 57 — WAN Technologies

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L57-wan-technologies.md](lessons/L57-wan-technologies.md)

**สิ่งที่ต้องรู้**
- Leased line, MPLS L3VPN (PE/CE/P), Metro Ethernet/EPL/EVPL, Broadband (FTTx), 4G/5G, Satellite (LEO)
- SLA: availability (99.9% = 8.76 ชม./ปี), latency, jitter, MTTR
- Hub-and-spoke vs full mesh; PPPoE, MTU/MSS (1492, `ip tcp adjust-mss`)
- Internet breakout: centralized vs local
- DMVPN (mGRE + NHRP + IPsec) เป็นพื้นฐานก่อน SD-WAN

**แบบทดสอบ**
1. availability 99.99% ต่อปี downtime เท่าไร
2. ทำไม PPPoE ต้องปรับ MSS
3. MPLS L3VPN: ใครดูแล routing ระหว่างสาขา
4. ข้อดี local internet breakout
5. DMVPN ประกอบด้วยอะไร

<details><summary>เฉลย</summary>

1. ~52.6 นาที
2. PPPoE header 8 byte → MTU 1492 ต้องลด MSS (1452) ไม่ให้ fragment/black hole
3. ISP (PE routers) แลก route กับ CE ผ่าน BGP/OSPF/static
4. ลด latency ไป SaaS, ลดภาระลิงก์ HQ
5. mGRE, NHRP, IPsec (+ routing protocol)
</details>

**5 โปรเจค**
- ⭐⭐ P1: ตารางเปรียบเทียบ WAN ทุกแบบ (ราคา/SLA/ความเร็ว) ในประเทศไทย
- ⭐⭐ P2: Lab MPLS L3VPN ย่อ (PE/CE) ใน GNS3
- ⭐⭐ P3: Lab DMVPN Phase 3 hub + 2 spoke
- ⭐⭐ P4: ทดลองปัญหา MTU/MSS (PMTUD black hole) แล้วแก้
- ⭐⭐⭐ P5: ออกแบบ WAN 30 สาขา (2 ลิงก์/สาขา) + คำนวณ availability และงบประมาณ

---

## Level 58 — Site-to-Site VPN (IPsec)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L58-ipsec-site-to-site.md](lessons/L58-ipsec-site-to-site.md)

**สิ่งที่ต้องรู้**
- IPsec: IKEv1/IKEv2, Phase 1 (IKE SA) / Phase 2 (IPsec SA, Child SA)
- ESP (protocol 50), AH (51), NAT-T (UDP 4500), IKE (UDP 500)
- Encryption (AES-GCM), integrity (SHA-256), DH group (14, 19, 20), PFS, lifetime
- Policy-based vs Route-based (VTI) VPN
- Proxy-ID / traffic selector mismatch = ปัญหาอันดับ 1 ข้ามยี่ห้อ
- GRE over IPsec (รองรับ multicast/routing protocol)

**แบบทดสอบ**
1. Phase 1 ขึ้น แต่ Phase 2 ไม่ขึ้น สาเหตุยอดฮิต
2. Route-based ดีกว่า policy-based อย่างไร
3. PFS คืออะไร
4. ทำไมต้อง GRE over IPsec ในบางกรณี
5. port/protocol ที่ firewall ต้องเปิดสำหรับ IPsec

<details><summary>เฉลย</summary>

1. traffic selector/proxy ID ไม่ตรง, transform set/PFS ไม่ตรง
2. ใช้ routing (รวม dynamic) ได้ง่าย ไม่ต้องแก้ policy ทุกครั้งที่เพิ่ม subnet
3. Perfect Forward Secrecy — สร้าง key ใหม่ด้วย DH ทุกครั้ง key รั่วไม่กระทบ session อื่น
4. IPsec ล้วนไม่ส่ง multicast → ใช้ OSPF/EIGRP ผ่านไม่ได้
5. UDP 500, UDP 4500, ESP (50)
</details>

**5 โปรเจค**
- ⭐⭐ P1: IPsec VTI ระหว่าง 2 router (GNS3)
- ⭐⭐ P2: strongSwan site-to-site ระหว่าง 2 Linux VM
- ⭐⭐ P3: pfSense/OPNsense ↔ Linux VPN (ข้ามยี่ห้อ)
- ⭐⭐⭐ P4: VPN + OSPF/BGP บน tunnel + redundant tunnel 2 ISP
- ⭐⭐⭐ P5: Site-to-site ระหว่าง lab บ้านกับ AWS/Azure VPN gateway (free tier/เครดิต) + ลบทรัพยากรหลังทำ

---

## Level 59 — Remote Access VPN (SSL VPN, WireGuard, OpenVPN)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L59-remote-access-vpn.md](lessons/L59-remote-access-vpn.md)

**สิ่งที่ต้องรู้**
- Client-based (AnyConnect/Secure Client, GlobalProtect, FortiClient) vs clientless
- Full tunnel vs Split tunnel (ข้อดี/ข้อเสียด้าน security/bandwidth)
- WireGuard (UDP, key-based, เร็ว เรียบง่าย), OpenVPN (TLS)
- MFA, posture check, certificate-based auth
- ZTNA (Tailscale, Cloudflare Access, Zscaler Private Access) เป็นทางเลือกแทน VPN

```ini
# wg0.conf (server)
[Interface]
Address = 10.99.0.1/24
ListenPort = 51820
PrivateKey = <server-private>
[Peer]
PublicKey = <client-public>
AllowedIPs = 10.99.0.2/32
```

**แบบทดสอบ**
1. Split tunnel ข้อดีข้อเสีย
2. WireGuard ใช้ protocol/port อะไร
3. AllowedIPs ใน WireGuard มีหน้าที่อะไร
4. ทำไม remote access VPN ต้องมี MFA
5. ZTNA ต่างจาก VPN อย่างไร

<details><summary>เฉลย</summary>

1. ข้อดี: ลดภาระ HQ, เร็ว; ข้อเสีย: traffic internet ไม่ถูกตรวจโดย security stack องค์กร
2. UDP (default 51820)
3. ทั้ง ACL ขาเข้า และ routing ขาออก (cryptokey routing)
4. รหัสผ่านรั่ว/phishing บ่อย — VPN เป็นเป้าหมายหลักของ ransomware
5. ZTNA ให้สิทธิ์ระดับแอปตาม identity/posture ไม่ใช่ทั้ง network
</details>

**5 โปรเจค**
- ⭐ P1: WireGuard server บน VPS/Raspberry Pi เข้าบ้านจากมือถือ
- ⭐⭐ P2: OpenVPN + certificate PKI (easy-rsa)
- ⭐⭐ P3: เปรียบเทียบ throughput/latency WireGuard vs OpenVPN
- ⭐⭐ P4: Tailscale/Headscale mesh VPN 3 เครื่อง + ACL
- ⭐⭐⭐ P5: Remote access VPN + MFA (FreeRADIUS + TOTP) + split tunnel policy + เอกสารสำหรับผู้ใช้

---

## Level 60 — SD-WAN & SASE

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L60-sdwan-sase.md](lessons/L60-sdwan-sase.md)

**สิ่งที่ต้องรู้**
- SD-WAN: แยก control/data plane, overlay บน transport หลายแบบ (MPLS+Internet+LTE)
- Application-aware routing, SLA probes (loss/latency/jitter), zero-touch provisioning
- ผู้ให้บริการ: Cisco Catalyst SD-WAN (Viptela), Fortinet, VMware VeloCloud, Palo Alto Prisma, Versa
- SASE = SD-WAN + SSE (SWG, CASB, ZTNA, FWaaS) บน cloud
- ข้อควรระวัง: vendor lock-in, design overlay/underlay, visibility

**แบบทดสอบ**
1. SD-WAN ต่างจาก DMVPN อย่างไร
2. Application-aware routing ทำงานอย่างไร
3. ZTP คืออะไร
4. SASE ประกอบด้วยอะไร
5. underlay vs overlay

<details><summary>เฉลย</summary>

1. มี controller ศูนย์กลาง, policy ตามแอป, จัดการ GUI/API, วัด SLA อัตโนมัติ
2. ระบุแอป (DPI) → เลือกลิงก์ที่ผ่าน SLA ของแอปนั้นแบบ real-time
3. Zero-touch provisioning: เสียบอุปกรณ์แล้วดึง config จาก controller เอง
4. Network (SD-WAN) + Security (SWG, CASB, ZTNA, FWaaS) จาก cloud
5. Underlay = เครือข่ายขนส่งจริง; Overlay = tunnel/logical network บนนั้น
</details>

**5 โปรเจค**
- ⭐⭐ P1: เปรียบเทียบ SD-WAN 4 ยี่ห้อ (ฟีเจอร์/license/ราคา)
- ⭐⭐ P2: Lab Cisco SD-WAN (Cisco DevNet Sandbox ฟรี) สำรวจ policy
- ⭐⭐ P3: ทำ "SD-WAN จิ๋ว" ด้วย Linux: 2 WAN + สคริปต์วัด SLA → เลือก route ตามแอป (PBR)
- ⭐⭐ P4: เขียน business case ย้ายจาก MPLS → SD-WAN (ROI)
- ⭐⭐⭐ P5: Capstone Tier 6: HQ + 3 สาขา: Wi-Fi Enterprise, QoS voice, IPsec/SD-WAN จำลอง, AAA, NTP/Syslog/SNMP ครบ + เอกสาร
