# คำสั่งตรวจเช็ค Cisco (IOS / IOS-XE / NX-OS)

> 📘 คำอธิบายละเอียดพร้อมตัวอย่างผลลัพธ์: [explained/02-cisco-explained.md](explained/02-cisco-explained.md)

> คำสั่ง `show` ใช้อ่านอย่างเดียว ปลอดภัยต่อการรันบนระบบจริง · คำสั่ง `debug`, `clear` และการตั้งค่าต้องทำตาม change process ([Level 95](../lessons/L95-change-itil-documentation.md))
> ส่วนใหญ่ใช้ได้ทั้ง IOS และ IOS-XE · ช่องที่ระบุ NX-OS คือ Nexus

---

## 0. เทคนิคการใช้ CLI

| เทคนิค | ตัวอย่าง |
|---|---|
| กรองเฉพาะบรรทัด | `show run \| include ntp` · `show log \| include LINK` |
| ไม่เอาบรรทัดที่มีคำนี้ | `show ip int brief \| exclude unassigned` |
| เริ่มแสดงตั้งแต่บรรทัดที่เจอ | `show run \| begin interface Gi1/0/10` |
| ดูเฉพาะ section | `show run \| section router ospf` · `show run interface Gi1/0/10` |
| ไม่ให้หยุดทีละหน้า | `terminal length 0` |
| รันคำสั่ง show ใน config mode | `do show ip int brief` |
| นับบรรทัด (IOS-XE) | `show int status \| count connected` |
| NX-OS ดูผลเป็น JSON | `show ip route \| json` |

---

## 1. ภาพรวมอุปกรณ์

| ตรวจ | คำสั่ง |
|---|---|
| รุ่น, version, uptime, เหตุผลที่ reboot ครั้งล่าสุด | `show version` |
| serial, module | `show inventory` |
| CPU (เรียงตามที่ใช้มาก) | `show processes cpu sorted` · `show processes cpu history` |
| Memory | `show processes memory sorted` · `show memory statistics` · NX-OS `show system resources` |
| พัดลม, ไฟ, อุณหภูมิ, PSU | `show environment all` (Catalyst 9k: `show environment`) · NX-OS `show environment` |
| เวลา | `show clock` |
| NTP | `show ntp associations` · `show ntp status` |
| Log | `show logging` · `show logging \| include %` |
| พื้นที่ flash / image | `dir flash:` · `show boot` |
| Stack (Catalyst) | `show switch` · `show switch stack-ports` |
| ข้อมูลทั้งหมดสำหรับเปิด TAC | `show tech-support` (ใหญ่มาก — ส่งออกเป็นไฟล์) |

---

## 2. Interface และ Layer 1

| ตรวจ | คำสั่ง |
|---|---|
| **สรุป IP และสถานะทุก interface** ⭐ | `show ip interface brief` |
| สถานะพอร์ต switch (connected/notconnect/err-disabled, VLAN, speed, duplex) | `show interfaces status` |
| รายละเอียด (errors, CRC, drops, utilization, duplex) | `show interfaces Gi1/0/10` |
| เฉพาะ error ทุกพอร์ต | `show interfaces counters errors` |
| description | `show interfaces description` |
| พอร์ตที่ err-disabled และสาเหตุ | `show interfaces status err-disabled` · `show errdisable recovery` |
| SFP: สัญญาณแสง Tx/Rx, อุณหภูมิ | `show interfaces transceiver detail` · NX-OS `show interface Eth1/1 transceiver details` |
| ทดสอบสายทองแดง (TDR) | `test cable-diagnostics tdr interface Gi1/0/10` → `show cable-diagnostics tdr interface Gi1/0/10` |
| PoE | `show power inline` · `show power inline Gi1/0/10 detail` |
| ล้าง counter (เพื่อดูว่า error ยังเพิ่มไหม) | `clear counters Gi1/0/10` |

### อ่านผล `show interfaces`
| เห็น | ความหมาย |
|---|---|
| `up/up` | ปกติ |
| `up/down` | L1 ขึ้นแต่ L2 ไม่ขึ้น (encapsulation/keepalive ผิด, ฝั่งตรงข้ามมีปัญหา) |
| `down/down` | ไม่มีสัญญาณ: สายขาด, ฝั่งตรงข้ามปิด, SFP ไม่ตรงชนิด |
| `administratively down` | ถูก `shutdown` อยู่ |
| `err-disabled` | ถูกปิดอัตโนมัติ (port-security, BPDU guard, loop) |
| `CRC`, `input errors` เพิ่มขึ้นเรื่อย ๆ | สาย/หัว/SFP เสีย, สัญญาณรบกวน |
| `late collision` | **duplex mismatch** |
| `output drops` | congestion (ลิงก์เต็ม/microburst) |
| `Rx power` ต่ำกว่า low warning | ไฟเบอร์สกปรก/งอ/ยาวเกิน/SFP เสื่อม |

---

## 3. Switching (VLAN, Trunk, STP, MAC)

| ตรวจ | คำสั่ง |
|---|---|
| VLAN และพอร์ตในแต่ละ VLAN | `show vlan brief` |
| Trunk: VLAN ที่อนุญาตและที่ใช้งานจริง, native VLAN | `show interfaces trunk` |
| โหมดของพอร์ต (access/trunk, VLAN) | `show interfaces Gi1/0/10 switchport` |
| **MAC อยู่พอร์ตไหน** ⭐ | `show mac address-table address aabb.cc00.1234` |
| MAC บนพอร์ต / VLAN | `show mac address-table interface Gi1/0/10` · `show mac address-table vlan 20` |
| STP: root, บทบาทพอร์ต | `show spanning-tree vlan 20` · `show spanning-tree summary` |
| STP เปลี่ยนบ่อยไหม (หา loop/พอร์ตขึ้นลง) | `show spanning-tree detail \| include ieee\|occurr\|from\|is exec` |
| EtherChannel | `show etherchannel summary` (ต้องเห็น `(SU)` และ member `(P)`) |
| LACP | `show lacp neighbor` |
| อุปกรณ์ข้างเคียง | `show cdp neighbors detail` · `show lldp neighbors detail` |
| Port security | `show port-security` · `show port-security interface Gi1/0/10` |
| DHCP snooping / DAI | `show ip dhcp snooping binding` · `show ip arp inspection statistics` |
| 802.1X | `show access-session interface Gi1/0/10 details` |
| NX-OS vPC | `show vpc` · `show vpc consistency-parameters global` |

**หาเครื่องจาก IP:** `show ip arp 10.0.20.55` (บน L3 switch/router ได้ MAC) → `show mac address-table address <MAC>` → ได้พอร์ต → ถ้าเป็น trunk/uplink ให้ `show cdp neighbors` แล้วตามไปที่ switch ถัดไป

---

## 4. Routing

| ตรวจ | คำสั่ง |
|---|---|
| **ตาราง route** ⭐ | `show ip route` · NX-OS `show ip route vrf all` |
| route ไป IP นี้ใช้เส้นไหน | `show ip route 10.20.1.5` |
| ดูเฉพาะชนิด | `show ip route static` · `show ip route ospf` · `show ip route bgp` |
| route ใน VRF | `show ip route vrf CUST-A` |
| ข้อมูลส่งจริงใน hardware (CEF) | `show ip cef 10.20.1.5 detail` |
| ARP | `show ip arp` · `show ip arp 10.0.20.55` |
| OSPF neighbor (ต้องเป็น FULL) | `show ip ospf neighbor` |
| OSPF interface (area, cost, timer) | `show ip ospf interface brief` |
| BGP สรุป (State/PfxRcd) | `show ip bgp summary` · `show bgp all summary` |
| BGP route ที่รับ/ส่ง | `show ip bgp neighbors 203.0.113.1 received-routes` (ต้องมี soft-reconfig) · `... advertised-routes` |
| BGP ทางที่เลือก | `show ip bgp 8.8.8.0` |
| EIGRP | `show ip eigrp neighbors` · `show ip eigrp topology` |
| HSRP / VRRP | `show standby brief` · `show vrrp brief` |
| IP SLA / track | `show ip sla statistics` · `show track` |
| BFD | `show bfd neighbors` |
| IPv6 | `show ipv6 interface brief` · `show ipv6 route` · `show ipv6 neighbors` |

### อ่าน `show ip route`
```
Codes: C - connected, L - local, S - static, O - OSPF, B - BGP, D - EIGRP, * - candidate default
O    10.20.0.0/16 [110/20] via 10.0.0.2, 00:12:41, GigabitEthernet0/1
     └ prefix      └ AD/metric  └ next-hop    └ อายุ route  └ ขาออก
S*   0.0.0.0/0 [1/0] via 203.0.113.1                    ← default route
Gateway of last resort is 203.0.113.1 to network 0.0.0.0
```
AD (ค่ายิ่งน้อยยิ่งน่าเชื่อถือ): connected 0 · static 1 · eBGP 20 · EIGRP 90 · OSPF 110 · RIP 120 · iBGP 200

### อ่านสถานะ neighbor
| Protocol | ปกติ | ติดค้าง → สาเหตุที่พบบ่อย |
|---|---|---|
| OSPF | `FULL` (บน LAN กับ DROTHER อาจเห็น `2WAY` ซึ่งปกติ) | `INIT`/ไม่ขึ้น: hello/dead, area, subnet, auth, ACL · `EXSTART/EXCHANGE`: **MTU ไม่ตรงกัน** |
| BGP | State/PfxRcd เป็น **ตัวเลข** | `Idle`/`Active`: IP/AS ผิด, TCP 179 ถูกบล็อก, update-source, ebgp-multihop · `(PfxRcd)` = 0: ไม่ได้ประกาศ/filter |

---

## 5. Ping และ Traceroute บน Cisco

```
ping 10.20.1.5
ping 10.20.1.5 source Loopback0              ! ทดสอบทาง route ขากลับของ loopback
ping 10.20.1.5 source Vlan20 repeat 100
ping 10.20.1.5 size 1500 df-bit              ! ทดสอบ MTU
ping vrf CUST-A 10.20.1.5
traceroute 10.20.1.5 source Loopback0 numeric
! NX-OS
ping 10.20.1.5 vrf default source 10.0.0.1 count 100
ping 10.20.1.5 packet-size 1472 df-bit
```
| สัญลักษณ์ใน ping | ความหมาย |
|---|---|
| `!` | ได้รับคำตอบ |
| `.` | timeout |
| `U` | destination unreachable |
| `M` | ต้อง fragment แต่ตั้ง DF ไว้ (ปัญหา MTU) |
| `Q` | source quench |
| `&` | TTL หมด |

> ping ครั้งแรกมักได้ `.!!!!` เพราะรอ ARP — ปกติ

---

## 6. ACL, NAT, Services

| ตรวจ | คำสั่ง |
|---|---|
| ACL และจำนวนครั้งที่ match | `show access-lists` · `show ip access-lists MY-ACL` |
| ACL ที่ผูกกับ interface | `show ip interface Gi0/1 \| include access list` |
| NAT translation | `show ip nat translations` · `show ip nat statistics` |
| DHCP server | `show ip dhcp binding` · `show ip dhcp pool` · `show ip dhcp conflict` |
| DHCP relay บน SVI | `show run interface Vlan20 \| include helper` |
| QoS | `show policy-map interface Gi0/1` |
| SNMP | `show snmp` · `show snmp user` |
| AAA | `show aaa servers` · `test aaa group tacacs+ user pass legacy` |
| ใครล็อกอินอยู่ | `show users` · `show ssh` |
| IPsec VPN | `show crypto ikev2 sa` · `show crypto isakmp sa` · `show crypto ipsec sa \| include peer\|pkts` |
| Control plane | `show policy-map control-plane` |

---

## 7. จับ Packet บน Cisco (IOS-XE EPC)

```
monitor capture CAP interface Gi1/0/10 both
monitor capture CAP match ipv4 host 10.0.20.55 any
monitor capture CAP buffer size 10
monitor capture CAP start
! ... ทดสอบ ...
monitor capture CAP stop
show monitor capture CAP buffer brief
monitor capture CAP export flash:cap.pcap
no monitor capture CAP
```
NX-OS: `ethanalyzer local interface inband capture-filter "host 10.0.20.55" limit-captured-frames 100`

---

## 8. Config และการเปลี่ยนแปลงอย่างปลอดภัย

| งาน | คำสั่ง |
|---|---|
| ดู config ที่ใช้อยู่ / ตอนบูต | `show running-config` · `show startup-config` |
| เทียบ running กับ startup | `show archive config differences nvram:startup-config system:running-config` |
| บันทึก | `copy running-config startup-config` (หรือ `write memory`) |
| backup ออกไปเก็บ | `copy running-config scp://user@10.0.0.50/sw01.cfg` |
| **กันตัดตัวเองก่อนแก้ remote** | `reload in 10` → แก้ → ใช้งานได้แล้ว `reload cancel` (อย่า save ก่อนยืนยัน) |
| ใครแก้อะไร (ถ้าเปิด archive log) | `show archive log config all` |

---

## 9. Cheat Sheet ย่อ

```
show version / inventory / environment / processes cpu sorted / logging
show ip interface brief · show interfaces status · show interfaces counters errors · show int transceiver detail
show vlan brief · show interfaces trunk · show mac address-table address <mac> · show spanning-tree summary
show etherchannel summary · show cdp|lldp neighbors detail
show ip route [ip] · show ip arp · show ip ospf neighbor · show ip bgp summary · show standby brief
show access-lists · show ip nat translations · show crypto ipsec sa
ping <ip> source <intf> size 1500 df-bit · traceroute <ip> source <intf> numeric
```
