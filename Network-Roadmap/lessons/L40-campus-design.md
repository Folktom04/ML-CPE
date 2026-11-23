# บทเรียน Level 40 — L3 Switching & Campus Design (ฉบับละเอียด)

> อ่านจบแล้วจะ: ออกแบบเครือข่าย campus ด้วยโครงสร้าง Core–Distribution–Access · เลือกระหว่าง 3-tier กับ Collapsed core · L2 access vs Routed access · คำนวณ oversubscription · ออกแบบ redundancy ให้ไม่มี SPOF · เลือกอุปกรณ์และเขียน HLD/LLD เบื้องต้น

---

## 1. Campus Network คืออะไร

เครือข่ายขององค์กรในพื้นที่เดียว (อาคารเดียวหรือหลายอาคาร) เช่น สำนักงานใหญ่ มหาวิทยาลัย โรงพยาบาล โรงงาน — รวมทั้งสายและ Wi-Fi สำหรับผู้ใช้ อุปกรณ์ IoT และการเชื่อมต่อไปยัง data center/WAN/อินเทอร์เน็ต

**เป้าหมายการออกแบบ**
- **Availability:** ไม่มี single point of failure ในส่วนสำคัญ
- **Scalability:** ขยายจำนวนผู้ใช้/อาคารได้โดยไม่ต้องรื้อ
- **Performance:** bandwidth พอ ไม่มีคอขวด
- **Security:** แบ่งส่วน ควบคุมการเข้าถึง
- **Manageability:** มาตรฐานเดียว ดูแลง่าย แก้ปัญหาเร็ว

---

## 2. Hierarchical Design: 3 ชั้น

```
                    ┌──────── WAN / Internet / Data Center ────────┐
                    │                                               │
        ┌───────── CORE ─────────┐   ← backbone ความเร็วสูง ทนทานสูง
        │ [CORE-1]═══════[CORE-2] │     40/100G · L3 · ไม่ทำ policy หนัก
        └───┬───────────────┬─────┘
            │               │            (routed links / L3)
  ┌──── DISTRIBUTION ────┐  ┌──── DISTRIBUTION ────┐  ← รวมแต่ละอาคาร
  │ [DIST-A1]═══[DIST-A2]│  │ [DIST-B1]═══[DIST-B2]│    gateway ของ VLAN, ACL, QoS, summarize
  └───┬────┬────┬────────┘  └───┬────┬─────────────┘
      │    │    │               │    │
  ── ACCESS ──────────────────────────────────────────  ← จุดเชื่อมต่อผู้ใช้
  [ASW-F1] [ASW-F2] [ASW-F3]  [ASW-F1] [ASW-F2]          PoE, VLAN, port security, 802.1X, QoS marking
   PC AP Phone ...
```

| ชั้น | หน้าที่ | สิ่งที่ทำ | สิ่งที่ไม่ควรทำ |
|---|---|---|---|
| **Access** | เชื่อมอุปกรณ์ปลายทาง | VLAN, PoE, port security, 802.1X, BPDU guard, QoS trust/marking | — |
| **Distribution** | รวม access ของอาคาร/โซน, ขอบเขตระหว่าง L2 กับ L3 | **gateway (SVI + FHRP)**, ACL, route summarization, QoS policy | ต่อผู้ใช้ตรง |
| **Core** | backbone เชื่อม distribution, DC, WAN | **ส่งต่อให้เร็วที่สุด**, redundancy สูง | ACL ซับซ้อน, เชื่อมผู้ใช้ |

**ทำไมต้องแบ่งชั้น:** เป็นโมดูล (เพิ่มอาคารใหม่ = เพิ่ม distribution คู่ใหม่), จำกัดขอบเขตปัญหา (failure domain), แก้ปัญหาง่ายเพราะรู้ว่าแต่ละชั้นทำอะไร

---

## 3. Collapsed Core (2 ชั้น)

รวม **Core + Distribution เป็นชั้นเดียว** (มักเป็น L3 switch คู่)

```
        [CORE/DIST-1]═══[CORE/DIST-2]    ← gateway, routing, ต่อ WAN/FW/server
         │   │   │   ╲ ╱   │   │   │
       [ASW] [ASW] [ASW] ... (dual uplink ไปทั้ง 2 ตัว)
```
- ✅ ราคาถูก ซับซ้อนน้อย เหมาะ **อาคารเดียว / องค์กรขนาดเล็ก–กลาง** (หลายสิบถึงไม่กี่ร้อยพอร์ตต่อชั้น)
- ❌ ขยายเป็นหลายอาคารยาก, ทุกอย่างพึ่ง core คู่นี้

**เลือกอย่างไร:** อาคารเดียว/ไม่กี่ชั้น → collapsed core · หลายอาคาร/คาดว่าจะโตมาก → 3-tier

---

## 4. L2 Access vs Routed Access

### L2 Access (แบบดั้งเดิม)
```
 DIST-1 (HSRP active, STP root) ═══ DIST-2 (standby)
       ╲                         ╱
        ╲ trunk (L2)      trunk ╱
               [ACCESS]                 ← L2 อย่างเดียว gateway อยู่ที่ distribution
```
- Gateway (SVI + HSRP/VRRP) อยู่ที่ distribution, ลิงก์ access→distribution เป็น **trunk**
- **STP ทำงาน** → uplink หนึ่งเส้นถูก block (เว้นแต่ใช้ MLAG/StackWise Virtual ที่ distribution)
- ✅ VLAN ข้ามหลาย access switch ได้ (ใน distribution เดียวกัน), เข้าใจง่าย
- ❌ ต้องดูแล STP + FHRP คู่กัน, converge ช้ากว่า, เสี่ยง loop

### Routed Access
```
 DIST-1 ═══ DIST-2
     ╲       ╱
  L3 ╲     ╱ L3 (routed links, OSPF/EIGRP, ECMP)
     [ACCESS L3]  ← gateway (SVI) อยู่ที่ access switch เอง
```
- Access switch เป็น L3, gateway อยู่ที่ access, uplink เป็น **routed link**
- ✅ **ไม่มี STP ระหว่างชั้น**, ใช้ **ทุก uplink พร้อมกัน (ECMP)**, converge เร็วด้วย routing (+BFD), failure domain เล็ก (VLAN อยู่แค่ใน access switch)
- ❌ VLAN ขยายข้าม access switch ไม่ได้, access switch ต้องรองรับ L3 (ราคาสูงขึ้น), ต้องวาง IP plan ต่อ access switch

### ทางเลือกปัจจุบัน
- **MLAG/StackWise Virtual ที่ distribution + L2 access:** ไม่มี STP block (เพราะ uplink เป็น port-channel เดียวไป 2 ตัว) ได้ทั้งความง่ายของ L2 และใช้ทุกลิงก์
- **Fabric (SD-Access, EVPN-VXLAN campus):** overlay ที่ให้ VLAN/segment เคลื่อนที่ได้บน underlay ที่เป็น L3 ทั้งหมด (สำหรับองค์กรใหญ่)

---

## 5. Redundancy — ไม่มี Single Point of Failure

| ส่วน | วิธีสำรอง |
|---|---|
| Core/Distribution | อุปกรณ์ **คู่** (MLAG/vPC/StackWise Virtual/VSF หรือ routing + FHRP) |
| Uplink | **2 เส้นขึ้นไป** ไปคนละอุปกรณ์ (dual-homed) |
| Gateway | **HSRP/VRRP** หรือ anycast gateway (Level 50) |
| Access switch | ใช้ **stack** เพื่อให้สมาชิกตัวหนึ่งเสียแล้วตัวอื่นยังทำงาน (แต่ผู้ใช้ที่เสียบตัวที่เสียยังได้รับผลกระทบ) |
| Power | **PSU คู่** ต่อ **UPS/PDU คนละ feed** |
| Fiber ระหว่างอาคาร | **2 เส้นทางกายภาพ** (ไม่ใช้ท่อเดียวกัน) |
| Control plane | NSF/SSO, ISSU (upgrade โดยไม่หยุด) ในอุปกรณ์ระดับสูง |
| อุปกรณ์ขอบ | Firewall HA, ISP 2 ราย |

> 🔑 **Redundancy ที่ไม่เคยทดสอบ = ไม่มี redundancy** ต้องทดสอบ failover (ดึงสาย, ปิดอุปกรณ์) ตอนส่งมอบและเป็นระยะ

---

## 6. Oversubscription — คำนวณ bandwidth

**Oversubscription ratio = ผลรวม bandwidth ฝั่งล่าง ÷ bandwidth uplink**
ผู้ใช้ทุกคนไม่ได้ใช้เต็มพร้อมกัน จึงยอมให้ uplink น้อยกว่าผลรวมได้

```
 Access 48 × 1G = 48 Gbps   uplink 2 × 10G = 20 Gbps  → 48/20 = 2.4 : 1  ✅
 Access 48 × 2.5G (mGig สำหรับ Wi-Fi 7) = 120 Gbps  uplink 2 × 10G → 6 : 1  ⚠️ พิจารณา 25G
```
**แนวทางทั่วไป (ไม่ใช่กฎตายตัว):** Access → Distribution ไม่เกินประมาณ **20:1** · Distribution → Core ไม่เกินประมาณ **4:1** · Data center ต่ำกว่านี้มาก (เช่น 3:1 หรือ 1:1)
ใช้ข้อมูลการใช้งานจริง (monitoring, 95th percentile) ประกอบการตัดสินใจ

---

## 7. Stacking vs Chassis vs MLAG

| | Stack | Chassis | MLAG/vPC/SV |
|---|---|---|---|
| ลักษณะ | switch หลายตัวต่อสาย stack เป็นตัวเดียว | กล่องใหญ่ใส่การ์ดได้ | 2 switch อิสระทำงานคู่กัน |
| จัดการ | 1 IP/1 config | 1 เครื่อง | 2 config ต้องสอดคล้อง |
| ใช้ที่ | **Access** | Core/Distribution ขนาดใหญ่ | **Core/Distribution/ToR** |
| upgrade | มักต้อง reload ทั้ง stack (บางรุ่นทำทีละตัวได้) | ISSU (รุ่นสูง) | ทีละตัว |

---

## 8. องค์ประกอบอื่นของ Campus

- **Wireless:** AP ที่ access (PoE+/++ และ mGig สำหรับ Wi-Fi 6E/7), WLC หรือ cloud (Level 51–52)
- **Services:** DHCP, DNS, NTP, RADIUS/NAC, Syslog/SNMP
- **Security:** firewall ที่ขอบ, segmentation (VLAN/VRF/firewall zone), 802.1X/NAC
- **QoS:** marking ที่ access, policy ที่ distribution/WAN (Level 54)
- **Management:** OOB/management VLAN, AAA (TACACS+), monitoring, config backup

---

## 9. ขั้นตอนออกแบบ (ย่อ)

```
 1) Requirements: จำนวนผู้ใช้/อุปกรณ์ต่อชั้น/อาคาร, Wi-Fi, IoT/CCTV, แอปสำคัญ, SLA, งบ, การเติบโต 3-5 ปี
 2) เลือกโครงสร้าง: 3-tier / collapsed core · L2 access / routed access / MLAG
 3) Physical: ตู้ rack ต่อชั้น, ไฟเบอร์ระหว่างอาคาร (2 เส้นทาง), จำนวนพอร์ต + เผื่อ 20-30%
 4) Logical: VLAN plan, IP plan (summarize ได้ต่ออาคาร), routing, STP/FHRP, QoS, security zones
 5) เลือกอุปกรณ์: พอร์ต, PoE budget, uplink speed, ฟีเจอร์ (802.1X, L3), support/EoL, ราคา
 6) เอกสาร: HLD (ภาพรวม + เหตุผล) และ LLD (IP, VLAN, port map, config)
 7) ทดสอบ: failover, performance, security · ส่งมอบ
```

### ปัจจัยเลือก access switch
- จำนวนพอร์ต + เผื่อโต 20–30%
- **PoE budget** (AP, phone, กล้อง — Level 4)
- **Uplink** 10/25G และจำนวน
- mGig (2.5/5G) สำหรับ AP รุ่นใหม่
- ฟีเจอร์: 802.1X, L3 (ถ้า routed access), stacking, QoS
- การจัดการ (cloud/on-prem), อายุการ support/EoL, งบประมาณ

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ทุกองค์กรต้องมี 3 ชั้น | อาคารเดียว/ขนาดเล็กใช้ collapsed core คุ้มกว่า |
| Uplink ต้องเท่ากับผลรวมพอร์ตผู้ใช้ | ยอมให้ oversubscribe ได้ตามพฤติกรรมการใช้งานจริง |
| มีอุปกรณ์คู่ = ไม่มีวันล่ม | ต้องทดสอบ และระวัง shared fate (ไฟ, ท่อไฟเบอร์เดียวกัน) |
| Routed access ดีกว่าเสมอ | เหมาะเมื่อไม่ต้องขยาย VLAN ข้าม access และงบรองรับ L3 switch |

---

## 11. Cheat Sheet

```
Access (ผู้ใช้, PoE, VLAN, security) → Distribution (gateway, ACL, summarize) → Core (เร็ว, ทนทาน)
Collapsed core = core+dist รวมกัน (อาคารเดียว/เล็ก-กลาง)
L2 access: trunk + STP + FHRP ที่ dist · Routed access: L3 ถึง access, ไม่มี STP ข้ามชั้น, ECMP
MLAG/StackWise Virtual ที่ dist = L2 access ที่ไม่มี STP block
Redundancy: อุปกรณ์คู่ · dual uplink · FHRP · PSU คู่ · ไฟเบอร์ 2 เส้นทาง · ทดสอบ failover
Oversubscription = downlink รวม ÷ uplink · access ≤ ~20:1 · dist ≤ ~4:1
เลือก access switch: พอร์ต+เผื่อ, PoE budget, uplink, mGig, 802.1X, EoL
```

---

## 12. แบบทดสอบ 10 ข้อ

1. หน้าที่ของ Access, Distribution, Core
2. Collapsed core คืออะไร เหมาะกับองค์กรแบบใด
3. L2 access กับ Routed access ต่างกันอย่างไร
4. ข้อดีของ routed access 3 ข้อ
5. Access 48 × 1G uplink 2 × 10G oversubscription เท่าไร
6. ยกตัวอย่าง redundancy ที่ควรมีใน campus 5 อย่าง
7. Shared fate คืออะไร ยกตัวอย่างใน campus
8. Stack กับ MLAG ต่างกันอย่างไร
9. ปัจจัยในการเลือก access switch
10. ทำไมต้องทดสอบ failover ก่อนส่งมอบ

<details><summary><b>เฉลย</b></summary>

1. Access = เชื่อมผู้ใช้/อุปกรณ์ (PoE, VLAN, security); Distribution = รวม access, gateway, ACL, summarize; Core = backbone ความเร็วสูงและทนทาน
2. รวม core กับ distribution เป็นชั้นเดียว — อาคารเดียว/องค์กรขนาดเล็ก–กลาง
3. L2 access: access เป็น L2, gateway ที่ distribution, ใช้ trunk + STP; Routed access: gateway อยู่ที่ access, uplink เป็น routed link, ไม่มี STP ระหว่างชั้น
4. ไม่มี STP ข้ามชั้น, ใช้ทุก uplink พร้อมกัน (ECMP), converge เร็ว, failure domain เล็ก
5. 48/20 = 2.4:1
6. Core/distribution คู่, dual uplink, FHRP, PSU คู่ต่อไฟคนละ feed, ไฟเบอร์ระหว่างอาคาร 2 เส้นทาง, firewall HA, ISP 2 ราย
7. ส่วนที่ดูเหมือนสำรองกันแต่เสียพร้อมกันได้ เช่น ไฟเบอร์ 2 เส้นในท่อเดียวกัน หรืออุปกรณ์คู่ต่อ UPS ตัวเดียวกัน
8. Stack รวมหลายตัวเป็น control plane เดียว (นิยมที่ access); MLAG เป็น 2 อุปกรณ์อิสระที่ประสานกันให้ทำ LAG ข้ามเครื่องได้ (นิยมที่ core/distribution)
9. จำนวนพอร์ต + เผื่อโต, PoE budget, uplink speed, mGig, ฟีเจอร์ (802.1X/L3/stack), การจัดการ, support/EoL, ราคา
10. ยืนยันว่า redundancy ทำงานจริง (config ถูก, เวลา converge ยอมรับได้) และเป็นหลักฐานการส่งมอบ
</details>

---

🎉 **จบ Tier 4** · ➡️ ต่อไป: **Level 41 — Routing Table & Static Routing** · กลับไปทำโปรเจคใน [04-switching.md](../04-switching.md)
