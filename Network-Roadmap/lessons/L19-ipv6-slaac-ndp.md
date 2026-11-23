# บทเรียน Level 19 — IPv6 Addressing: SLAAC, DHCPv6, NDP (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ NDP ทั้ง 5 ข้อความ · อุปกรณ์ได้ IPv6 อย่างไร (SLAAC / Stateless DHCPv6 / Stateful DHCPv6) · คำนวณ EUI-64 · DAD · Prefix Delegation · วางแผน IPv6 address plan · ป้องกัน Rogue RA

---

## 1. NDP — Neighbor Discovery Protocol

NDP คือชุดข้อความ **ICMPv6** ที่ทำหน้าที่แทน ARP, ICMP Router Discovery และ Redirect ของ IPv4

| ICMPv6 Type | ข้อความ | ใครส่ง → ใคร | หน้าที่ |
|---|---|---|---|
| **133** | **RS** Router Solicitation | Host → ff02::2 (all routers) | "มี router ไหม? ขอข้อมูลเครือข่าย" |
| **134** | **RA** Router Advertisement | Router → ff02::1 (all nodes) หรือตอบ host | "ฉันคือ router นี่คือ prefix, gateway, flag" (ส่งเป็นระยะด้วย) |
| **135** | **NS** Neighbor Solicitation | Host → solicited-node multicast | "ใครเป็นเจ้าของ IPv6 นี้? MAC อะไร?" (= ARP request) และใช้ใน DAD |
| **136** | **NA** Neighbor Advertisement | เจ้าของ address | "ฉันเอง MAC คือ..." (= ARP reply) |
| **137** | **Redirect** | Router → Host | "ปลายทางนี้ไปทาง router อื่นดีกว่า" |

### Solicited-Node Multicast — ทำไมดีกว่า ARP broadcast
- NS ไม่ส่งถึงทุกเครื่อง แต่ส่งไปที่ multicast **`ff02::1:ffXX:XXXX`** (XX = 24 บิตท้ายของ address ที่ตามหา)
- เฉพาะเครื่องที่ address ลงท้ายตรงกันเท่านั้นที่รับ → รบกวนเครื่องอื่นน้อยกว่า broadcast มาก

**ตัวอย่าง:** หา `2001:db8::12:3456:789a` → ส่ง NS ไปที่ `ff02::1:ff56:789a`

```bash
ip -6 neigh show            # Linux: neighbor table (เหมือน ARP table)
netsh interface ipv6 show neighbors   # Windows
show ipv6 neighbors         # Cisco
```

---

## 2. อุปกรณ์ได้ IPv6 อย่างไร — 3 วิธี

ทุกอย่างเริ่มจาก **Router Advertisement (RA)** ซึ่งมี flag บอกวิธีที่ client ควรใช้

| Flag ใน RA | ความหมาย |
|---|---|
| **A** (Autonomous) ใน Prefix Information | สร้าง address เองจาก prefix นี้ได้ (SLAAC) |
| **O** (Other config) | ไปขอข้อมูลอื่น (เช่น DNS) จาก DHCPv6 |
| **M** (Managed) | ไปขอ **address** จาก DHCPv6 (stateful) |

### วิธีที่ 1: SLAAC (Stateless Address Autoconfiguration)
```
 Host                                          Router
  │ ① สร้าง link-local fe80::xxxx ของตัวเอง + DAD
  │ ② RS ──────────────────────────────────────►│
  │◄──────────────── ③ RA: prefix 2001:db8:1:10::/64, A=1
  │ ④ เอา prefix + interface ID (64 บิต) → 2001:db8:1:10::<interface ID>
  │ ⑤ DAD ตรวจว่าไม่ซ้ำ
  │ ⑥ Default gateway = link-local ของ router (จาก source ของ RA)
```
- **ไม่ต้องมี DHCP server** และ router ไม่ต้องจำว่าใครใช้ address อะไร (stateless)
- **DNS:** ส่งใน RA ได้ด้วย option **RDNSS** (RFC 8106) หรือใช้ stateless DHCPv6
- Default gateway ใน IPv6 มักเป็น **link-local address ของ router** (เช่น fe80::1)

### วิธีที่ 2: SLAAC + Stateless DHCPv6 (O=1)
- address จาก SLAAC
- DNS server, domain name ฯลฯ ขอจาก DHCPv6 (server ไม่ต้องจำ address)

### วิธีที่ 3: Stateful DHCPv6 (M=1)
- DHCPv6 server **แจก address** และจดว่าใครได้อะไร (เหมือน DHCPv4)
- เหมาะกับองค์กรที่ต้องการควบคุม/บันทึกว่าเครื่องไหนใช้ address ใด
- ⚠️ **Default gateway ยังมาจาก RA เสมอ** — DHCPv6 ไม่แจก gateway
- ⚠️ **Android ไม่รองรับ stateful DHCPv6** → ในวงที่มีมือถือ Android ต้องเปิด SLAAC ด้วย

| | SLAAC | SLAAC + Stateless DHCPv6 | Stateful DHCPv6 |
|---|---|---|---|
| Address จาก | เครื่องสร้างเอง | เครื่องสร้างเอง | DHCPv6 server |
| DNS จาก | RA (RDNSS) | DHCPv6 | DHCPv6 |
| Gateway จาก | RA | RA | RA |
| Flag | A=1 | A=1, O=1 | M=1 (A=0) |
| บันทึกว่าใครใช้ address | ❌ | ❌ | ✅ |

DHCPv6 ใช้ **UDP 546 (client) / 547 (server)** และ client ส่งหา multicast `ff02::1:2` (ข้ามวงต้องใช้ relay เหมือน IPv4)

---

## 3. Interface ID — EUI-64 และ Privacy Address

### EUI-64 (สร้างจาก MAC)
```
 MAC:            00:1A:2B : 3C:4D:5E
 1) แบ่งครึ่ง แทรก FF:FE ตรงกลาง
                 00:1A:2B:FF:FE:3C:4D:5E
 2) กลับบิตที่ 7 (U/L bit) ของไบต์แรก
                 00 = 0000 0000 → 0000 0010 = 02
 3) Interface ID = 021A:2BFF:FE3C:4D5E
 Address = 2001:db8:1:10:21a:2bff:fe3c:4d5e
```
- ✅ คงที่ คาดเดาได้ (ดีกับอุปกรณ์เครือข่าย)
- ❌ **เปิดเผย MAC** และติดตามอุปกรณ์ข้ามเครือข่ายได้ → เป็นปัญหาความเป็นส่วนตัว

### Privacy / Random Interface ID
- Windows, macOS, iOS, Android ใช้ **interface ID แบบสุ่ม** (RFC 7217 stable-private และ RFC 8981 temporary address ที่เปลี่ยนเป็นระยะ)
- เครื่องจึงมีหลาย global address: ตัวที่คงที่ (รับการเชื่อมต่อเข้า) + ตัว temporary (ใช้ออกไปข้างนอก)
- ผลกับองค์กร: ติดตามว่าใครใช้ IP ใดยากขึ้น → ต้องเก็บ NDP table/flow log หรือใช้ stateful DHCPv6/802.1X ประกอบ

---

## 4. DAD — Duplicate Address Detection

ก่อนใช้ address ใด ๆ (รวม link-local) เครื่องส่ง **NS ถามหา address ของตัวเอง** (source = `::`)
- **ไม่มีใครตอบ** → ใช้ได้
- **มีคนตอบ NA** → address ซ้ำ ห้ามใช้ (address จะอยู่สถานะ "duplicate")

---

## 5. Prefix Delegation (DHCPv6-PD)

- ISP ให้ **prefix ทั้งก้อน** (เช่น /56) กับ router บ้าน/สาขา ผ่าน DHCPv6-PD
- router นำไปแบ่ง /64 ให้แต่ละ LAN/VLAN ของตัวเองอัตโนมัติ
- ใช้กันทั่วไปในเน็ตบ้านที่รองรับ IPv6

---

## 6. ตัวอย่างการตั้งค่า Cisco

```
ipv6 unicast-routing                              ! เปิดการ route IPv6 (สำคัญ ลืมบ่อย)
interface vlan 10
 ipv6 address 2001:db8:1:10::1/64
 ipv6 nd other-config-flag                        ! O=1 ให้ไปเอา DNS จาก DHCPv6
 ipv6 dhcp server DNS-ONLY                        ! หรือใช้ ipv6 dhcp relay destination <server>
!
ipv6 dhcp pool DNS-ONLY
 dns-server 2001:db8:1:99::53
 domain-name corp.local
!
show ipv6 interface brief
show ipv6 route
show ipv6 neighbors
```
Linux router: `radvd` (ส่ง RA) หรือ `dnsmasq` (RA + DHCPv6)

---

## 7. วางแผน IPv6 Address Plan

**ได้ 2001:db8:abcd::/48** — มี 16 บิต (หลักที่ 4) สำหรับแบ่ง subnet
```
 2001:db8:abcd: S V V V ::/64
                │ └─┴─┴─ VLAN ID (hex 3 หลัก)
                └─────── สาขา/อาคาร (0-F)

 2001:db8:abcd:0010::/64   สำนักงานใหญ่ VLAN 10 (Users)
 2001:db8:abcd:0020::/64   สำนักงานใหญ่ VLAN 20 (Voice)
 2001:db8:abcd:1010::/64   สาขา 1 VLAN 10
 2001:db8:abcd:f000::/52   Infrastructure (loopback, P2P)
```
**หลักการ:** แบ่งตาม nibble (ทีละ 4 บิต = 1 hex) เพื่อให้อ่านง่ายและ summarize ได้, ให้ตัวเลขตรงกับ VLAN ID, ใช้ /64 ทุก LAN, ลิงก์ point-to-point ใช้ /127 (RFC 6164), loopback /128

---

## 8. ความปลอดภัย: Rogue RA

- ใครก็ส่ง RA ได้ → เครื่องผู้ไม่หวังดี (หรือ Windows ที่เปิด ICS ผิดพลาด) ประกาศตัวเป็น router → เครื่องอื่นส่ง traffic ผ่านมัน (MITM) หรือได้ prefix ผิด
- **ป้องกัน:** **RA Guard** บน switch (อนุญาต RA เฉพาะพอร์ตที่ต่อ router จริง), **DHCPv6 Guard**, **ND Inspection/Source Guard**
- แม้องค์กรยังไม่ใช้ IPv6 ก็ควรเปิด RA Guard

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| DHCPv6 แจก default gateway | gateway มาจาก RA เสมอ |
| ทุกอุปกรณ์รองรับ stateful DHCPv6 | Android ไม่รองรับ ต้องเปิด SLAAC |
| IPv6 address ของเครื่องคงที่ตลอด | มี temporary address ที่เปลี่ยนเป็นระยะ |
| ไม่ใช้ IPv6 ก็ไม่ต้องป้องกัน | Rogue RA ทำได้แม้องค์กรไม่ได้ตั้งใจใช้ IPv6 |
| ลืม `ipv6 unicast-routing` ก็ route ได้ | Cisco ไม่ route IPv6 และไม่ส่ง RA ถ้าไม่เปิด |

---

## 10. Cheat Sheet

```
NDP (ICMPv6): RS 133 · RA 134 · NS 135 · NA 136 · Redirect 137
NS ไปที่ solicited-node ff02::1:ffXX:XXXX (24 บิตท้าย) แทน broadcast
SLAAC: RA ให้ prefix (/64, A=1) → เครื่องสร้าง interface ID เอง
O=1 → DNS จาก DHCPv6 (stateless) · M=1 → address จาก DHCPv6 (stateful)
Gateway = link-local ของ router จาก RA เสมอ · Android ไม่รองรับ stateful DHCPv6
EUI-64: แทรก FFFE กลาง MAC + กลับบิต 7 · Privacy address = สุ่ม/เปลี่ยน
DAD = NS ถามหา address ตัวเองก่อนใช้ · DHCPv6 UDP 546/547 · PD = แจก prefix ทั้งก้อน
Plan: /48 → /64 ทุก LAN · แบ่งทีละ nibble · P2P /127 · loopback /128
RA Guard ป้องกัน Rogue RA
```

---

## 11. แบบทดสอบ 10 ข้อ

1. ข้อความ NDP ใดทำหน้าที่แทน ARP request และ ARP reply
2. RS และ RA ส่งไปที่ multicast address ใด
3. คำนวณ EUI-64 interface ID จาก MAC `00:50:56:AB:CD:EF`
4. RA flag M=1 และ O=1 หมายความว่าอะไร
5. ในการใช้ stateful DHCPv6 เครื่องได้ default gateway จากที่ใด
6. ทำไมวงที่มีมือถือ Android ต้องเปิด SLAAC
7. DAD ทำงานอย่างไร
8. Prefix Delegation คืออะไร
9. องค์กรได้ /48 ออกแบบให้ VLAN 20 ที่สาขา 3 มี prefix อะไร (ใช้รูปแบบในบท)
10. Rogue RA คืออะไร ป้องกันอย่างไร

<details><summary><b>เฉลย</b></summary>

1. NS (135) แทน ARP request, NA (136) แทน ARP reply
2. RS → ff02::2 (all routers); RA → ff02::1 (all nodes)
3. 00:50:56 | FF:FE | AB:CD:EF → กลับบิต 7 ของ 00 → 02 → **0250:56FF:FEAB:CDEF**
4. M=1 = ขอ address จาก DHCPv6 (stateful); O=1 = ขอข้อมูลอื่น (DNS) จาก DHCPv6
5. จาก RA (link-local ของ router)
6. Android ไม่รองรับ stateful DHCPv6 จึงได้ address จาก SLAAC เท่านั้น
7. ส่ง NS ถามหา address ที่จะใช้ (source ::) ถ้ามีคนตอบ NA แสดงว่าซ้ำ ห้ามใช้
8. ISP แจก prefix ทั้งก้อน (เช่น /56) ผ่าน DHCPv6 ให้ router นำไปแบ่ง /64 ให้ LAN ของตัวเอง
9. `2001:db8:abcd:3020::/64`
10. ผู้อื่นส่ง RA ปลอมอ้างเป็น router → traffic ผ่านผู้โจมตีหรือได้ prefix ผิด — ป้องกันด้วย RA Guard บน switch
</details>

---

➡️ ต่อไป: **Level 20 — HTTP, HTTPS & TLS พื้นฐาน**
