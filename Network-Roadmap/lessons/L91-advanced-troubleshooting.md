# บทเรียน Level 91 — Advanced Troubleshooting ระดับองค์กร (ฉบับละเอียด)

> อ่านจบแล้วจะ: จัดการปัญหาที่ยาก (intermittent, ข้ามหลายทีม) อย่างเป็นระบบ · เก็บหลักฐานต่อเนื่อง · วินิจฉัย asymmetric routing, MTU black hole, ECMP polarization, control-plane overload/CoPP, TCAM exhaustion · ทำ packet walk ใน firewall (ASA/FortiGate/Palo Alto) · capture หลายจุดและ align เวลา · ทำงานกับ TAC · เขียน post-mortem

---

## 1. ปัญหาระดับองค์กรต่างจากปัญหาพื้นฐานอย่างไร

| ปัญหาพื้นฐาน (Level 30) | ปัญหาระดับองค์กร |
|---|---|
| เกิดตลอด ทำซ้ำได้ | **เป็นพัก ๆ (intermittent)** เกิดวันละครั้งตอนไม่มีใครดู |
| อยู่ในอุปกรณ์ตัวเดียว | ข้าม **หลายอุปกรณ์/หลายทีม** (network, server, app, security, ISP, cloud) |
| สาเหตุเดียว | **หลายสาเหตุซ้อนกัน** |
| "ใช้ไม่ได้" | "**ช้าบางครั้ง** เฉพาะบางคน เฉพาะบางแอป" |
| ทุกคนยอมรับว่าเป็นปัญหา network | "**network ผิดแน่**" (ต้องพิสูจน์ทั้งผิดและไม่ผิด) |

---

## 2. วิธีคิด (Methodology) — ทบทวนและขยาย

```
 1. กำหนดปัญหาให้ชัด   → ใคร? อะไร? ที่ไหน? เมื่อไร (เวลาแน่นอน)? เริ่มตั้งแต่เมื่อไร? ใครไม่เป็น?
 2. ขอบเขตผลกระทบ      → ผู้ใช้กี่คน/site ไหน/แอปไหน → จัด priority
 3. มีอะไรเปลี่ยน?       → change log, Git diff, patch, ISP maintenance, cert หมดอายุ
 4. รวบรวมหลักฐาน       → log/flow/metric/capture ณ เวลาที่เกิด (ไม่ใช่หลังจากนั้น)
 5. ตั้งสมมติฐาน         → เรียงตามความน่าจะเป็น × ความง่ายในการพิสูจน์
 6. ทดสอบทีละตัว         → เปลี่ยนทีละอย่าง บันทึกผล
 7. แก้ + ยืนยัน         → พิสูจน์ด้วยข้อมูลว่าหายจริง (ไม่ใช่ "ดูเหมือนจะหาย")
 8. Root cause + ป้องกัน → post-mortem, monitoring เพิ่ม, แก้ที่ระบบ
```
### การเปรียบเทียบ (Compare good vs bad) ⭐ เครื่องมือทรงพลังที่สุด
"ผู้ใช้ชั้น 3 เป็น ชั้น 4 ไม่เป็น" → ต่างกันอย่างไร (switch, VLAN, path, DHCP scope, AP, firmware)
"ช้าตอน 10:00 ไม่ช้าตอน 14:00" → อะไรต่างกันในสองช่วงนั้น (backup? update? คนเข้างาน?)

### Timeline
จดทุกเหตุการณ์พร้อม **เวลาที่แม่นยำ (NTP ต้องถูกต้องทุกอุปกรณ์ — Level 55)** → รวม syslog/flow/alert/ticket เข้าด้วยกัน (SIEM/Loki ช่วยได้มาก)

---

## 3. ปัญหา Intermittent — จับให้ได้ตอนเกิด

| เทคนิค | ตัวอย่าง |
|---|---|
| **Ring buffer capture** (จับต่อเนื่อง วนทับ) | `tcpdump -i eth0 -w /data/cap -C 100 -W 50 host 10.1.1.50` (50 ไฟล์ × 100 MB) — หยุดเมื่อเกิดเหตุ |
| **Embedded capture บนอุปกรณ์** | Cisco EPC (`monitor capture`), FortiGate `diagnose sniffer packet`, Palo Alto packet capture, ASA `capture` |
| **Trigger อัตโนมัติ** | Cisco **EEM**: เมื่อ syslog X เกิด → รันคำสั่ง show หลายตัวเก็บลงไฟล์ |
| **Synthetic test ถี่ ๆ** | ping/HTTP ทุก 1–5 วินาทีจากจุดผู้ใช้ไปเป้าหมาย พร้อม timestamp (Smokeping, blackbox) |
| **mtr ยาว ๆ** | `mtr -rwbzc 600 target` (report 600 รอบ — เห็น loss ที่ hop ไหน) |
| **เพิ่มความละเอียด telemetry** | interface counters ทุก 10 วินาทีชั่วคราว |
| **ขอให้ผู้ใช้จดเวลา** | "กดปุ่มนี้เมื่อเกิด" (สคริปต์บันทึก timestamp + traceroute) |

```
! Cisco EEM: เมื่อ BGP neighbor down ให้เก็บข้อมูลทันที
event manager applet BGP-DOWN-CAPTURE
 event syslog pattern "%BGP-5-ADJCHANGE.*Down"
 action 1.0 cli command "enable"
 action 2.0 cli command "show ip bgp summary | append flash:bgp_down.txt"
 action 3.0 cli command "show interfaces | append flash:bgp_down.txt"
 action 4.0 cli command "show logging | append flash:bgp_down.txt"
```

---

## 4. ปัญหาคลาสสิก #1: Asymmetric Routing + Stateful Firewall

```
          ┌──► [FW1] ──┐
 [Client] ┤            ├──► [Server]
          └─── [FW2] ◄─┘
 ขาไป (SYN) ผ่าน FW1 · ขากลับ (SYN-ACK) ผ่าน FW2
 FW2 ไม่เคยเห็น SYN → ไม่มี session → drop SYN-ACK ("no session"/"TCP out of state")
```
**อาการ:** เชื่อมต่อไม่ได้แบบไม่สม่ำเสมอ, บาง flow ได้บาง flow ไม่ได้ (ขึ้นกับ hash ECMP), ICMP ได้ (บาง firewall ไม่ strict กับ ICMP) แต่ TCP ไม่ได้
**ยืนยัน:** capture บนทั้งสอง firewall, ดู route ทั้งสองทิศ (`traceroute` จากทั้งสองฝั่ง), log "out of state"/"no session"
**แก้:**
- ออกแบบ routing ให้สมมาตร (route ขากลับผ่าน firewall เดียวกัน) — ดีที่สุด
- Firewall cluster ที่ **sync session** (active/active ที่รองรับ asymmetric — HA ของ FortiGate/Palo Alto/Check Point)
- ใช้ **SNAT** ที่ firewall ให้ขากลับต้องกลับมาที่ตัวเดิม
- (ไม่แนะนำ) ปิด TCP state check — ลดความปลอดภัย

**จุดที่เกิดบ่อย:** dual ISP + dual firewall, HSRP active บนคนละตัวกับ firewall active, DC สองแห่ง (active-active) ที่มี firewall ของตัวเอง, SD-WAN, cloud (TGW + inspection VPC ต้องเปิด appliance mode)

---

## 5. ปัญหาคลาสสิก #2: MTU / PMTUD Black Hole

```
 Client (MTU 1500) → [Router] → GRE/IPsec tunnel (MTU จริง ~1400) → Server
 Packet 1500 + DF bit → router ต้องส่ง ICMP "Fragmentation Needed" (type 3 code 4) กลับไป
 แต่ firewall บล็อก ICMP ทั้งหมด → client ไม่รู้ → ส่ง 1500 ซ้ำ ๆ → ค้าง
```
**อาการคลาสสิก:**
- **ping ได้, SSH login ได้ แต่ `ls` ใน directory ใหญ่ค้าง**
- เว็บบางเว็บโหลดได้ บางเว็บค้าง (หน้าที่ response ใหญ่), TLS handshake ค้างที่ Server Hello/Certificate (certificate ใหญ่)
- โอนไฟล์เล็กได้ ไฟล์ใหญ่ค้าง · VPN เชื่อมได้แต่ใช้งานแอปไม่ได้
**ทดสอบ:**
```bash
ping -M do -s 1472 10.20.1.10      # Linux: 1472 + 28 = 1500 (DF)
ping -M do -s 1372 10.20.1.10      # ลดจนผ่าน → รู้ path MTU
ping -f -l 1472 10.20.1.10         # Windows
```
```
ping 10.20.1.10 size 1500 df-bit   ! Cisco
```
**แก้:**
- **TCP MSS clamping** บน tunnel/WAN: `ip tcp adjust-mss 1360` (IPsec — Level 58) — แก้ได้กับ TCP
- อนุญาต **ICMP type 3 code 4** (และ ICMPv6 Packet Too Big — **จำเป็นสำหรับ IPv6** ห้ามบล็อก)
- ตั้ง `ip mtu` บน tunnel ให้ถูกต้อง · ใน DC/overlay ตั้ง jumbo บน underlay (Level 74)

---

## 6. ปัญหาคลาสสิก #3: ECMP / LAG Hash Polarization

```
 ชั้นที่ 1 hash แบ่ง flow: ลิงก์ซ้าย = flow ที่ hash "คู่", ขวา = "คี่"
 ชั้นที่ 2 ใช้ hash เดียวกัน (algorithm + seed เดียวกัน) → flow ทั้งหมดที่มาทางซ้ายเป็น "คู่" ทั้งหมด
 → ที่ชั้น 2 ทุก flow ไปลิงก์เดียวกัน อีกลิงก์ว่าง
```
**อาการ:** ลิงก์หนึ่งใน port-channel/ECMP เต็ม อีกเส้นว่าง ทั้งที่ traffic มีหลาย flow
**สาเหตุอื่นของการกระจายไม่สม่ำเสมอ:** hash แค่ src/dst IP (L3) ขณะ traffic ส่วนใหญ่มาจาก IP เดียว (proxy/NAT/backup server), **elephant flow** ไม่กี่ตัว (Level 98)
**แก้:** ใช้ hash L3+L4 (`port-channel load-balance src-dst-mixed-ip-port`), ตั้ง **hash seed/universal ID ต่างกัน** ในแต่ละชั้น, เพิ่มจำนวนลิงก์ (2^n), adaptive load balancing
```
show etherchannel load-balance
show interfaces port-channel 1 etherchannel        ! ดู load ของแต่ละ member
test etherchannel load-balance interface po1 ip 10.1.1.10 10.2.2.20   ! ดูว่า flow นี้ไปลิงก์ไหน
```

---

## 7. ปัญหา Control Plane

### CPU สูง — ต้องแยกให้ได้ว่า "ใครกิน CPU"
```
show processes cpu sorted 5sec            ! Cisco IOS
show processes cpu history                ! กราฟ 60 วินาที/60 นาที/72 ชั่วโมง
```

| สาเหตุ | สัญญาณ |
|---|---|
| **Process** (routing protocol converge, SNMP polling หนัก, SSH/automation ยิงถี่) | process ชื่อ BGP Router, SNMP ENGINE, IP Input |
| **Interrupt / punt** — traffic ที่ hardware ส่งขึ้น CPU | ค่า CPU ส่วน interrupt สูง (`CPU 85%/70%` ตัวหลังคือ interrupt) |

**Traffic ที่ถูก punt ขึ้น CPU:** ARP จำนวนมาก (ARP storm/scan), **TTL expired** (routing loop, traceroute flood), packet ไปยัง IP ของอุปกรณ์เอง, ACL ที่มี `log`, IP options, ICMP redirect/unreachable จำนวนมาก, glean (ARP ไม่ resolve), fragmentation
```
show platform hardware ... punt / show controllers cpu-interface    ! (ขึ้นกับ platform)
debug platform ... ห้ามใช้มั่วใน production (อาจทำให้ CPU แย่ลง)
monitor capture CAP control-plane both match any ; monitor capture CAP start   ! ดูว่าอะไรขึ้น CPU
```
### CoPP (Control Plane Policing)
จำกัดอัตรา traffic แต่ละประเภทที่ขึ้น CPU — ป้องกัน CPU (hardening — Tier 7) แต่ **CoPP drop ก็ทำให้เกิดปัญหาได้** (เช่น BGP/OSPF keepalive ถูก drop → neighbor flap)
```
show policy-map control-plane          ! ดู drop ต่อ class — ถ้า class ของ routing protocol มี drop = ปัญหา
```

### TCAM Exhaustion
**TCAM** = หน่วยความจำ hardware สำหรับ lookup (route, ACL, QoS, MAC) — มีขนาดจำกัด
- เมื่อเต็ม: route/ACL ใหม่ **ไม่ถูกลง hardware** → ถูก process ด้วย software (ช้ามาก/CPU สูง) หรือ **ไม่ทำงานเลย**
- เกิดเมื่อ: รับ **full Internet table** (>1M IPv4 + >200k IPv6) บนอุปกรณ์ที่ไม่รองรับ, ACL ใหญ่มาก (object-group ที่ขยายเป็นหลายพันบรรทัด), IPv6 เพิ่มขึ้น
```
show platform hardware fed switch active fwd-asic resource tcam utilization   ! Catalyst 9k
show hardware capacity / show system resources                                ! (ขึ้นกับ platform)
```
แก้: รับ default route + partial table, summarization, ปรับ SDM template, อุปกรณ์ที่ใหญ่ขึ้น

---

## 8. Packet Walk ใน Firewall

ให้ firewall **จำลอง/ติดตาม** ว่า packet จะถูกทำอะไรในแต่ละขั้น

| Firewall | คำสั่ง |
|---|---|
| **Cisco ASA/FTD** | `packet-tracer input inside tcp 10.1.1.10 51000 203.0.113.10 443 detailed` — เห็นทุก phase: route lookup, ACL, NAT, inspection, ผลลัพธ์ ALLOW/DROP + เหตุผล |
| **FortiGate** | `diagnose debug flow filter addr 10.1.1.10` → `diagnose debug flow trace start 20` → `diagnose debug enable` (ปิดด้วย `diagnose debug disable` เสมอ) — เห็น policy ID ที่ match, "Denied by forward policy check", SNAT/DNAT |
| **Palo Alto** | `test security-policy-match from trust to untrust source 10.1.1.10 destination 8.8.8.8 protocol 6 destination-port 443 application ssl` · Session browser · **packet capture แบบ 4 stage (receive/firewall/transmit/drop)** · `show counter global filter delta yes packet-filter yes` (ดู drop counter) |
| **Check Point** | `fw ctl zdebug drop` · `fw monitor` |
| Linux nftables/iptables | counters ใน rule, `nft monitor trace` |

**Drop counters** ของ firewall บอกเหตุผลการทิ้งได้ละเอียด (เช่น Palo Alto `flow_policy_deny`, `flow_tcp_non_syn_drop` = asymmetric!)

---

## 9. Multi-Point Capture

จับ packet **หลายจุดพร้อมกัน** บน path เพื่อหาว่า packet หาย/ถูกแก้ที่ไหน
```
 [Client]──A──[SW]──B──[FW]──C──[Router]──D──[Server]
 ถ้า SYN เห็นที่ A, B แต่ไม่เห็นที่ C → FW ทิ้ง
 ถ้า SYN ถึง D, SYN-ACK ออกจาก D แต่ไม่ถึง A → ปัญหาขากลับ (route/asymmetric)
```
- เวลาของทุกจุดต้อง **sync ด้วย NTP** · ใช้ filter เดียวกัน (host/port) · เริ่มพร้อมกัน
- รวมไฟล์: `mergecap -w merged.pcapng a.pcap b.pcap c.pcap` · เปรียบเทียบด้วย IP ID/TCP seq (เพื่อยืนยันว่าเป็น packet เดียวกัน — ระวัง NAT เปลี่ยน IP/port)
- ใช้ **SPAN/RSPAN/ERSPAN** หรือ TAP เมื่อ capture บนอุปกรณ์ไม่ได้ (Level 22)
- สังเกต: retransmission, TTL ที่เปลี่ยน (บอกจำนวน hop/อุปกรณ์ที่แทรก), DSCP ที่ถูกเขียนทับ, MSS ที่ถูกแก้, TCP RST ที่มาจากอุปกรณ์กลางทาง (ดู TTL ของ RST ว่ามาจากปลายทางจริงไหม)

---

## 10. ปัญหาอื่นที่พบบ่อยในองค์กร

| ปัญหา | เบาะแส |
|---|---|
| **Duplex mismatch / auto-neg** | late collisions, CRC ฝั่งหนึ่ง — ช้ามากเมื่อโหลดสูง |
| **SFP/optic เสื่อม** | `show interfaces transceiver` — Rx power ต่ำ, CRC เพิ่มขึ้นเรื่อย ๆ |
| **Unicast flooding** | MAC aging (300s) < ARP timeout (4h) + routing asymmetric → traffic flood ทั่ว VLAN |
| **Duplicate IP / ARP flapping** | `%IP-4-DUPADDR`, MAC ของ gateway เปลี่ยนไปมา |
| **STP topology change บ่อย** | `show spanning-tree detail | inc ieee|occurr|from` — พอร์ตที่ไม่มี PortFast ขึ้นลง |
| **DNS ช้า/timeout** | แอป "ช้า" ตอนเริ่มเชื่อมต่อ — ดู DNS response time |
| **Firewall session table เต็ม/timeout สั้น** | connection ค้างนาน (DB) ถูกตัดเงียบ ๆ → ใช้ TCP keepalive/ปรับ timeout |
| **NAT port exhaustion** | ผู้ใช้มากหลัง IP เดียว → เชื่อมต่อใหม่ล้มเหลวเป็นระยะ |
| **Certificate/clock** | TLS/802.1X/VPN ล้มเพราะเวลาเพี้ยนหรือ cert หมดอายุ |

---

## 11. ทำงานกับ Vendor TAC อย่างมืออาชีพ

**ก่อนเปิด case เตรียม:**
- รุ่น, serial, software version, contract number
- **อาการชัดเจน + ผลกระทบทางธุรกิจ** (เพื่อกำหนด severity ให้ถูก: S1 = production down)
- **Timeline** ที่แม่นยำ, topology ย่อ
- `show tech-support` (หรือ tech support file/diagnose bundle) **ณ เวลาที่เกิด** หรือเร็วที่สุด, log, capture
- สิ่งที่ลองแล้วและผล
**ระหว่าง case:** บันทึกเลข case, อัปเดตทุกครั้งที่มีข้อมูลใหม่, ขอ escalate เมื่อจำเป็น (ผ่าน account team/duty manager), ทดสอบ workaround ใน lab ก่อน, **ระวังข้อมูลลับ** ใน show tech (password hash, key — ตรวจก่อนส่ง)

---

## 12. Post-Mortem แบบ Blameless

```
 1. Summary: เกิดอะไร ผลกระทบ (ผู้ใช้/ระยะเวลา/ธุรกิจ)
 2. Timeline: เวลาเกิด → ตรวจพบ → ตอบสนอง → แก้ → ยืนยัน
 3. Root cause (5 Whys) + contributing factors
 4. อะไรทำได้ดี / อะไรควรดีกว่า
 5. Action items: เจ้าของ + กำหนดเสร็จ (ป้องกัน, ตรวจจับเร็วขึ้น, ลดผลกระทบ)
```
**5 Whys ตัวอย่าง:** สาขาเชียงใหม่ใช้ ERP ไม่ได้ → เพราะ VPN ใช้แอปไม่ได้ → เพราะ MTU black hole → เพราะ ISP ใหม่ใช้ PPPoE (MTU 1492) → เพราะ template config ไม่มี `adjust-mss` → **แก้ที่ template + เพิ่ม test MTU ใน checklist ส่งมอบสาขา**
- **Blameless:** มองที่ระบบ/กระบวนการ ไม่ใช่โทษคน → คนกล้าเล่าความจริง → องค์กรเรียนรู้

---

## 13. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ping ได้ = network ไม่ผิด | MTU/asymmetric/firewall state/L7 ยังผิดได้ |
| ปัญหาเป็นพัก ๆ ต้องรอให้เกิดแล้วค่อยดู | ตั้งการเก็บข้อมูลต่อเนื่องไว้ล่วงหน้า |
| CPU สูง = ต้องเปลี่ยนอุปกรณ์ | หาว่า process หรือ punt traffic อะไร — มักแก้ได้ |
| แก้แล้วอาการหาย = รู้ root cause | ต้องพิสูจน์ด้วยข้อมูลและอธิบายกลไกได้ |
| Post-mortem คือหาคนผิด | blameless — แก้ที่ระบบ |

---

## 14. Cheat Sheet

```
Define (who/what/where/when/who not) → scope → what changed → evidence → hypothesis → test 1 อย่าง → fix+verify → RCA
Compare good vs bad · Timeline (NTP!)
Intermittent: ring capture -C -W · EPC/sniffer · EEM trigger · synthetic ถี่ · mtr -c 600
Asymmetric + stateful FW: no session/out of state → routing สมมาตร/session sync/SNAT
MTU black hole: ping ได้ แต่ใหญ่ค้าง → ping -M do -s · adjust-mss · อนุญาต ICMP 3/4, ICMPv6 PTB
Polarization: hash L3+L4 · seed ต่างกัน · test etherchannel load-balance
CPU: process vs interrupt · punt (ARP, TTL expire, ACL log, glean) · CoPP drops · TCAM
Packet walk: ASA packet-tracer · Forti diagnose debug flow · PAN test security-policy-match + counters
Multi-point capture + mergecap · TAC: version, show tech, timeline, impact · Post-mortem 5 Whys blameless
```

---

## 15. แบบทดสอบ 10 ข้อ

1. ทำไมการเปรียบเทียบ "ผู้ที่เป็น" กับ "ผู้ที่ไม่เป็น" จึงมีประโยชน์
2. จะเก็บหลักฐานปัญหาที่เกิดวันละครั้งตอนตี 2 อย่างไร
3. ขาไปผ่าน FW1 ขากลับผ่าน FW2 จะเกิดอะไร แก้อย่างไร
4. อาการใดบ่งชี้ MTU black hole และแก้อย่างไร
5. ECMP polarization คืออะไร
6. CPU ของ router สูง จะแยกว่าเป็น process หรือ traffic ที่ punt อย่างไร ยกตัวอย่าง traffic ที่ punt
7. CoPP drop ทำให้เกิดปัญหาอะไรได้
8. TCAM เต็มมีผลอย่างไร
9. ใช้คำสั่งอะไรดูว่า FortiGate ทิ้ง packet ด้วย policy ไหน
10. ข้อมูลอะไรควรเตรียมก่อนเปิด TAC case

<details><summary><b>เฉลย</b></summary>

1. ความแตกต่างระหว่างสองกลุ่มชี้ไปยังสาเหตุ (switch/VLAN/path/เวลา/firmware) ช่วยตัดสมมติฐานได้เร็ว
2. ตั้ง ring buffer capture, synthetic test ถี่ ๆ พร้อม timestamp, EEM/trigger เก็บ show ตอนเกิด syslog, เพิ่มความละเอียด telemetry ชั่วคราว
3. FW2 ไม่มี session (ไม่เคยเห็น SYN) จึงทิ้ง packet ขากลับ — ทำ routing ให้สมมาตร, ใช้ cluster ที่ sync session, หรือ SNAT
4. Ping ได้แต่ข้อมูลขนาดใหญ่ค้าง (เว็บบางหน้า, TLS, โอนไฟล์ใหญ่, ls ใน SSH) — ทดสอบ ping DF หลายขนาด, แก้ด้วย MSS clamping, อนุญาต ICMP Fragmentation Needed/PTB, ตั้ง MTU ของ tunnel ให้ถูก
5. หลายชั้นใช้ hash แบบเดียวกัน ทำให้ flow ไปกระจุกที่ลิงก์เดียวในชั้นถัดไป
6. ดู `show processes cpu sorted` — ส่วน interrupt สูงแปลว่า traffic ถูก punt — เช่น ARP storm, TTL expired, packet ไปยังอุปกรณ์เอง, ACL log, glean
7. Traffic สำคัญ (เช่น BGP/OSPF keepalive) ถูก drop ทำให้ neighbor flap หรือการจัดการอุปกรณ์ล้มเหลว
8. Route/ACL ใหม่ไม่ลง hardware — ถูกประมวลผลด้วย software (CPU สูง/ช้า) หรือไม่ทำงาน
9. `diagnose debug flow filter ...` + `diagnose debug flow trace start N` + `diagnose debug enable` (แล้ว disable)
10. รุ่น/serial/version/contract, อาการและผลกระทบทางธุรกิจ (severity), timeline, topology, show tech/log/capture ตอนเกิด, สิ่งที่ลองแล้ว
</details>

---

➡️ ต่อไป: **Level 92 — Network Design Methodology**
