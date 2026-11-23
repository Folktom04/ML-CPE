# บทเรียน Level 95 — Change Management, ITIL & Documentation (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ ITIL 4 practices ที่ network engineer ใช้ทุกวัน (Incident, Problem, Change, Service Request, Configuration/CMDB) · แยกประเภท change (Standard/Normal/Emergency) · เขียน change plan ที่ครบ (โดยเฉพาะ rollback + verification) · ใช้กลไกป้องกันตัวเอง (`reload in`, `commit confirmed`, `configure replace`) · ทำ maintenance window และสื่อสาร · เขียนเอกสารที่ทีมใช้ได้จริง (diagram, runbook, SOP, as-built) · วัฒนธรรม blameless postmortem

---

## 1. ทำไมต้องมีกระบวนการ

สถิติจากหลายองค์กรตรงกัน: **สาเหตุอันดับต้นของ outage คือ "การเปลี่ยนแปลง"** (config ผิด, upgrade มีปัญหา, ทำผิดลำดับ) ไม่ใช่ฮาร์ดแวร์เสีย
กระบวนการที่ดี **ไม่ได้มีไว้ทำให้ช้า** แต่ทำให้:
- คนอื่นช่วยตรวจ (สองตาดีกว่าตาเดียว)
- ทุกคนรู้ว่ากำลังจะเกิดอะไร (helpdesk/ผู้ใช้/ทีมแอป)
- มีทางถอยเมื่อผิดพลาด
- ย้อนดูได้ว่าใครทำอะไรเมื่อไร (audit, troubleshooting — "มีอะไรเปลี่ยน?" Level 91)

---

## 2. ITIL 4 — Practices ที่เกี่ยวกับงาน Network

**ITIL** = กรอบแนวปฏิบัติการบริหารบริการ IT ที่ใช้แพร่หลาย (ITIL 4 ใช้คำว่า "practices")
| Practice | ความหมาย | ตัวอย่างงาน network |
|---|---|---|
| **Incident Management** | กู้บริการให้กลับมาเร็วที่สุด | "สาขาเชียงใหม่ใช้งานไม่ได้" → กู้ก่อน (เปลี่ยนไป ISP2) |
| **Problem Management** | หา **root cause** และป้องกันไม่ให้เกิดซ้ำ | ทำไม ISP1 ของเชียงใหม่ล่มเดือนละ 3 ครั้ง → แก้ที่สาเหตุ |
| **Change Enablement** (Change Management) | ควบคุมการเปลี่ยนแปลงให้ความเสี่ยงต่ำ | เพิ่ม VLAN, upgrade firmware, เปลี่ยน firewall rule |
| **Service Request** | คำขอมาตรฐานที่ไม่ใช่ปัญหา | ขอเปิดพอร์ต, ขอ VPN account, ขอย้ายโต๊ะ |
| **Service Configuration Management (CMDB)** | ข้อมูลของ configuration item (CI) และความสัมพันธ์ | อุปกรณ์/วงจร/บริการ (NetBox เป็น SoT — Level 89) |
| **Monitoring & Event Management** | ตรวจจับเหตุการณ์ | Level 86 |
| **Knowledge Management** | เก็บความรู้ให้ใช้ซ้ำได้ | KB, runbook |
| **Service Level Management** | ตกลงและติดตาม SLA/SLO | Level 86/94 |

### Incident vs Problem
```
 Incident: "อินเทอร์เน็ต HQ ล่ม 10:05" → workaround: สลับไป ISP2 → บริการกลับ 10:12 → ปิด incident
 Problem : "ทำไม BGP กับ ISP1 flap 5 ครั้งในเดือนนี้" → พบ SFP เสื่อม (Rx power ต่ำ) → เปลี่ยน → ปิด problem
           ระหว่างยังไม่รู้สาเหตุ = "known error" + workaround ที่บันทึกไว้
```
**Major incident:** ผลกระทบสูง → ตั้ง incident commander, ช่องทางสื่อสารเฉพาะ (war room/bridge), อัปเดตสถานะเป็นระยะ (ทุก 30 นาที), แยกคนแก้กับคนสื่อสาร

---

## 3. ประเภทของ Change

| ประเภท | ลักษณะ | การอนุมัติ | ตัวอย่าง |
|---|---|---|---|
| **Standard** | ความเสี่ยงต่ำ ทำบ่อย ขั้นตอนตายตัว ผ่านการพิสูจน์แล้ว | **อนุมัติล่วงหน้า** (pre-approved) — ทำตาม template | เปลี่ยน VLAN พอร์ตผู้ใช้, เพิ่ม description, เพิ่ม user VPN |
| **Normal** | ต้องประเมินความเสี่ยงเป็นรายครั้ง | **CAB** (Change Advisory Board) หรือผู้มีอำนาจตามระดับความเสี่ยง | เพิ่ม route policy, upgrade core switch, เปลี่ยน firewall rule ที่กระทบหลายระบบ |
| **Emergency** | ต้องทำทันทีเพื่อแก้ incident/ช่องโหว่ร้ายแรง | ECAB (กลุ่มเล็ก/ผู้มีอำนาจ) อนุมัติเร็ว + **บันทึกย้อนหลัง** | patch ช่องโหว่ที่ถูกโจมตีอยู่, แก้ config ที่ทำให้ระบบล่ม |
💡 **เป้าหมาย:** ย้าย change ที่ทำบ่อยให้เป็น **Standard** (ด้วย template + automation + pre/post check — Level 84) → CAB โฟกัสเฉพาะ change ที่เสี่ยงจริง

### ระดับความเสี่ยง (ตัวอย่างเกณฑ์)
| ปัจจัย | ต่ำ | สูง |
|---|---|---|
| ผลกระทบถ้าผิด | พอร์ตเดียว | ทั้ง site/บริการหลัก |
| ความซับซ้อน | ขั้นตอนเดียว | หลายอุปกรณ์/หลายทีม |
| เคยทำมาก่อน | บ่อย | ครั้งแรก |
| ทดสอบได้ใน lab | ได้ | ไม่ได้ |
| Rollback | ง่าย/เร็ว | ยาก/ช้า/ไม่ได้ |

---

## 4. Change Plan ที่ดี — องค์ประกอบ

```
 1. Summary          : ทำอะไร ทำไม (เหตุผลทางธุรกิจ/ticket ที่เกี่ยวข้อง)
 2. Scope            : อุปกรณ์/site/บริการที่เกี่ยวข้อง
 3. Risk & Impact    : ระดับความเสี่ยง, ผลกระทบระหว่างทำ (downtime เท่าไร?), ผลกระทบถ้าผิดพลาด
 4. Schedule         : maintenance window, ระยะเวลาโดยประมาณ, จุดตัดสินใจ rollback (go/no-go time)
 5. Prerequisites    : backup config, ไฟล์ firmware + checksum, console/OOB พร้อม, ผู้เกี่ยวข้อง standby
 6. Pre-checks       : สถานะก่อนทำ (interfaces, neighbors, routes, ping ไปจุดสำคัญ) — เก็บไว้เทียบ
 7. Implementation   : ขั้นตอนทีละบรรทัด + คำสั่งจริง (copy ได้) + ผลที่คาดหวังแต่ละขั้น
 8. Verification     : ⭐ จะพิสูจน์อย่างไรว่าสำเร็จ (post-check เทียบ pre-check, ผู้ใช้/ทีมแอปทดสอบ)
 9. Rollback plan    : ⭐ ทำอย่างไรเมื่อผิดพลาด, ใช้เวลาเท่าไร, เมื่อไรต้องตัดสินใจ rollback
 10. Communication   : แจ้งใครก่อน/ระหว่าง/หลัง (helpdesk, ผู้ใช้, ทีมแอป, ผู้บริหาร), ช่องทาง
 11. Contacts        : ผู้ทำ, ผู้ตรวจ, vendor TAC (เลข contract), ผู้ตัดสินใจ
```
**ส่วนที่มักถูกลืม/ทำแบบขอไปที:** **rollback plan และ verification** → ถ้าเขียนไม่ได้ว่าจะ rollback อย่างไร = ยังไม่พร้อมทำ change

### ตัวอย่าง (ย่อ): Upgrade IOS-XE บน access switch stack
```
 Pre:   show version · show switch · show interfaces status | count connected
        show cdp/lldp neighbors · show spanning-tree summary · copy running-config tftp/scp
        verify /md5 flash:cat9k_iosxe.17.12.04.SPA.bin  → ตรงกับ checksum จากผู้ผลิต
 Impl:  install add file flash:cat9k_iosxe.17.12.04.SPA.bin activate commit
        (switch reload ~10–15 นาที — ผู้ใช้ชั้น 3 หลุด, AP/โทรศัพท์ดับระหว่างนั้น)
 Verify: show version (17.12.04) · จำนวนพอร์ต connected เท่าเดิม ±2 · neighbors ครบ · AP join ครบ
        · ผู้ใช้ตัวแทนทดสอบ login/โทรศัพท์
 Rollback (ถ้า 30 นาทีหลัง reload ยังไม่ผ่าน): install rollback to committed (หรือ boot image เดิม)
        · เวลาที่ใช้ ~15 นาที
 Go/No-go: 01:30 ถ้ายังไม่เริ่ม upgrade ให้เลื่อน (เผื่อเวลา rollback ก่อน 04:00)
```

---

## 5. กลไกป้องกันตัวเองระหว่างทำ Change

| แพลตฟอร์ม | คำสั่ง | ทำอะไร |
|---|---|---|
| Cisco IOS | `reload in 10` (ก่อนแก้) → แก้ → ถ้ายังเข้าได้ `reload cancel` | ถ้าแก้ผิดจนตัวเองหลุด อุปกรณ์จะ reload กลับไปใช้ startup-config เดิม (อย่า `write memory` ก่อนยืนยัน) |
| Cisco IOS-XE/XR, NX-OS | `configure replace flash:backup.cfg` / **`configure terminal revert timer 10`** (IOS-XE: `archive` + `configure confirm`) | rollback config ทั้งก้อนแบบไม่ต้อง reload |
| **Junos** | `commit confirmed 5` → ตรวจ → `commit` | ถ้าไม่ยืนยันภายใน 5 นาที **rollback อัตโนมัติ** ⭐ · `rollback 1` · `show | compare` |
| Arista EOS | `configure session` + `commit timer 00:05:00` | คล้าย commit confirmed |
| Palo Alto | candidate config + `commit` · revert to running/saved config | |
| FortiGate | `config system global` → `set cfg-save revert` + `set cfg-revert-timeout` | revert ถ้าไม่ยืนยัน |
| NETCONF | confirmed commit (Level 83) | |
| Linux | `at now + 5 minutes <<< "nft -f /etc/nftables.conf.bak"` | ตั้ง job คืนค่าไว้ก่อนแก้ firewall |
**หลักทอง:** แก้อุปกรณ์ที่ remote เสมอ **ตั้ง safety net ก่อน** + มี **OOB/console** สำรอง (Level 93)

---

## 6. Maintenance Window และการสื่อสาร

- **Window:** ช่วงที่ผลกระทบต่ำ (กลางคืน/วันหยุด) — แต่ระวังตรงกับ batch job/backup/งานของทีมอื่น (ตรวจ **change calendar**/freeze period เช่น ปิดงบ สิ้นปี เทศกาลขายสินค้า)
- **Change freeze:** ช่วงห้ามเปลี่ยน (ยกเว้น emergency)
- **ประกาศล่วงหน้า:** อะไรจะหยุด เมื่อไร นานเท่าไร ติดต่อใคร
- **ระหว่างทำ:** อัปเดตใน channel ของ change (เริ่ม/เสร็จแต่ละขั้น/ปัญหา)
- **หลังทำ:** แจ้งผล (สำเร็จ/rollback), ปิด change ticket พร้อมหลักฐาน (post-check), อัปเดตเอกสาร/NetBox/diagram
- **Collision check:** ไม่ทำ change สองรายการที่กระทบกันใน window เดียวกัน (ถ้าเกิดปัญหาจะแยกสาเหตุไม่ออก)

---

## 7. เอกสาร (Documentation) ที่ทีมต้องมี

| เอกสาร | เนื้อหา | ใครใช้ |
|---|---|---|
| **Network diagrams** | L1 (physical: สาย/พอร์ต/rack), **L2** (VLAN/trunk/STP), **L3** (subnet/routing/area/AS), WAN/Internet/cloud, security zones | ทุกคน — ตอน troubleshoot |
| **IP/VLAN plan** | ใน IPAM (NetBox) ไม่ใช่ Excel | |
| **Standards** | naming, config baseline, port profile, รุ่นอุปกรณ์มาตรฐาน | วิศวกร |
| **Runbook** | ขั้นตอนตอบสนองเหตุ/งานเฉพาะทีละขั้น (ทำตามได้ตอนตี 3) | NOC/on-call |
| **SOP** (Standard Operating Procedure) | งานประจำมาตรฐาน (เพิ่ม user VPN, เปลี่ยน cert) | helpdesk/ทีม |
| **As-built** | สภาพที่ติดตั้ง **จริง** หลังโปรเจค (ต่างจาก design เพราะเปลี่ยนหน้างาน) + config + ผลทดสอบ | ทีมดูแลต่อ |
| **Contact/escalation list** | ISP (circuit ID, เบอร์ NOC), vendor (contract), ทีมภายใน | ทุกคน |
| **Knowledge base** | ปัญหาที่เคยเจอ + วิธีแก้ | ทุกคน |
| **Post-mortem** | บทเรียนจาก incident | ทุกคน |

### Runbook ที่ดี
```
 RB-012: ISP1 (HQ) ล่ม
 อาการ/Alert: BgpPeerDown ISP1, synthetic internet HQ ล้มเหลว
 ผลกระทบที่คาด: traffic ย้ายไป ISP2 อัตโนมัติภายใน 3 วินาที (ไม่ควรมีผลต่อผู้ใช้)
 1. ตรวจว่า failover ทำงาน: show ip bgp summary (ISP2 Established), show ip route 0.0.0.0
 2. ตรวจ utilization ISP2 (Grafana: WAN-HQ) — ถ้า > 85% แจ้งทีม เปิด QoS profile "degraded"
 3. ตรวจฝั่งเรา: show interfaces Gi0/0/0 (up? errors? optic Rx power)
 4. เปิด ticket ISP1: โทร 02-xxx-xxxx (NOC 24 ชม.) circuit ID: BKK-DIA-12345, contract #...
 5. แจ้ง #it-incident: "ISP1 ล่ม ใช้ ISP2 อยู่ ไม่กระทบผู้ใช้ ETA จาก ISP: ..."
 6. เมื่อ ISP1 กลับมา: ตรวจ BGP Established + รับ prefix ปกติ, traffic กลับมาตาม policy
 Escalate: ถ้า ISP2 ล่มด้วย → RB-013 (Internet ล่มทั้งหมด) + โทร on-call lead
```
### หลักการเขียนเอกสาร
- **เขียนให้คนที่ไม่เคยเห็นระบบอ่านแล้วทำได้** (คนใหม่, ตัวเองในอีก 1 ปี)
- **อยู่ใกล้งาน:** docs-as-code (Markdown ใน Git — MkDocs/Docusaurus), wiki (Confluence/BookStack), diagram as code (draw.io ใน Git, Mermaid, netbox-topology-views)
- **มีเจ้าของและวันที่ทบทวน** — เอกสารเก่าผิด อันตรายกว่าไม่มี
- **อัปเดตเป็นส่วนหนึ่งของ change** (definition of done) ไม่ใช่ "ไว้ทีหลัง"
- เก็บสำเนาที่เข้าถึงได้เมื่อระบบล่ม (offline/printed สำหรับ runbook สำคัญ)

---

## 8. Blameless Postmortem Culture

**Blameless** = มุ่งที่ **ระบบและกระบวนการ** ไม่ใช่หาคนผิดมาลงโทษ
- ถ้าคนกลัวถูกลงโทษ → ปิดบังข้อมูล → องค์กรไม่เรียนรู้ → เกิดซ้ำ
- คำถามที่ถูก: "**อะไรในระบบที่ทำให้ความผิดพลาดนี้เกิดได้ง่าย?**" (ไม่มี review? คำสั่งอันตรายไม่มีการยืนยัน? เอกสารผิด? เหนื่อยเกินไปตอนตี 4?)
- ผลลัพธ์: action items ที่ **แก้ที่ระบบ** (automation, guardrail, checklist, training) มีเจ้าของและกำหนดเสร็จ
- เผยแพร่ post-mortem ภายในองค์กร — ให้ทีมอื่นเรียนรู้ด้วย
(โครงสร้าง post-mortem ดู Level 91)

---

## 9. เครื่องมือ

| ประเภท | ตัวอย่าง |
|---|---|
| ITSM (ticket/change/CMDB) | ServiceNow, Jira Service Management, ManageEngine ServiceDesk Plus, GLPI, iTop |
| Change ↔ automation | Git PR ลิงก์กับ change ticket, pipeline ตรวจว่ามี change ที่อนุมัติก่อน deploy (Level 84) |
| Documentation | Confluence, BookStack, MkDocs, NetBox (Level 89), draw.io, Visio |
| Status page | Statuspage, Uptime Kuma (สื่อสารกับผู้ใช้ระหว่าง incident) |

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Change management ทำให้ช้าและเป็นภาระ | ทำ standard change + automation ให้เร็ว โฟกัส CAB กับงานเสี่ยงจริง |
| แก้เล็กน้อยไม่ต้องผ่าน change | change "เล็ก" ทำระบบล่มได้บ่อย — อย่างน้อยต้องบันทึกและเป็น standard change |
| Rollback plan = "ทำกลับ" | ต้องระบุขั้นตอน เวลา และจุดตัดสินใจที่ชัดเจน |
| Incident = Problem | incident กู้บริการ, problem หาสาเหตุราก |
| เอกสารทำตอนจบโปรเจค | อัปเดตเป็นส่วนหนึ่งของทุก change |

---

## 11. Cheat Sheet

```
ITIL 4: Incident (กู้เร็ว) · Problem (root cause, known error) · Change Enablement · Service Request · CMDB
Change: Standard (pre-approved) · Normal (CAB ตามความเสี่ยง) · Emergency (ECAB + บันทึกย้อนหลัง)
Plan: summary · scope · risk/impact · schedule (go/no-go) · prereq (backup, checksum, OOB) · pre-check
      · steps · VERIFICATION · ROLLBACK · communication · contacts
Safety net: reload in 10 / configure replace / revert timer · Junos commit confirmed · EOS commit timer
Window · change calendar/freeze · collision check · แจ้งก่อน/ระหว่าง/หลัง
Docs: diagrams L1/L2/L3 · IPAM · standards · runbook · SOP · as-built · contacts · KB · postmortem
Docs-as-code · เจ้าของ+วันทบทวน · update = ส่วนหนึ่งของ change · สำเนา offline
Blameless: แก้ที่ระบบ ไม่ใช่โทษคน
```

---

## 12. แบบทดสอบ 10 ข้อ

1. Incident กับ Problem management ต่างกันอย่างไร
2. Standard, Normal, Emergency change ต่างกันอย่างไร
3. ทำไมควรเปลี่ยน change ที่ทำบ่อยให้เป็น standard change และทำอย่างไร
4. ส่วนใดของ change plan ที่สำคัญแต่มักถูกละเลย
5. `reload in 10` ทำงานอย่างไร และต้องระวังอะไร
6. Junos `commit confirmed` ช่วยอะไร
7. Go/no-go time คืออะไร
8. Runbook ที่ดีมีลักษณะอย่างไร
9. As-built document คืออะไร ต่างจาก design อย่างไร
10. Blameless postmortem คืออะไร ทำไมสำคัญ

<details><summary><b>เฉลย</b></summary>

1. Incident มุ่งกู้บริการให้กลับมาเร็วที่สุด (อาจใช้ workaround); problem มุ่งหา root cause และป้องกันไม่ให้เกิดซ้ำ
2. Standard = ความเสี่ยงต่ำ ทำบ่อย อนุมัติล่วงหน้า; Normal = ประเมินความเสี่ยงและอนุมัติรายครั้ง (CAB); Emergency = ต้องทำทันที อนุมัติเร็วและบันทึกย้อนหลัง
3. ลดภาระ CAB และทำงานได้เร็วโดยความเสี่ยงยังต่ำ — ใช้ template ขั้นตอนตายตัว, automation และ pre/post check ที่พิสูจน์แล้ว
4. Rollback plan และ verification steps
5. ตั้งเวลาให้อุปกรณ์ reload กลับไปใช้ startup-config ถ้าแก้ผิดจนเข้าไม่ได้ — ต้องไม่ write memory ก่อนยืนยัน และอย่าลืม `reload cancel` เมื่อสำเร็จ
6. ถ้าไม่ commit ยืนยันภายในเวลาที่กำหนด จะ rollback อัตโนมัติ ป้องกันการตัดการเชื่อมต่อตัวเอง
7. เวลาล่าสุดที่ต้องตัดสินใจว่าจะทำต่อหรือยกเลิก/rollback เพื่อให้เหลือเวลาพอ rollback ภายใน window
8. ขั้นตอนชัดเจนทีละข้อพร้อมคำสั่ง, อาการ/alert ที่ใช้, ผลที่คาดหวัง, ข้อมูลติดต่อ, เกณฑ์ escalate — คนที่ไม่เคยเห็นระบบทำตามได้ตอนตี 3
9. เอกสารสภาพที่ติดตั้งจริงหลังโปรเจค (config, พอร์ต, ผลทดสอบ) ซึ่งอาจต่างจาก design เพราะการเปลี่ยนหน้างาน
10. การวิเคราะห์เหตุการณ์ที่มุ่งแก้ระบบ/กระบวนการแทนการโทษคน ทำให้คนกล้าเล่าความจริง องค์กรเรียนรู้และป้องกันการเกิดซ้ำได้
</details>

---

➡️ ต่อไป: **Level 96 — Multicast**
