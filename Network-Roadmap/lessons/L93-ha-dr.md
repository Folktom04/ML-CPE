# บทเรียน Level 93 — High Availability & Disaster Recovery (ฉบับละเอียด)

> อ่านจบแล้วจะ: คำนวณ availability (MTBF/MTTR, ต่ออนุกรม/ขนาน) · ใส่ redundancy ทุกชั้นอย่างมีเหตุผล · เข้าใจ failure domain, blast radius, shared fate · กำหนด RPO/RTO · ออกแบบ DR site (hot/warm/cold) · active-active vs active-standby · ใช้กลไก fast convergence (BFD, NSF/GR, ISSU) · ทำ FMEA · ทดสอบ failover (game day/chaos)

---

## 1. Availability คืออะไร

```
 Availability = เวลาที่ใช้งานได้ / เวลาทั้งหมด
              = MTBF / (MTBF + MTTR)
 MTBF = Mean Time Between Failures (นานแค่ไหนจะเสีย)
 MTTR = Mean Time To Repair/Recover (เสียแล้วกู้นานแค่ไหน)
```
ตัวอย่าง: switch MTBF 200,000 ชั่วโมง, MTTR 4 ชั่วโมง (รอช่างพร้อมอะไหล่) → 200,000 / 200,004 = **99.998%**
→ ถ้าไม่มีอะไหล่และต้องรอ 3 วัน (72 ชม.) → 99.964% — **MTTR สำคัญพอ ๆ กับ MTBF** (อะไหล่, support contract, runbook, automation)

| Availability | Downtime ต่อปี |
|---|---|
| 99% | 3.65 วัน |
| 99.9% | 8.76 ชั่วโมง |
| 99.95% | 4.38 ชั่วโมง |
| 99.99% | 52.6 นาที |
| 99.999% | 5.26 นาที |

---

## 2. Serial vs Parallel

### อนุกรม (Serial) — ทุกตัวต้องทำงาน
```
 [ISP] → [Router] → [Firewall] → [Core] → [Server]
 A_total = A1 × A2 × A3 × ...
 5 อุปกรณ์ × 99.9% = 0.999^5 = 99.5%  ← แย่กว่าอุปกรณ์ทุกตัว!
```
### ขนาน (Parallel) — ตัวใดตัวหนึ่งทำงานก็พอ
```
 A_total = 1 − (1 − A1) × (1 − A2)
 2 ตัว × 99% → 1 − (0.01 × 0.01) = 99.99%
```
### รวมกัน
```
 ISP คู่ (99.5% แต่ละเส้น) → 1 − 0.005² = 99.9975%
 Firewall คู่ (99.9%)    → 99.9999%
 Core คู่ (99.95%)       → 99.999975%
 End-to-end ≈ 0.999975 × 0.999999 × 0.99999975 ≈ 99.997%
```
⚠️ สูตรขนานถือว่า **ล้มเหลวอย่างอิสระ** — ถ้ามี shared fate (ข้อ 4) ตัวเลขจริงต่ำกว่านี้มาก และยังต้องคิด **ความสำเร็จของ failover เอง** (failover ที่ไม่เคยทดสอบอาจไม่ทำงาน)

---

## 3. Redundancy ทุกชั้น

| ชั้น | Redundancy | กลไก (บทที่เกี่ยวข้อง) |
|---|---|---|
| **Power** | dual PSU ต่อ **คนละ PDU/วงจร/UPS**, generator | — |
| **Link** | หลายลิงก์ (LAG), คนละ line card/module | LACP (L37) |
| **Device** | อุปกรณ์คู่ | stacking, VSS/StackWise Virtual, MLAG/vPC, EVPN-MH (L37/74) |
| **Gateway** | default gateway คู่ | HSRP/VRRP/GLBP, anycast gateway (L50/74) |
| **Path** | หลายเส้นทาง | OSPF/BGP ECMP, fast convergence (L45/48/49) |
| **Firewall** | HA pair/cluster | active/passive + session sync (L62) |
| **WAN/ISP** | 2 ISP คนละเจ้า/คนละสื่อ | BGP multihoming, SD-WAN (L49/60) |
| **Service** | DNS/DHCP/RADIUS/NTP หลายตัว | DHCP failover, หลาย DNS server, RADIUS server group (L15/16/56) |
| **Site** | DC สองแห่ง/DR | GSLB, DCI, cloud (L71/79) |
| **People/Process** | คนรู้งานมากกว่า 1 คน, runbook, on-call | (L95) |

**ใส่ redundancy ตามความสำคัญ** — access switch ของเครื่องพนักงานไม่จำเป็นต้องคู่เสมอ (ผลกระทบจำกัด) แต่ core/WAN/firewall/DC ต้องคู่

---

## 4. Failure Domain, Blast Radius, Shared Fate

### Failure Domain
พื้นที่ที่ได้รับผลกระทบเมื่อส่วนประกอบหนึ่งล้มเหลว — **ออกแบบให้เล็ก**
- L2 domain ขนาดใหญ่ → broadcast storm/loop ลามทั้งองค์กร → ใช้ L3 ที่ distribution/access
- Stack ของ switch 8 ตัว → firmware bug ทำให้ stack ทั้งชุดล่ม → แบ่ง stack ย่อย
- Controller/management plane เดียวคุมทุก site → ระวัง config ผิดครั้งเดียวกระทบทุกที่ (ใช้ canary — Level 84)

### Blast Radius
"ถ้า X ผิดพลาด กระทบกว้างแค่ไหน" — ใช้กับการเปลี่ยนแปลงด้วย: change ทีละ site, ทีละ AZ

### Shared Fate ⭐ (สิ่งที่ "ดูเหมือนแยก" แต่เสียพร้อมกัน)
| ดูเหมือน | ความจริง |
|---|---|
| ISP สองเจ้า | **ใช้ไฟเบอร์ในท่อเดียวกัน/เสาเดียวกัน/backbone เดียวกัน** — รถแบ็คโฮขุดครั้งเดียวขาดทั้งคู่ |
| PSU สองตัว | ต่อ PDU เดียวกัน / UPS เดียวกัน |
| Firewall คู่ | firmware version เดียวกัน → bug เดียวกัน, config ผิดถูก sync ไปทั้งคู่ |
| DC สองแห่ง | อยู่ในพื้นที่น้ำท่วมเดียวกัน / grid ไฟฟ้าเดียวกัน |
| DNS สองตัว | เป็น VM บน host/storage เดียวกัน |
| Cloud สอง AZ | พึ่งบริการ control plane ระดับ region เดียวกัน |
| Link สองเส้นใน port-channel | อยู่บน line card เดียวกัน |
**ตรวจสอบ:** ขอ **เส้นทางสาย (route diversity)** จาก ISP เป็นลายลักษณ์อักษร, เข้าห้องอาคารคนละด้าน, ตรวจ mapping PSU/PDU, กระจาย VM บนคนละ host (anti-affinity), หลีกเลี่ยงการ upgrade ทั้งคู่พร้อมกัน

---

## 5. Fast Convergence — failover ให้เร็ว

| กลไก | หน้าที่ |
|---|---|
| **BFD** | ตรวจลิงก์/neighbor เสียระดับ ~50–300 ms (แทน hello/dead หลายวินาที) — ผูกกับ OSPF/BGP/static (L45/48) |
| Fast hello/timers | ลด timer ของ protocol (ใช้ BFD ดีกว่า) |
| **LFA / TI-LFA** | คำนวณเส้นทางสำรองไว้ล่วงหน้า สลับได้ใน <50 ms (L97) |
| **NSF / Graceful Restart** | control plane รีสตาร์ท (เช่น supervisor สลับ) แต่ data plane ยังส่งต่อ — neighbor ช่วยไม่ลบ route |
| **SSO** (Stateful Switchover) | supervisor/route processor คู่ sync สถานะ → สลับโดยไม่หลุด |
| **ISSU** (In-Service Software Upgrade) | อัปเกรด software โดย traffic ไม่หยุด (บนแพลตฟอร์มที่รองรับ) |
| PortFast / edge port, RSTP | STP converge เร็ว (L36) |
| HSRP/VRRP timers + preempt delay | gateway สลับเร็ว และไม่ preempt ก่อน routing พร้อม (L50) |
| BGP PIC (Prefix Independent Convergence) | สลับ next-hop สำรองสำหรับหลายแสน prefix ทีเดียว |
⚠️ timer ที่เร็วเกินไปอาจทำให้ **flap** บ่อยเมื่อเครือข่ายไม่เสถียร → ใช้ dampening/hold-down อย่างเหมาะสม

---

## 6. RPO และ RTO

```
          ◄──── RPO ────►          ◄────── RTO ──────►
 ────[backup ล่าสุด]────────[เกิดภัย]────────────────────[ระบบกลับมา]────► เวลา
     ข้อมูลช่วงนี้หายได้สูงสุด          ใช้เวลากู้คืนได้สูงสุด
```
| | ความหมาย | ตัวอย่าง |
|---|---|---|
| **RPO** (Recovery Point Objective) | ข้อมูลหายได้มากสุดเท่าไร (ย้อนเวลา) | 15 นาที → ต้อง replicate อย่างน้อยทุก 15 นาที |
| **RTO** (Recovery Time Objective) | ระบบต้องกลับมาภายในเท่าไร | 2 ชั่วโมง |
- กำหนดโดย **ธุรกิจ** (ผ่าน **BIA — Business Impact Analysis**) ไม่ใช่ทีม IT เดาเอง
- RPO/RTO ยิ่งต่ำยิ่งแพง → จัดระดับแอป (tier 1: RPO 0/RTO 15 นาที, tier 3: RPO 24 ชม./RTO 3 วัน)
- **ผลต่อ network:** bandwidth สำหรับ replication (RPO ต่ำ = ต้องส่งข้อมูลต่อเนื่อง), latency (synchronous replication ต้องการ RTT ต่ำมาก — มักจำกัดระยะ < ~100 km), DCI, การย้าย IP/DNS ตอน failover

---

## 7. DR Site

| ประเภท | สถานะ | RTO | ค่าใช้จ่าย |
|---|---|---|---|
| **Hot site** | ระบบพร้อมทำงาน ข้อมูล replicate ต่อเนื่อง | นาที–ชั่วโมง | สูง |
| **Warm site** | มีอุปกรณ์/โครงสร้าง แต่ต้องเปิด/restore บางส่วน | ชั่วโมง–วัน | กลาง |
| **Cold site** | มีพื้นที่/ไฟ/เครือข่ายพื้นฐาน ต้องติดตั้งและ restore | วัน–สัปดาห์ | ต่ำ |
| **Cloud DR (DRaaS)** | replicate ไป cloud เปิดเมื่อเกิดเหตุ (pilot light / warm standby) | ชั่วโมง | จ่ายตามใช้ |

### ประเด็น network ของ DR
- **IP addressing:** ใช้ IP เดิมที่ DR (ต้องย้าย route/ขยาย L2 — เสี่ยง) หรือ **IP ใหม่ + เปลี่ยน DNS** (ง่ายกว่า ต้องตั้ง TTL ต่ำ) หรือ GSLB (L71)
- **การเชื่อมต่อผู้ใช้/สาขา:** SD-WAN/VPN ต้องมี tunnel ไป DR พร้อมใช้ (routing prefer HQ ปกติ, DR เมื่อ HQ ล่ม)
- **Internet/public IP:** BGP ประกาศ prefix จาก DR (provider-independent IP + AS ของตัวเอง ทำให้ย้ายได้)
- **Firewall/NAT/VPN config ที่ DR** ต้อง **sync** กับ HQ (drift เป็นสาเหตุอันดับต้นที่ DR ใช้ไม่ได้)
- **Dependencies:** AD/DNS/DHCP/RADIUS/certificate/license server ต้องอยู่ที่ DR ด้วย
- **Runbook การ failover/failback** ทีละขั้น ใครทำอะไร ใครตัดสินใจประกาศภัยพิบัติ

---

## 8. Active-Active vs Active-Standby

| | **Active-Standby** | **Active-Active** |
|---|---|---|
| การทำงาน | ตัวหลักรับโหลด ตัวสำรองรอ | ทั้งคู่รับโหลด |
| ใช้ทรัพยากร | 50% | เต็ม |
| ความซับซ้อน | ต่ำ คาดเดาง่าย | สูงกว่า (state sync, asymmetric, split-brain) |
| ⚠️ กับดัก | ตัวสำรองไม่เคยถูกใช้จริง → เสียโดยไม่รู้ (ต้องทดสอบ) | **แต่ละตัวต้องรับโหลดรวมได้เมื่ออีกตัวล่ม** — ถ้าใช้ตัวละ 70% ล่มหนึ่งตัว = 140% → ล่มทั้งระบบ |
**กฎ:** ใน active-active แบบ 2 ตัว **ใช้รวมไม่เกิน ~50% ของความจุรวม** (หรือ N+1 สำหรับ N ตัว)

### Split-brain
สองฝั่งคิดว่าตัวเองเป็น active (ลิงก์ heartbeat ขาด) → IP/MAC ซ้ำ, ข้อมูลไม่สอดคล้อง
- ป้องกัน: heartbeat หลายเส้น (คนละ path), quorum/witness (ตัวที่สาม), fencing

---

## 9. FMEA — Failure Mode and Effects Analysis

ไล่ทีละส่วนประกอบ: "ถ้าสิ่งนี้เสีย จะเกิดอะไร ตรวจพบอย่างไร กู้อย่างไร"
| ส่วนประกอบ | Failure mode | ผลกระทบ | ตรวจพบ | ระยะเวลา | Mitigation | Severity |
|---|---|---|---|---|---|---|
| ISP1 | ขาด | traffic ย้ายไป ISP2 (ขาดหายไม่กี่วินาที) | BGP down alert | — | ISP2 + BFD | ต่ำ |
| Core-01 | ล่ม | HSRP ย้าย, ลิงก์ครึ่งหนึ่งหาย | SNMP/ping | 1–3 วินาที | Core-02, ECMP | ต่ำ |
| Firewall HA | config ผิด sync ทั้งคู่ | **ทุกอย่างหยุด** | synthetic | จน rollback | change process, backup, commit confirm | **สูง** |
| DNS ภายใน | ทั้งคู่บน storage เดียว | login/แอปล้ม | synthetic DNS | ชั่วโมง | แยก host/storage, DNS ที่ DR | **สูง** |
| ห้อง DC | ไฟดับเกิน UPS | ทั้ง HQ | BMS/SNMP UPS | ชั่วโมง | generator + ทดสอบรายเดือน, DR | สูง |
→ ลำดับความสำคัญของการแก้ด้วย Severity × Likelihood (Risk Priority)

---

## 10. ทดสอบ Failover — Game Day และ Chaos Engineering

> **"Redundancy ที่ไม่เคยทดสอบ คือ redundancy ที่ไม่มีอยู่จริง"**

ทำไม failover มักล้มเหลวตอนเกิดเหตุจริง: config drift (ตัวสำรองไม่ได้อัปเดต), license หมดอายุบนตัวสำรอง, route ขากลับไม่มี, ไม่มีใครจำขั้นตอนได้, timer ตั้งผิด, firewall สำรองไม่มี rule ใหม่

### Game Day
- **วางแผน:** scenario (ถอดสาย ISP1, ปิด core-01, reboot firewall active, ปิด DNS ตัวหลัก), ผลที่คาดหวัง (เช่น "หยุด < 3 วินาที"), เกณฑ์หยุดทดสอบ, ผู้สังเกตการณ์, วิธี rollback
- **แจ้ง stakeholder + ทำใน maintenance window** (ครั้งแรก) → เมื่อมั่นใจแล้วทำในเวลาทำงานแบบควบคุม
- **วัดผลจริง:** ping ต่อเนื่อง, synthetic HTTP, เวลา convergence จาก log
- **บันทึกและแก้ไข** สิ่งที่ไม่เป็นไปตามคาด → ทดสอบซ้ำ
- **ทำเป็นประจำ** (ทุกไตรมาส/ทุกครึ่งปี) — DR drill ปีละครั้งเป็นอย่างน้อย (และตามข้อกำหนดของหน่วยงานกำกับ)

### Chaos Engineering
ฉีดความล้มเหลวแบบสุ่มอย่างควบคุม (เริ่มใน lab/staging — containerlab ปิด link/node สุ่มแล้ววัดผลกระทบต่อแอป) เพื่อหาจุดอ่อนก่อนเกิดเหตุจริง

---

## 11. Checklist HA ที่มักถูกลืม

- [ ] PSU คู่ต่อ **คนละ** PDU/UPS
- [ ] ISP สองเจ้ามี **route diversity** ยืนยันเป็นเอกสาร
- [ ] Firmware ของคู่ HA ไม่ upgrade พร้อมกัน (แต่ต้อง version ที่ compatible)
- [ ] License/subscription ของตัวสำรองยังไม่หมดอายุ
- [ ] Config ของตัวสำรอง/DR sync และตรวจ drift
- [ ] Monitoring แจ้งเตือนเมื่อ **ตัวสำรองเสีย** (ไม่ใช่แค่ตัวหลัก) และเมื่อ HA state เปลี่ยน
- [ ] อะไหล่ (spare) ของอุปกรณ์สำคัญ หรือ support contract ระดับ 4 ชั่วโมง
- [ ] OOB access (console server + 4G) เข้าถึงได้เมื่อ network หลักล่ม
- [ ] เอกสาร/runbook อยู่ในที่ที่เข้าถึงได้แม้ระบบล่ม (ไม่ใช่เฉพาะใน wiki บน server ที่ล่ม)

---

## 12. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| มีอุปกรณ์คู่แล้ว = HA | ต้องตรวจ shared fate และทดสอบ failover จริง |
| ISP สองเจ้า = redundancy เต็มที่ | อาจใช้ท่อ/เส้นทางเดียวกัน — ต้องยืนยัน diversity |
| Active-active ใช้ได้ 100% ทั้งสองตัว | ต้องรับโหลดรวมได้เมื่อตัวหนึ่งล่ม (≤50%) |
| RPO/RTO ให้ IT กำหนด | ธุรกิจกำหนดผ่าน BIA |
| อุปกรณ์ในสายยิ่งมากยิ่งปลอดภัย | อนุกรมยิ่งยาว availability ยิ่งลด |

---

## 13. Cheat Sheet

```
A = MTBF/(MTBF+MTTR) · MTTR สำคัญ (อะไหล่, support, runbook)
อนุกรม: A1×A2×... (ลดลง) · ขนาน: 1-(1-A1)(1-A2) (เพิ่มขึ้น, ถ้าอิสระ)
99.9% ≈ 8.76 ชม./ปี · 99.99% ≈ 52.6 นาที/ปี · 99.999% ≈ 5.26 นาที/ปี
Redundancy: power · link · device · gateway · path · firewall · ISP · services · site · people
Failure domain เล็ก · blast radius · shared fate (ท่อ ISP, PDU, firmware, storage, region)
Fast convergence: BFD · LFA/TI-LFA · NSF/GR · SSO · ISSU · BGP PIC · ระวัง flap
RPO (ข้อมูลหาย) · RTO (เวลากู้) · BIA · tier ของแอป
DR: hot/warm/cold/cloud · IP/DNS/GSLB · config sync · dependencies · runbook
Active-active ≤50% ต่อตัว · split-brain → quorum/witness
FMEA · Game day · Chaos · "ไม่ทดสอบ = ไม่มี"
```

---

## 14. แบบทดสอบ 10 ข้อ

1. Availability คำนวณจาก MTBF และ MTTR อย่างไร และทำไม MTTR สำคัญ
2. อุปกรณ์ 3 ตัว availability 99.9% ต่ออนุกรม รวมเท่าไร
3. Firewall 2 ตัว availability 99% ทำงานขนาน รวมเท่าไร
4. Shared fate คืออะไร ยกตัวอย่าง 3 อย่าง
5. RPO กับ RTO ต่างกันอย่างไร ใครควรกำหนด
6. Hot, warm, cold site ต่างกันอย่างไร
7. ทำไม active-active สองตัวไม่ควรใช้เกิน 50% ต่อตัว
8. Split-brain คืออะไร ป้องกันอย่างไร
9. BFD ช่วย HA อย่างไร
10. ทำไมต้องทำ game day และควรวางแผนอย่างไร

<details><summary><b>เฉลย</b></summary>

1. A = MTBF/(MTBF+MTTR) — MTTR ที่ยาว (รออะไหล่/ไม่มี runbook) ลด availability ได้มาก แม้อุปกรณ์จะเสียไม่บ่อย
2. 0.999³ ≈ 99.7%
3. 1 − (0.01 × 0.01) = 99.99%
4. สิ่งที่ดูแยกกันแต่เสียพร้อมกัน เช่น ISP สองเจ้าใช้ท่อไฟเบอร์เดียวกัน, PSU คู่ต่อ PDU เดียว, firewall คู่ firmware/bug เดียวกัน, DNS สองตัวบน storage เดียว, DC สองแห่งในพื้นที่น้ำท่วมเดียวกัน
5. RPO = ปริมาณข้อมูลที่ยอมให้หาย (ย้อนเวลา); RTO = เวลาที่ต้องกู้ระบบให้กลับมา — ธุรกิจกำหนดผ่าน BIA
6. Hot พร้อมทำงานและ replicate ต่อเนื่อง (RTO นาที–ชั่วโมง, แพง); warm มีโครงสร้างแต่ต้องเปิด/restore บางส่วน; cold มีแค่พื้นที่/พื้นฐาน ต้องติดตั้งและ restore (RTO วัน–สัปดาห์, ถูก)
7. เมื่อตัวหนึ่งล่ม อีกตัวต้องรับโหลดทั้งหมด ถ้าแต่ละตัวใช้เกิน 50% ตัวที่เหลือจะ overload และล่มตาม
8. ทั้งสองฝั่งคิดว่าตนเป็น active เพราะ heartbeat ขาด — ใช้ heartbeat หลายเส้นทาง, quorum/witness, fencing
9. ตรวจการเสียของลิงก์/neighbor ในระดับมิลลิวินาที ทำให้ routing protocol สลับเส้นทางเร็ว
10. Redundancy ที่ไม่ทดสอบมักใช้ไม่ได้จริง — วางแผน scenario, ผลที่คาดหวัง, เกณฑ์หยุด, rollback, แจ้ง stakeholder, ทำใน window, วัดผลจริง บันทึกและแก้ไข ทำซ้ำเป็นประจำ
</details>

---

➡️ ต่อไป: **Level 94 — Capacity Planning, Cost & Vendor Management**
