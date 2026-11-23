# Part 2 — Data Center & Infrastructure + Immutable Backup & DR (Level 21–43)

> ตามขอบเขตงาน ISC: **High-Density Server, Server Clustering & HA, SAN/NAS Storage Integration, Cooling & Power Management, Cabling & Physical Infrastructure Standards, ห้อง Data Center (Raised Floor, FM-200, PAC, Biometric) และ Immutable Backup, Multi-Site Replication, DR Drill, RTO/RPO Verification**
> แบรนด์: Dell, HPE, Lenovo (server) · Dell EMC PowerStore, HPE Alletra, Sangfor aStor, Infortrend (storage) · APC, Vertiv/Liebert, Syndome, Delta (UPS)

## Level ที่ใช้เนื้อหาเดิม (เรียนจาก SI-Track แล้วตอบ ISC Checkpoint)

| Level | หัวข้อ | เรียนจาก | ISC Checkpoint |
|---|---|---|---|
| 21 | DC fundamentals (Tier, power, cooling, rack) | [SI L21](../SI-Track/01-datacenter-a.md) | อธิบาย Tier III ให้ลูกค้าภาครัฐ และประเมินห้อง server เดิมได้ |
| 24 | Server hardware | [SI L22](../SI-Track/01-datacenter-a.md) | ตั้ง iDRAC (Dell) / iLO (HPE) / XCC (Lenovo) และอัปเดต firmware ตาม HCL ได้ทั้ง 3 ยี่ห้อ |
| 25 | Server OS & workload sizing | [SI L23](../SI-Track/01-datacenter-a.md) | Size server จากผล RVTools/Live Optics และเสนอ spec Dell/HPE/Lenovo เทียบกันได้ |
| 26 | Storage fundamentals | [SI L24](../SI-Track/01-datacenter-a.md) | คำนวณ RAID/IOPS ตาม workload HIS/ERP |
| 27 | Fibre Channel SAN | [SI L25](../SI-Track/01-datacenter-a.md) | ทำ zoning Fabric A/B และ multipath บน VMware/Windows |
| 28 | iSCSI, NVMe-oF, NFS/SMB | [SI L26](../SI-Track/01-datacenter-a.md) | ตั้ง iSCSI แยก VLAN + jumbo + MPIO สำหรับ PowerStore/Infortrend |
| 30 | VMware vSphere | [SI L28](../SI-Track/01-datacenter-a.md) | ติดตั้ง vCenter + cluster + vDS ตามมาตรฐานบริษัท (เตรียมสอบ VCP-DCV) |
| 31 | High-Availability Cluster | [SI L29](../SI-Track/01-datacenter-a.md) | ทดสอบ HA/DRS และ Windows Failover Cluster ต่อหน้าลูกค้า |
| 32 | Application & Database HA | [SI L30](../SI-Track/01-datacenter-a.md) | ออกแบบ HA ให้ HIS/ERP 3 tier |
| 33 | DC network & fabric (100G, spine-leaf, VXLAN) | [SI L33–L34](../SI-Track/02-datacenter-b.md) | ออกแบบ ToR คู่ + uplink 100G (ตามผลงาน PFO-DC-01) |
| 34 | DC security & segmentation | [SI L35](../SI-Track/02-datacenter-b.md) | แยก management network ของ iDRAC/vCenter/storage |
| 35 | DC monitoring & DCIM | [SI L36](../SI-Track/02-datacenter-b.md) | Monitor UPS/PAC/อุณหภูมิผ่าน SNMP เข้า NOC 24x7 |
| 36 | Pre-sales, assessment & sizing | [SI L37](../SI-Track/02-datacenter-b.md) | เขียน proposal + BOM ตาม TOR ภาครัฐ (spec ไม่ล็อกยี่ห้อ) |
| 37 | Implementation, testing & handover | [SI L38–L39](../SI-Track/02-datacenter-b.md) | ส่งมอบตาม ISO 9001 พร้อม UAT, as-built และเอกสารกำกับ |
| 39 | Backup & immutable repository | [SI L31](../SI-Track/02-datacenter-b.md) | ออกแบบ 3-2-1-1-0 พร้อม Object Lock/WORM |
| 40 | Disaster Recovery & multi-site replication | [SI L32](../SI-Track/02-datacenter-b.md) | ออกแบบ replication ข้ามสาขา/DR site + orchestration |
| 41 | Cloud backup & DRaaS | [SI L75](../SI-Track/06-cloud-hci-b.md) | เสนอ DR ไป cloud เป็นทางเลือกให้ลูกค้าที่ไม่มี DR site |
| 42 | Backup verification & DR drill | [SI L93](../SI-Track/08-support-b.md) | ทำ DR drill และออกรายงาน RTO/RPO compliance |

---

## Level 22 — Data Center Facilities: Power, Cooling, Fire Suppression & Access Control

**สิ่งที่ต้องรู้**
- **Power:** UPS online double-conversion (APC Symmetra/Galaxy, Vertiv Liebert, Delta, Syndome), N+1/2N, bypass, battery (VRLA อายุ 3–5 ปี / Li-ion), runtime calculation, ATS + generator, rack PDU (metered/switched), A/B feed
- **Cooling:** Precision Air Conditioning (PAC/CRAC) คุมอุณหภูมิและความชื้น, in-row cooling, hot/cold aisle containment, blanking panel, ASHRAE ช่วงที่แนะนำประมาณ 18–27 °C
- **Fire suppression:** FM-200 (HFC-227ea) / Novec 1230 / inert gas, smoke detection (VESDA), ห้องต้องปิดสนิท (room integrity test), abort/manual release, ความปลอดภัยของคน
- **Access & security:** biometric + card, CCTV, log การเข้าออก, ทางหนีไฟ
- **Raised floor:** ความสูง, รับน้ำหนัก, ใช้เป็น plenum ลมเย็นและเดินสาย, grounding
- **Environment monitoring:** temp/humidity sensor, water leak, smoke, door; แจ้งเตือนผ่าน SNMP/SMS
- เกี่ยวข้อง: มาตรฐาน TIA-942 และการตรวจรับงาน (commissioning)

**แบบทดสอบ**
1. Server 20 เครื่อง × 500 W + storage 2 kW + network 1 kW ต้องใช้ UPS อย่างน้อยกี่ kW (เผื่อ 30%) และระบายความร้อนกี่ BTU/hr
2. ทำไมห้อง FM-200 ต้องทำ room integrity test
3. PAC ต่างจากแอร์บ้าน/แอร์สำนักงานอย่างไร
4. ทำไมต้องใส่ blanking panel ในช่อง rack ที่ว่าง
5. แบตเตอรี่ UPS ควรตรวจหรือเปลี่ยนเมื่อไร

<details><summary>เฉลย</summary>

1. โหลด 13 kW × 1.3 ≈ 17 kW (เลือก UPS 20 kVA/kW ตาม power factor); ความร้อน 13 kW × 3,412 ≈ 44,400 BTU/hr (+ เผื่อ)
2. ก๊าซต้องคงความเข้มข้นในห้องตามเวลาที่กำหนด ถ้าห้องรั่วจะดับไฟไม่ได้
3. ออกแบบให้ทำงาน 24x7 คุมอุณหภูมิและความชื้นแม่นยำ ระบายความร้อนแบบ sensible ปริมาณสูง มี alarm/monitoring
4. ป้องกันลมร้อนด้านหลังวนกลับมาด้านหน้า (hot air recirculation)
5. ตรวจทุก PM (แรงดัน/ความต้านทาน/self-test) และวางแผนเปลี่ยนตามอายุ (VRLA ประมาณ 3–5 ปี) หรือเมื่อผลทดสอบตก
</details>

**5 โปรเจค**
- ⭐⭐ P1: Power & cooling calculator (kW, kVA, BTU/hr, UPS runtime, จำนวน PAC N+1)
- ⭐⭐ P2: DC room design (floor plan, raised floor, PAC, UPS room, FM-200 zone, access control) สำหรับ 8 rack
- ⭐⭐ P3: เปรียบเทียบ UPS 4 ยี่ห้อพันธมิตร (topology, efficiency, monitoring, ราคา)
- ⭐⭐ P4: Monitor UPS ผ่าน SNMP (NUT หรือ Zabbix template) + แจ้งเตือน on-battery
- ⭐⭐⭐ P5: DC facility commissioning checklist + PM checklist (UPS, PAC, FM-200, access, sensor)

---

## Level 23 — Cabling & Physical Infrastructure Standards

**สิ่งที่ต้องรู้**
- มาตรฐาน: TIA-568 (structured cabling), TIA-606 (labeling), TIA-607 (grounding/bonding), TIA-942 (DC), ISO/IEC 11801
- Topology ใน DC: MDA (main distribution), HDA, EDA; ToR vs EoR/MoR cabling
- Copper Cat6/6A, fiber OM3/OM4/OS2, MPO/MTP สำหรับ 40/100G, ODF/patch panel, cable tray/ladder
- Testing & certification: copper certification (Fluke DSX), fiber loss (OLTS) + OTDR, ผลทดสอบแนบ as-built
- Labeling ทั้ง 2 ปลาย, แยกสายไฟกับสายสัญญาณ, bend radius, ความยาวสำรอง
- Documentation: cable schedule, rack elevation, floor plan

**แบบทดสอบ**
1. MPO/MTP ใช้เมื่อไร
2. ทำไมต้องทำ certification test ไม่ใช่แค่ test ว่าต่อติด
3. OTDR ใช้หาอะไร
4. TIA-606 เกี่ยวกับอะไร
5. ToR กับ EoR cabling ต่างกันอย่างไร

<details><summary>เฉลย</summary>

1. ลิงก์ 40/100G ที่ใช้หลาย fiber พร้อมกัน และ trunk cable ความหนาแน่นสูง
2. พิสูจน์ว่าสายผ่านมาตรฐาน (NEXT, insertion loss, return loss) รองรับความเร็วตาม category และใช้เป็นหลักฐานรับประกัน
3. ตำแหน่งจุดต่อ/รอยหัก/จุดที่มี loss สูงตลอดเส้นใยแก้ว
4. การ label และ documentation ของระบบสาย
5. ToR = switch อยู่บนแต่ละ rack (สายสั้น); EoR = switch รวมที่ปลายแถว (สายยาวจากทุก rack)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Cable schedule (from/to/type/length/label) สำหรับ 4 rack
- ⭐⭐ P2: Labeling standard ตาม TIA-606 + template พิมพ์ label
- ⭐⭐ P3: Fiber loss budget calculator (ระยะ, จำนวนหัวต่อ/splice, ชนิด optic)
- ⭐⭐ P4: Rack elevation + patching diagram (NetBox) ของ lab/DC จำลอง
- ⭐⭐⭐ P5: Cabling acceptance procedure (test, เกณฑ์ผ่าน, รูปแบบรายงานผล) สำหรับงานส่งมอบ

---

## Level 29 — Storage Arrays ตามพอร์ตโฟลิโอ: Dell PowerStore, HPE Alletra, Sangfor aStor, Infortrend

> พื้นฐานจาก [SI L27](../SI-Track/01-datacenter-a.md)

**สิ่งที่ต้องรู้**
- **Dell PowerStore:** all-flash NVMe, data reduction (ลดขนาดข้อมูลได้ตามที่ Dell รับประกันตามเงื่อนไข), block/file/vVols, replication/Metro volume, PowerStore Manager + REST API
- **HPE Alletra (6000/9000/MP):** all-flash, InfoSight (predictive analytics), Data Services Cloud Console, replication/peer persistence
- **Sangfor aStor (Enterprise Distributed Storage):** software-defined/scale-out (block, file, object), เหมาะกับข้อมูลโตเร็ว, object storage สำหรับ backup/immutable
- **Infortrend EonStor (GS/DS):** unified/SAN storage ราคาประหยัด, เหมาะ SMB/งานภาพ/วิดีโอ/backup target
- งานที่ต้องทำได้: initial setup, pool/volume/LUN, host group, multipath, snapshot/replication, firmware upgrade (NDU), health/monitoring, collect log ส่ง support
- เลือกให้ตรงลูกค้า: performance-critical → all-flash (PowerStore/Alletra); capacity/scale-out/object → aStor; งบจำกัด → Infortrend

**แบบทดสอบ**
1. Scale-up กับ scale-out storage ต่างกันอย่างไร
2. ลูกค้าต้องการ backup target ที่ immutable ขนาด 500 TB และโตทุกปี ควรเสนอแบบไหน
3. ระบบ HIS ต้องการ latency < 1 ms ควรเสนอแบบไหน
4. HPE InfoSight ช่วยงาน support อย่างไร
5. ก่อน upgrade firmware storage ต้องทำอะไร

<details><summary>เฉลย</summary>

1. Scale-up เพิ่มดิสก์/shelf ใต้ controller เดิม; scale-out เพิ่ม node (ทั้ง performance และ capacity โตไปด้วยกัน)
2. Scale-out object storage ที่รองรับ Object Lock (เช่น Sangfor aStor หรือ object storage อื่น) + backup software ที่รองรับ immutability
3. All-flash NVMe (PowerStore/Alletra) + network ที่เหมาะสม
4. วิเคราะห์ telemetry ล่วงหน้า แจ้งปัญหา/ความเสี่ยงก่อนเกิดเหตุ และช่วยหา root cause
5. ตรวจ compatibility (host, HBA, OS, multipath), health ทุก controller/path, backup config, อ่าน release notes, นัด maintenance window, แจ้งลูกค้า
</details>

**5 โปรเจค**
- ⭐⭐ P1: ตารางเปรียบเทียบ 4 ยี่ห้อพันธมิตร (architecture, protocol, data services, use case, ระดับราคา)
- ⭐⭐ P2: Simulator/demo lab ของ vendor (Dell/HPE มี virtual lab/demo) สร้าง volume + host + snapshot
- ⭐⭐ P3: MinIO (แทน aStor) ทำ object storage + Object Lock เป็น backup target ของ Veeam
- ⭐⭐ P4: Storage installation & handover checklist (ใช้ได้กับทุกยี่ห้อ)
- ⭐⭐⭐ P5: Storage proposal 2 ทางเลือกให้ลูกค้าสมมติ (production all-flash + backup scale-out)

---

## Level 38 — Capstone Data Center (อ้างอิง PFO-DC-01)

**โจทย์:** องค์กรขนาดใหญ่ต้องการ Next-Gen Data Center ใหม่ 12 rack: cooling อัจฉริยะ, UPS สำรองไฟ, เครือข่าย 100 Gbps, server/storage สำหรับ VM 300 ตัว + database สำคัญ ทำงาน 24x7 และส่งมอบตาม ISO 9001

**แบบทดสอบ (Self-review)**
1. Power/cooling คำนวณจากโหลดจริง + เผื่อโต และ redundancy N+1/2N ถูกต้องหรือไม่
2. Server/storage/network ไม่มี SPOF และผ่าน HA test แล้วหรือยัง
3. Cabling ผ่าน certification และมีเอกสารครบหรือไม่
4. Monitoring (facility + IT) ส่งเข้า NOC 24x7 แล้วหรือยัง
5. UAT, as-built และ training ส่งมอบครบตามขั้นตอน ISO 9001 หรือไม่

**5 โปรเจค**
- ⭐⭐⭐ P1: Facility design (floor plan, power, PAC, FM-200, access) + calculation
- ⭐⭐⭐ P2: IT design (server, storage, 100G network, virtualization, HA) + sizing
- ⭐⭐⭐ P3: BOM 2 ทางเลือก (Dell/HPE/Lenovo + PowerStore/Alletra) + TCO 5 ปี
- ⭐⭐⭐ P4: Implementation plan + UAT 40 test case + lab ย่อส่วน
- ⭐⭐⭐ P5: Handover package + PM plan รายไตรมาส

---

## Level 43 — Capstone Backup & DR (อ้างอิง PFO-DR-04)

**โจทย์:** บริษัทผู้ผลิตและส่งออก มีโรงงาน 2 แห่ง (ใช้เป็น primary และ DR ของกันและกัน) ต้องการระบบสำรองข้อมูลอัตโนมัติข้ามสาขา (offsite replication) ที่ป้องกัน ransomware ได้ และ **RTO ≤ 15 นาที** สำหรับ ERP

**แบบทดสอบ (Self-review)**
1. RTO 15 นาทีเป็นไปได้ด้วยวิธีใด (replication + orchestration หรือ backup restore) พิสูจน์ด้วยการวัดแล้วหรือยัง
2. RPO ของ ERP เท่าไร และ bandwidth ระหว่างโรงงานพอหรือไม่
3. มี immutable copy ที่ผู้ดูแลระบบลบเองไม่ได้หรือไม่
4. DR drill มี runbook, ผลเวลา และรายงานส่งลูกค้าหรือยัง
5. Failback ทดสอบแล้วหรือยัง

> หมายเหตุ: คำว่า "กู้คืนได้ 100%" ในเอกสารขาย ต้องพิสูจน์ด้วยผล restore test จริงทุกครั้ง ห้ามรับปากโดยไม่มีผลทดสอบ

**5 โปรเจค**
- ⭐⭐⭐ P1: BIA + RTO/RPO ต่อระบบ + bandwidth calculation
- ⭐⭐⭐ P2: Backup & DR architecture (replication, immutable object lock, orchestration)
- ⭐⭐⭐ P3: Lab: Veeam/Proxmox replication 2 site + immutable repository
- ⭐⭐⭐ P4: DR drill จริงใน lab (failover → ตรวจ ERP → failback) + จับเวลา RTO
- ⭐⭐⭐ P5: RTO/RPO compliance report ฉบับส่งลูกค้า
