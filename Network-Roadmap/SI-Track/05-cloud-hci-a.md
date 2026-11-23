# Part 3 — คลาวด์และเวอร์ชวลไลเซชัน (Cloud & HCI) ตอน A: Hyper-Converged Infrastructure (Level 61–70)

> ตามบริการ: **Hyper-Converged Infrastructure (HCI) และการทำ Cloud Migration แบบไร้รอยต่อ**

---

## Level 61 — Hypervisor Landscape & Virtualization Deep Dive

**สิ่งที่ต้องรู้**
- Type 1 hypervisor: VMware ESXi, Microsoft Hyper-V, Nutanix AHV (KVM-based), Proxmox VE (KVM), Citrix XenServer, Red Hat OpenShift Virtualization
- เทคนิค: CPU scheduling, NUMA, memory ballooning/TPS, overcommit, paravirtual drivers (VMware PVSCSI/VMXNET3, VirtIO)
- ตลาดหลัง Broadcom ซื้อ VMware: เปลี่ยนเป็น subscription (VCF/VVF), ยกเลิก perpetual license → ลูกค้าประเมินย้าย platform จำนวนมาก
- เกณฑ์เลือก: ฟีเจอร์, ecosystem (backup/DR), ทักษะทีม, ราคา, support ในไทย
- VM ↔ container (ต่อที่ Level 79)

**แบบทดสอบ**
1. AHV สร้างบนเทคโนโลยีอะไร
2. ทำไม driver VirtIO/VMXNET3 สำคัญ
3. Memory overcommit มีความเสี่ยงอะไร
4. ปัจจัยที่ต้องพิจารณาเมื่อลูกค้าอยากย้ายออกจาก VMware
5. NUMA มีผลต่อ VM ขนาดใหญ่อย่างไร

<details><summary>เฉลย</summary>

1. KVM
2. Performance สูงกว่าอุปกรณ์จำลอง (emulated) และใช้ CPU น้อยกว่า
3. Host RAM ไม่พอทำให้ swap/ballooning และ performance ตกหนัก
4. ความเข้ากันได้ของ backup/DR/monitoring, เครื่องมือ migration, ทักษะทีม, license OS/app, hardware HCL, downtime ที่รับได้
5. VM ที่ vCPU/RAM เกิน 1 NUMA node จะต้องเข้าถึง memory ข้าม node ทำให้ช้าลง ควร size ให้พอดี NUMA
</details>

**5 โปรเจค**
- ⭐⭐ P1: ติดตั้ง Hyper-V, Proxmox และ ESXi (nested) แล้วสร้าง VM เดียวกันบนทุกตัว
- ⭐⭐ P2: ตารางเปรียบเทียบ 5 hypervisor (ฟีเจอร์, license, backup support, ราคา)
- ⭐⭐ P3: Benchmark VM ด้วย driver emulated vs paravirtual (fio, iperf3)
- ⭐⭐ P4: เอกสาร "VMware exit assessment" สำหรับลูกค้า (คำถาม, ความเสี่ยง, ทางเลือก)
- ⭐⭐⭐ P5: Decision matrix ถ่วงน้ำหนักเลือก platform ใหม่ให้ลูกค้าสมมติ 3 ราย

---

## Level 62 — HCI Concepts

**สิ่งที่ต้องรู้**
- HCI = compute + storage (software-defined, ใช้ดิสก์ใน node) + virtualization + management รวมในกล่องเดียว, scale-out ทีละ node
- เทียบ 3-tier (server + SAN + switch): ง่ายกว่า, จัดการจุดเดียว แต่ scale compute/storage แยกกันได้ยากกว่า
- Data protection: replication factor (RF2/RF3) หรือ erasure coding, data locality
- Failure domain: disk, node, block, rack; rebuild
- Use case: VDI, ROBO (สาขา), private cloud, รวม server เก่า
- Vendor: Nutanix, VMware vSAN/VCF (Dell VxRail), Microsoft Azure Local (เดิมชื่อ Azure Stack HCI), HPE (SimpliVity/Alletra dHCI), Huawei FusionCube

**แบบทดสอบ**
1. HCI ต่างจาก 3-tier อย่างไร
2. RF2 หมายความว่าอะไร
3. Erasure coding ดีกว่า RF ตรงไหน ข้อเสียคือ
4. ข้อเสียของ HCI เมื่อ storage โตเร็วกว่า compute
5. Data locality คืออะไร

<details><summary>เฉลย</summary>

1. ไม่มี SAN แยก ใช้ดิสก์ใน server รวมเป็น storage pool ด้วย software จัดการจากจุดเดียว
2. เก็บข้อมูล 2 สำเนาบน node ต่างกัน ทน node/disk เสีย 1 จุด
3. ใช้พื้นที่คุ้มกว่า; ข้อเสียคือใช้ CPU มากกว่า, write performance ต่ำกว่า, ต้องใช้ node มากขึ้น
4. ต้องซื้อ node (รวม CPU/license) เพิ่มเพื่อเพิ่มพื้นที่ (แก้ด้วย storage-only node หรือ external storage)
5. เก็บข้อมูลของ VM ไว้ใน node ที่ VM ทำงาน ลด network hop เพิ่ม performance
</details>

**5 โปรเจค**
- ⭐ P1: Infographic 3-tier vs HCI (ข้อดี/ข้อเสีย/use case)
- ⭐⭐ P2: คำนวณ usable capacity ของ cluster 4 node ที่ RF2, RF3 และ EC
- ⭐⭐ P3: ตารางเปรียบเทียบ HCI 4 ยี่ห้อ
- ⭐⭐ P4: Proxmox + Ceph 3 node (HCI แบบ open-source) ทดลองปิด node
- ⭐⭐⭐ P5: TCO 5 ปี: 3-tier (server + SAN) vs HCI สำหรับ 100 VM

---

## Level 63 — Nutanix (AOS, AHV, Prism)

**สิ่งที่ต้องรู้**
- สถาปัตยกรรม: CVM (Controller VM) บนทุก node, Distributed Storage Fabric, AOS
- Prism Element (ต่อ cluster) / Prism Central (หลาย cluster, ฟีเจอร์ขั้นสูง)
- RF2 ต้องอย่างน้อย 3 node, RF3 ต้องอย่างน้อย 5 node; storage container, compression/dedupe/EC-X
- Foundation (imaging/สร้าง cluster), LCM (Life Cycle Manager อัปเกรด firmware/software)
- Data protection: Protection Domain/Leap, snapshot, async/NearSync/sync replication, Metro Availability
- Networking: AHV ใช้ Open vSwitch (br0, bond), Flow Network Security (micro-seg), Flow Virtual Networking
- Nutanix Move (ย้าย VM จาก ESXi/Hyper-V/AWS → AHV), NCI/NCM licensing
- ฝึกฟรี: Nutanix Community Edition (CE), Nutanix University, NCA/NCP-MCI

**แบบทดสอบ**
1. CVM ทำหน้าที่อะไร
2. RF3 ต้องมีอย่างน้อยกี่ node
3. Prism Element vs Prism Central
4. ใช้เครื่องมืออะไร upgrade firmware/AOS
5. AHV networking ใช้เทคโนโลยีอะไร

<details><summary>เฉลย</summary>

1. บริหาร storage ของ node (I/O, replication, data services) และเป็นส่วนหนึ่งของ distributed system
2. 5 node
3. PE = จัดการ cluster เดียว; PC = จัดการหลาย cluster + ฟีเจอร์ขั้นสูง (Flow, automation, reporting)
4. LCM (Life Cycle Manager)
5. Open vSwitch (OVS)
</details>

**5 โปรเจค**
- ⭐⭐ P1: ติดตั้ง Nutanix CE (nested หรือ hardware เก่า) แบบ 1 หรือ 3 node
- ⭐⭐ P2: สร้าง VM, network, storage container, snapshot และ restore
- ⭐⭐ P3: ตั้ง Protection Domain replication ระหว่าง 2 cluster (CE)
- ⭐⭐ P4: Nutanix Prism v3/v4 API: Python ดึง VM list และ cluster health
- ⭐⭐⭐ P5: Build & handover guide Nutanix cluster 4 node (pre-req, Foundation, config, test)

---

## Level 64 — VMware vSAN & VMware Cloud Foundation

**สิ่งที่ต้องรู้**
- vSAN OSA (cache + capacity tier) vs ESA (NVMe single tier, vSAN 8+)
- Storage Policy-Based Management (SPBM): FTT=1/2, RAID-1/5/6
- ขั้นต่ำ: FTT=1 RAID-1 = 3 host (หรือ 2 node + witness), RAID-5 = 4 host (ESA เริ่มที่ 3 host ได้บาง configuration), RAID-6 = 6 host
- Stretched cluster + witness, 2-node ROBO, vSAN network (10/25G+, แยก VMkernel)
- vSAN ReadyNode / Dell VxRail, VCF (SDDC Manager, NSX, vSAN, Aria)
- Health check, Skyline/Diagnostics, resync

**แบบทดสอบ**
1. FTT=1 RAID-1 ใช้พื้นที่กี่เท่าของข้อมูล
2. RAID-6 (FTT=2) ต้องอย่างน้อยกี่ host
3. Witness ใน stretched cluster ทำหน้าที่อะไร
4. ESA ต่างจาก OSA อย่างไร
5. ทำไมต้องรอ resync เสร็จก่อน maintenance host ถัดไป

<details><summary>เฉลย</summary>

1. 2 เท่า
2. 6 host
3. ตัดสินเสียงข้างมาก (quorum) ป้องกัน split-brain เมื่อลิงก์ระหว่าง site ขาด
4. ESA ใช้ NVMe tier เดียว ไม่มี disk group, performance และ data services ดีกว่า (RAID-5/6 ประสิทธิภาพใกล้ RAID-1)
5. ระหว่าง resync ข้อมูลยังไม่ครบสำเนา ถ้าปิดอีก host อาจทำข้อมูลเข้าถึงไม่ได้
</details>

**5 โปรเจค**
- ⭐⭐ P1: vSAN nested lab 3 host (VMware HOL หรือ eval)
- ⭐⭐ P2: สร้าง storage policy 3 แบบ แล้ววัดพื้นที่ที่ใช้จริง
- ⭐⭐ P3: 2-node + witness lab แล้วทดลองปิด host
- ⭐⭐ P4: vSAN capacity calculator (RF/FTT, slack space 25–30%, growth)
- ⭐⭐⭐ P5: Maintenance runbook vSAN (ensure accessibility vs full data migration, firmware update)

---

## Level 65 — HCI ทางเลือกอื่น: Azure Local, HPE, Proxmox/Ceph

**สิ่งที่ต้องรู้**
- Microsoft Azure Local (ชื่อเดิม Azure Stack HCI): Hyper-V + Storage Spaces Direct (S2D) + Azure Arc, จ่ายรายเดือนผ่าน Azure, validated hardware
- S2D: mirror (2-way/3-way), parity, cache, RDMA (iWARP/RoCE) สำหรับ storage network
- HPE: SimpliVity, Alletra dHCI (disaggregated HCI: compute กับ storage แยก scale)
- Open-source: Proxmox VE + Ceph (MON, OSD, CRUSH, pool size/min_size)
- เลือกให้ตรงกับลูกค้า: Microsoft shop → Azure Local; งบจำกัด/ทีมมี Linux → Proxmox; ต้องการ enterprise support ครบ → Nutanix/vSAN

**แบบทดสอบ**
1. Azure Local ต้องเชื่อม Azure หรือไม่ ทำไม
2. S2D 3-way mirror ทนดิสก์/node เสียได้กี่จุด
3. dHCI ต่างจาก HCI อย่างไร
4. Ceph pool size=3, min_size=2 หมายความว่าอะไร
5. ลูกค้าแบบไหนเหมาะกับ Proxmox + Ceph

<details><summary>เฉลย</summary>

1. ต้องเชื่อม (ผ่าน Azure Arc) สำหรับ registration, billing และ management
2. 2 จุดพร้อมกัน
3. dHCI แยก compute node กับ storage array แต่จัดการแบบ HCI ทำให้ scale แยกกันได้
4. เก็บ 3 สำเนา, รับ I/O ได้ตราบที่มีอย่างน้อย 2 สำเนา
5. งบจำกัด, ทีมมีทักษะ Linux, รับได้กับ support แบบ subscription ของ Proxmox/partner
</details>

**5 โปรเจค**
- ⭐⭐ P1: S2D lab ด้วย Windows Server (nested) 2–3 node
- ⭐⭐ P2: Proxmox + Ceph 3 node พร้อม CRUSH rule และทดสอบ OSD เสีย
- ⭐⭐ P3: เปรียบเทียบ Azure Local vs Nutanix vs vSAN ด้าน license model ในไทย
- ⭐⭐ P4: Decision tree "ลูกค้าแบบนี้ควรใช้ HCI ตัวไหน"
- ⭐⭐⭐ P5: PoC plan HCI 2 ยี่ห้อพร้อม success criteria สำหรับลูกค้า

---

## Level 66 — HCI Sizing & Design

**สิ่งที่ต้องรู้**
- Input: VM inventory (RVTools/Collector), performance (CPU %, RAM, IOPS, latency), growth, workload พิเศษ (DB, VDI)
- Compute: core รวม ÷ ratio, RAM (+ CVM/overhead), N+1 (หรือ N+2 สำหรับ cluster ใหญ่/ระหว่าง upgrade)
- Storage: logical → × RF/FTT → + slack (vSAN 25–30%, Nutanix เผื่อ rebuild 1 node) → ÷ data reduction (ระมัดระวัง)
- Performance: all-flash/NVMe, network 25G ขึ้นไป
- Sizer tools: Nutanix Sizer, vSAN ReadyNode Sizer, Dell/HPE sizer
- License: core-based (VCF/VVF, NCI, Windows Server Datacenter)

**แบบทดสอบ**
1. ทำไมต้องเผื่อพื้นที่สำหรับ rebuild 1 node
2. VM 200 ตัว รวม 600 GB RAM, host มี 512 GB (ใช้ได้ 450 GB หลังหัก overhead) ต้องกี่ host (N+1)
3. ทำไมไม่ควร size ด้วย data reduction สูงเกินจริง
4. N+2 ใช้เมื่อไร
5. License นับตาม core มีผลต่อการเลือก CPU อย่างไร

<details><summary>เฉลย</summary>

1. เมื่อ node เสีย ข้อมูลต้องถูกสร้างสำเนาใหม่บน node ที่เหลือ ถ้าพื้นที่ไม่พอจะ rebuild ไม่ได้
2. 600/450 = 1.33 → 2 host + 1 = 3 host (ตรวจ CPU และ storage ประกอบด้วย)
3. ถ้าลดได้น้อยกว่าที่คิด พื้นที่จะหมดเร็ว ลูกค้าต้องซื้อเพิ่มกะทันหัน
4. Cluster ใหญ่หรือ workload สำคัญ ที่ต้องทน host เสียระหว่าง maintenance อีก host
5. เลือก CPU core น้อยแต่ clock สูงอาจประหยัด license; ต้องสมดุลกับจำนวน host
</details>

**5 โปรเจค**
- ⭐⭐ P1: HCI sizing spreadsheet (compute + storage + N+1 + growth)
- ⭐⭐ P2: ใช้ Nutanix Sizer หรือ vSAN Sizer กับข้อมูลสมมติแล้วเทียบกับ spreadsheet ตัวเอง
- ⭐⭐ P3: Python อ่าน RVTools export → คำนวณ sizing อัตโนมัติ
- ⭐⭐ P4: Sizing สำหรับ VDI 500 users (persistent vs non-persistent)
- ⭐⭐⭐ P5: Sizing report ฉบับส่งลูกค้า (assumptions, ผลลัพธ์, ความเสี่ยง, ตัวเลือก)

---

## Level 67 — HCI Network Design

**สิ่งที่ต้องรู้**
- ToR คู่ (MLAG/vPC/stack), 25G ขึ้นไปสำหรับ storage traffic, 1G สำหรับ IPMI/iDRAC
- Traffic: management, storage/backplane (CVM/vSAN), live migration, VM networks, backup
- Teaming: active-backup (ง่าย ปลอดภัย), LACP (ต้องตั้ง switch ให้ตรง), LBT
- MTU 9000 สำหรับ storage (ต้องตรงกันทุก hop), ไม่ใช้ STP blocking บน server port (portfast/edge)
- RDMA (RoCEv2/iWARP) สำหรับ S2D/บางรุ่น ต้องตั้ง DCB/PFC
- Multicast/IGMP (vSAN รุ่นเก่า) — vSAN 6.6+ ใช้ unicast

**แบบทดสอบ**
1. ทำไม storage network ของ HCI ควร ≥ 25G
2. active-backup กับ LACP เลือกอย่างไร
3. ผลของ MTU ไม่ตรงกันใน vSAN/Nutanix network
4. ทำไมต้อง portfast/edge port
5. ลูกค้ามี switch แค่ 1 ตัว ปัญหาคืออะไร

<details><summary>เฉลย</summary>

1. ทุก write ต้องส่ง replica ข้าม network และ rebuild ใช้ bandwidth สูง
2. Active-backup ง่าย ไม่ต้องพึ่ง config switch; LACP ได้ bandwidth รวมแต่ซับซ้อน (ต้องมี MLAG)
3. Packet ใหญ่ถูก drop ทำให้ storage ช้า/partition, health check fail
4. ไม่ต้องรอ STP 30 วินาทีตอน link up (ระหว่าง reboot node)
5. Single point of failure: switch ล่มทั้ง cluster ล่ม
</details>

**5 โปรเจค**
- ⭐⭐ P1: HCI network diagram + VLAN/IP table สำหรับ 4 node
- ⭐⭐ P2: Switch config template สำหรับ ToR คู่ (Cisco/Dell/Aruba) พร้อม port profile ของ node
- ⭐⭐ P3: ทดสอบ MTU mismatch ใน Proxmox/Ceph lab แล้วบันทึกอาการ
- ⭐⭐ P4: Pre-install network validation script (ping/MTU/VLAN ระหว่าง node)
- ⭐⭐⭐ P5: RDMA/DCB design สำหรับ Azure Local (PFC priority 3, ETS) พร้อมเหตุผล

---

## Level 68 — HCI Deployment & Lifecycle Management

**สิ่งที่ต้องรู้**
- Deploy: Nutanix Foundation, vSAN cluster quickstart/VCF bring-up, Azure Local deployment via Azure portal
- Day-2: เพิ่ม/ถอด node, เปลี่ยนดิสก์, upgrade (LCM, vLCM image-based), health check
- Upgrade order ตาม vendor (เช่น firmware → hypervisor → AOS/vSAN) และ compatibility matrix
- Rolling upgrade ทีละ node (VM migrate ออกอัตโนมัติ)
- Capacity monitoring + forecast (runway)

**แบบทดสอบ**
1. Rolling upgrade คืออะไร
2. ทำไมต้องตรวจ cluster health ก่อน upgrade
3. vLCM image-based ดีอย่างไร
4. การเพิ่ม node ต้องตรวจอะไร
5. Capacity runway คืออะไร

<details><summary>เฉลย</summary>

1. Upgrade ทีละ node โดยย้าย VM ออกก่อน ระบบยังให้บริการตลอด
2. ถ้ามีปัญหาค้างอยู่ (resync, disk เสีย) การปิด node อาจทำให้ข้อมูลเข้าถึงไม่ได้
3. กำหนด ESXi + driver + firmware เป็นชุดเดียวกันทุก host ไม่ drift
4. Hardware/firmware ตรงกับ node เดิม, network/VLAN, license, version software
5. ระยะเวลาที่ทรัพยากรจะพอใช้ก่อนเต็มจากแนวโน้มปัจจุบัน
</details>

**5 โปรเจค**
- ⭐⭐ P1: Upgrade Nutanix CE/Proxmox cluster แบบ rolling ใน lab พร้อม runbook
- ⭐⭐ P2: เพิ่ม node ใน cluster lab แล้วดู rebalance
- ⭐⭐ P3: Pre-upgrade health check script (API) ที่สรุป go/no-go
- ⭐⭐ P4: Lifecycle calendar ของลูกค้า (patch รายไตรมาส, firmware, EoL)
- ⭐⭐⭐ P5: Capacity forecast จาก metric 90 วัน (Python) + กราฟ runway

---

## Level 69 — Cloud Fundamentals

**สิ่งที่ต้องรู้**
- IaaS / PaaS / SaaS, public / private / hybrid / multi-cloud, shared responsibility
- Region, Availability Zone; ในไทย: AWS Asia Pacific (Bangkok) region (เปิดปี 2025), Microsoft ประกาศ datacenter region ในไทย, Google Cloud ประกาศลงทุน, และ local cloud (เช่น NT, True IDC, INET)
- Pricing model: on-demand, reserved/savings plan, spot, egress cost
- Well-Architected Framework (security, reliability, performance, cost, operational excellence, sustainability)
- Data residency และ PDPA (การส่งข้อมูลออกนอกประเทศ)

**แบบทดสอบ**
1. Shared responsibility ใน SaaS ลูกค้ายังรับผิดชอบอะไร
2. AZ คืออะไร ทำไมต้องกระจาย workload หลาย AZ
3. Egress cost คืออะไร
4. Reserved instance เหมาะกับ workload แบบไหน
5. PDPA เกี่ยวกับการเลือก region อย่างไร

<details><summary>เฉลย</summary>

1. Data, identity/access (user, MFA), การตั้งค่า, endpoint
2. Data center แยกกันภายใน region (ไฟ/เครือข่ายแยก) กระจายเพื่อ HA
3. ค่าส่งข้อมูลออกจาก cloud (ไปอินเทอร์เน็ตหรือข้าม region)
4. Workload ที่ทำงานคงที่ต่อเนื่อง 1–3 ปี
5. การส่งข้อมูลส่วนบุคคลไปต่างประเทศต้องมีมาตรการตามกฎหมาย จึงอาจต้องเลือก region ในไทย
</details>

**5 โปรเจค**
- ⭐ P1: เปรียบเทียบบริการพื้นฐาน AWS/Azure/GCP (compute, storage, network, DB)
- ⭐⭐ P2: Pricing calculator: ประเมินค่าใช้จ่าย 50 VM บน AWS และ Azure
- ⭐⭐ P3: Well-Architected review ของแอปตัวอย่าง (ใช้ tool ของ AWS หรือ Azure)
- ⭐⭐ P4: ตาราง "ลูกค้าไทยควรเลือก region ไหน" ตามประเภทข้อมูล
- ⭐⭐⭐ P5: Cloud strategy deck สำหรับผู้บริหาร (ทำไม, อะไรย้าย, อะไรไม่ย้าย, ค่าใช้จ่าย)

---

## Level 70 — AWS & Azure Core Services สำหรับ SI

> Network ของ cloud ดู Roadmap หลัก [L78, L79](../08-datacenter-cloud.md)

**สิ่งที่ต้องรู้**
- AWS: IAM, VPC, EC2, EBS, S3, ELB, RDS, Route 53, CloudWatch, Organizations/Control Tower
- Azure: Entra ID, Subscription/Management Group/Resource Group, VNet, VM, Managed Disk, Storage Account, Load Balancer/App Gateway, Azure SQL, Monitor, Azure Policy
- Identity เชื่อมกับ AD ของลูกค้า (Entra Connect / IAM Identity Center)
- Tagging, naming convention, RBAC
- Cert ที่ควรมี: AWS SAA, AZ-104, AZ-305

**แบบทดสอบ**
1. Azure Resource Group ใช้ทำอะไร
2. EBS ต่างจาก S3 อย่างไร
3. Entra Connect ทำอะไร
4. ทำไมต้องมี tagging policy
5. AWS Organizations/Azure Management Group ช่วยอะไร

<details><summary>เฉลย</summary>

1. จัดกลุ่ม resource ที่มี lifecycle เดียวกัน (สิทธิ์, ลบ, ค่าใช้จ่าย)
2. EBS = block storage ผูกกับ EC2; S3 = object storage เข้าถึงผ่าน API
3. Sync identity จาก AD on-prem ไป Entra ID (hybrid identity)
4. แยกค่าใช้จ่ายตามแผนก/โปรเจค, automation, ownership
5. จัดการหลาย account/subscription และบังคับ policy จากศูนย์กลาง
</details>

**5 โปรเจค**
- ⭐⭐ P1: AWS: VPC + EC2 web + ALB + RDS (free tier) แล้วลบทิ้ง
- ⭐⭐ P2: Azure: VNet + VM + Load Balancer + Azure SQL แล้วลบทิ้ง
- ⭐⭐ P3: Naming/tagging convention + Azure Policy บังคับ tag
- ⭐⭐ P4: Hybrid identity lab: AD → Entra ID (Entra Connect cloud sync)
- ⭐⭐⭐ P5: Landing zone แบบย่อ (management group, policy, hub network) ด้วย Terraform
