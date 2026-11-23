# Part 3 — คลาวด์และเวอร์ชวลไลเซชัน (Cloud & HCI) ตอน B: Cloud Migration แบบไร้รอยต่อ (Level 71–80)

---

## Level 71 — Hybrid Connectivity สำหรับ Migration

> พื้นฐานจาก Roadmap หลัก [L58](../06-services-wireless-wan.md), [L79](../08-datacenter-cloud.md)

**สิ่งที่ต้องรู้**
- Site-to-site VPN (BGP) → AWS VGW/TGW, Azure VPN Gateway; Direct Connect / ExpressRoute ผ่าน partner ในไทย
- Bandwidth ที่ต้องใช้สำหรับ migration: ขนาดข้อมูล ÷ เวลา + replication delta
- Hybrid DNS (conditional forwarder, resolver endpoint), AD extension (DC ใน cloud)
- Firewall rule สำหรับเครื่องมือ migration (replication port)
- L2 extension ชั่วคราว (VMware HCX Network Extension) เพื่อย้ายโดยไม่เปลี่ยน IP

**แบบทดสอบ**
1. ข้อมูล 50 TB ลิงก์ 1 Gbps (ใช้ได้จริง 70%) ใช้เวลาประมาณกี่วัน
2. เมื่อไรควรใช้ offline transfer (Snowball/Data Box)
3. ข้อดีของ L2 extension ระหว่าง migration
4. ทำไมต้องมี DC ใน cloud
5. Hybrid DNS ต้องตั้งอะไรทั้ง 2 ฝั่ง

<details><summary>เฉลย</summary>

1. 50 TB = 400,000 Gb ÷ 0.7 Gbps ≈ 571,000 วินาที ≈ 6.6 วัน
2. ข้อมูลมากจนการโอนผ่านเครือข่ายใช้เวลานานเกินรับได้ หรือ bandwidth จำกัด
3. VM ย้ายแล้วใช้ IP เดิม ไม่ต้องแก้ app/firewall/DNS (ลด downtime และความเสี่ยง)
4. ให้ VM ใน cloud authenticate ได้แม้ลิงก์ไป on-prem ขาด และลด latency
5. On-prem forward zone ของ cloud ไป resolver endpoint; cloud forward zone ของ on-prem ไป DNS ภายใน
</details>

**5 โปรเจค**
- ⭐⭐ P1: Site-to-site VPN BGP: lab (pfSense/VyOS) ↔ AWS หรือ Azure
- ⭐⭐ P2: Migration bandwidth calculator (ข้อมูล, ลิงก์, เวลา cutover)
- ⭐⭐ P3: Hybrid DNS lab (BIND ↔ Azure DNS Private Resolver/Route 53 Resolver)
- ⭐⭐ P4: Firewall/port requirement ของเครื่องมือ migration (HCX, Move, AWS MGN, Azure Migrate)
- ⭐⭐⭐ P5: Connectivity design สำหรับ migration 300 VM (ระหว่างย้าย และหลังย้าย)

---

## Level 72 — Migration Strategy & Assessment

**สิ่งที่ต้องรู้**
- 7Rs: Retire, Retain, Rehost (lift-and-shift), Relocate, Replatform, Repurchase (SaaS), Refactor
- Discovery & assessment: Azure Migrate, AWS Migration Evaluator/Application Discovery Service, Nutanix Collector, RVTools
- Dependency mapping (ต่อยอดจาก L49): แอปไหนต้องย้ายพร้อมกัน (move group)
- Wave planning: เริ่มจากระบบเสี่ยงต่ำ (pilot) → ระบบสำคัญ
- Business case: TCO on-prem vs cloud, license (BYOL, Azure Hybrid Benefit)
- ความเสี่ยง: latency ระหว่าง app กับ DB ที่ย้ายแยกกัน, license ของ app, compliance

**แบบทดสอบ**
1. Rehost กับ Replatform ต่างกันอย่างไร
2. ทำไมต้องมี dependency mapping ก่อนแบ่ง wave
3. ระบบแบบไหนควรเป็น wave แรก
4. Azure Hybrid Benefit คืออะไร
5. ตัวอย่างระบบที่ควร Retain

<details><summary>เฉลย</summary>

1. Rehost ย้าย VM เดิมไปตรง ๆ; Replatform ปรับเล็กน้อย (เช่น DB ย้ายไป managed service)
2. ถ้าย้าย app กับ DB แยก wave จะเกิด latency ข้าม site หรือพัง
3. ระบบสำคัญน้อย dependency น้อย (dev/test, internal tools) เพื่อทดสอบกระบวนการ
4. ใช้ license Windows Server/SQL Server เดิม (ที่มี SA) ใน Azure ลดค่าใช้จ่าย
5. ระบบที่ผูกกับ hardware/latency ต่ำมาก, ข้อกำหนด data residency, ระบบใกล้ปลดระวาง
</details>

**5 โปรเจค**
- ⭐⭐ P1: Azure Migrate appliance discovery ใน lab (Hyper-V/VMware)
- ⭐⭐ P2: Assessment workbook: 50 VM จัดกลุ่มด้วย 7Rs พร้อมเหตุผล
- ⭐⭐ P3: Dependency map → move groups (ใช้ข้อมูล netstat/flow ของ lab)
- ⭐⭐ P4: Wave plan 4 wave + timeline + ผู้รับผิดชอบ
- ⭐⭐⭐ P5: Migration business case (TCO 5 ปี, ความเสี่ยง, ROI) ให้ลูกค้าสมมติ

---

## Level 73 — Migration Tools & Seamless Cutover

**สิ่งที่ต้องรู้**
- VMware → VMware (DC ใหม่/cloud): VMware HCX (bulk migration, vMotion, replication-assisted vMotion, Network Extension)
- VMware/Hyper-V → Nutanix AHV: Nutanix Move (replicate แล้ว cutover)
- → AWS: AWS Application Migration Service (MGN, block-level replication ต่อเนื่อง)
- → Azure: Azure Migrate Server Migration (agentless สำหรับ VMware/Hyper-V)
- → Proxmox: import wizard จาก ESXi, `qm importdisk`
- **แบบไร้รอยต่อ (seamless):** replicate ต่อเนื่อง → test migration ใน isolated network → cutover ใน window สั้น (นาที) → ตรวจสอบ → rollback ได้
- ระวัง: driver (VMware Tools → VirtIO/Hyper-V), IP/MAC เปลี่ยน, license activation, app ที่ผูก hardware

**แบบทดสอบ**
1. Replication-based migration ช่วยลด downtime อย่างไร
2. Test migration ทำไมต้องทำใน isolated network
3. ย้าย VM จาก ESXi → AHV ต้องระวังเรื่อง driver อะไร
4. Rollback plan ของ cutover คืออะไร
5. HCX Network Extension ช่วยอะไร

<details><summary>เฉลย</summary>

1. ข้อมูลส่วนใหญ่ถูกส่งไปล่วงหน้า ตอน cutover ส่งแค่ delta สุดท้าย downtime จึงเหลือไม่กี่นาที
2. ไม่ให้ IP/ชื่อชนกับเครื่อง production ที่ยังทำงาน
3. ต้องติดตั้ง VirtIO driver (Move ช่วยติดตั้งให้ใน OS ที่รองรับ) และถอด VMware Tools หลังย้าย
4. เปิด VM ต้นทางกลับ (ไม่ลบต้นทางจนกว่าจะผ่าน acceptance) และย้อน DNS/route
5. ย้าย VM โดยไม่เปลี่ยน IP (ขยาย L2 ชั่วคราว)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Nutanix Move: ESXi (nested) → Nutanix CE ย้าย VM Windows + Linux
- ⭐⭐ P2: ESXi → Proxmox ด้วย import wizard พร้อมบันทึกปัญหา driver/network
- ⭐⭐ P3: Azure Migrate หรือ AWS MGN ย้าย VM 1 ตัว (lab, ลบทรัพยากรหลังจบ)
- ⭐⭐⭐ P4: Cutover runbook (T-7 วัน → T-0 → T+1) ของแอป 3 tier พร้อม go/no-go และ rollback
- ⭐⭐⭐ P5: วัด downtime จริงของ cutover แบบ replication vs cold migration แล้วเขียนรายงาน

---

## Level 74 — Database & Data Migration

**สิ่งที่ต้องรู้**
- Offline (backup/restore, ต้องหยุดระบบ) vs Online (replication, CDC, downtime น้อย)
- เครื่องมือ: AWS DMS, Azure Database Migration Service, SQL Server log shipping/AG, Oracle Data Guard/GoldenGate, pg_dump/logical replication
- Homogeneous vs heterogeneous (เช่น Oracle → PostgreSQL ต้องแปลง schema: AWS SCT)
- File data: robocopy (`/MIR`, `/COPY:DATS`), rsync, Azure File Sync, AWS DataSync; ACL/permission
- Data validation: row count, checksum, application test

**แบบทดสอบ**
1. CDC คืออะไร
2. ย้าย file server ต้องระวังอะไร
3. Heterogeneous migration ยากตรงไหน
4. วิธีตรวจว่าข้อมูลย้ายครบ
5. ทำไมต้องหยุดการเขียนก่อน cutover สุดท้าย

<details><summary>เฉลย</summary>

1. Change Data Capture: จับการเปลี่ยนแปลงต่อเนื่องแล้ว replay ปลายทาง
2. Permission (NTFS ACL), path ยาว, ไฟล์เปิดค้าง, DFS namespace/drive mapping ของผู้ใช้
3. Schema, data type, stored procedure, SQL dialect ต้องแปลงและทดสอบ app ใหม่
4. Row count, checksum/hash, query ตัวอย่าง, ให้ผู้ใช้/app owner ทดสอบ
5. ให้ข้อมูลต้นทางกับปลายทางตรงกันสมบูรณ์ ไม่มีรายการที่เขียนหายระหว่างสลับ
</details>

**5 โปรเจค**
- ⭐⭐ P1: PostgreSQL logical replication ย้าย DB แบบ near-zero downtime (docker)
- ⭐⭐ P2: SQL Server backup/restore → Azure SQL Managed Instance หรือ VM (lab)
- ⭐⭐ P3: robocopy migration script + log + รายงานไฟล์ที่ copy ไม่ได้
- ⭐⭐ P4: Data validation script (row count + checksum) ระหว่าง DB ต้นทาง/ปลายทาง
- ⭐⭐⭐ P5: DB migration runbook พร้อม cutover timeline นาทีต่อนาที

---

## Level 75 — Cloud Backup & DR (DRaaS)

**สิ่งที่ต้องรู้**
- Backup ไป cloud: Veeam Cloud Connect, Azure Backup, AWS Backup, S3/Blob + immutability
- DR ไป cloud: Azure Site Recovery, AWS Elastic Disaster Recovery (DRS), Zerto, Nutanix NC2
- Pilot light, warm standby, multi-site active-active
- ค่าใช้จ่าย: storage ถูก, compute จ่ายเมื่อ failover/drill
- DR drill ใน cloud ทำได้ง่ายโดยไม่กระทบ production

**แบบทดสอบ**
1. Pilot light คืออะไร
2. ทำไม DR ใน cloud ประหยัดกว่าสร้าง DR site เอง
3. Azure Site Recovery ใช้ทำอะไร
4. ข้อควรระวังเรื่อง network ตอน failover ไป cloud
5. ทำไม backup ใน cloud ต้องเปิด immutability

<details><summary>เฉลย</summary>

1. รัน core ขั้นต่ำ (เช่น DB replica) ไว้ใน cloud และเปิดส่วนที่เหลือเมื่อเกิดเหตุ
2. ไม่ต้องซื้อ hardware/พื้นที่ จ่ายค่า compute เฉพาะตอนใช้
3. Replicate และ failover VM/server ไป Azure (หรือระหว่าง region)
4. IP plan, DNS, VPN/ผู้ใช้เข้าถึง, firewall rule, license
5. ป้องกัน ransomware/ผู้ดูแลถูกยึดบัญชีแล้วลบ backup
</details>

**5 โปรเจค**
- ⭐⭐ P1: Veeam backup → S3-compatible + Object Lock (ต่อยอด L31)
- ⭐⭐ P2: Azure Site Recovery หรือ AWS DRS 1 VM + test failover (ลบทรัพยากรหลังจบ)
- ⭐⭐ P3: DR cost comparison: DR site vs colocation vs DRaaS (3 ปี)
- ⭐⭐ P4: DR network design (IP, DNS, VPN สำหรับผู้ใช้) เมื่อ failover ไป cloud
- ⭐⭐⭐ P5: DR drill report แบบส่งลูกค้า (scope, ผล RTO/RPO, ปัญหา, การปรับปรุง)

---

## Level 76 — Cloud Governance, Landing Zone & FinOps

**สิ่งที่ต้องรู้**
- Landing zone: AWS Control Tower, Azure Landing Zone (CAF), hub-spoke network, identity, logging, policy
- Guardrails: SCP, Azure Policy (deny region, บังคับ tag, ห้าม public IP)
- FinOps: visibility (tag, cost allocation), optimize (rightsizing, reserved/savings plan, shutdown schedule, ลบ orphan disk/IP), budget & alert
- Operating model: ใครสร้าง resource ได้, approval, CI/CD
- Cloud Center of Excellence (CCoE)

**แบบทดสอบ**
1. Landing zone คืออะไร
2. ตัวอย่าง guardrail 3 ข้อ
3. Rightsizing คืออะไร
4. ทรัพยากรที่มักถูกลืมแล้วเสียเงิน
5. ทำไมต้องตั้ง budget alert

<details><summary>เฉลย</summary>

1. สภาพแวดล้อม cloud พื้นฐานที่วางโครงสร้าง account/network/identity/security/logging ไว้ก่อนย้าย workload
2. จำกัด region, ห้าม public storage, บังคับ encryption/tag, ห้ามปิด logging
3. ปรับขนาด VM ให้ตรงการใช้งานจริง
4. Disk ที่ไม่ได้ต่อ VM, snapshot เก่า, public IP ที่ไม่ใช้, NAT gateway, VM dev ที่เปิดทิ้งไว้
5. รู้ก่อนค่าใช้จ่ายบานปลาย (เช่น resource ที่เปิดผิดพลาด)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Azure Policy/AWS SCP 5 ข้อ ใน lab
- ⭐⭐ P2: Budget + alert + cost dashboard แยกตาม tag
- ⭐⭐ P3: สคริปต์หา orphan resource (disk, IP, snapshot) แล้วรายงาน
- ⭐⭐ P4: Auto start/stop VM dev ตามเวลา (Automation/Lambda)
- ⭐⭐⭐ P5: FinOps monthly report template + คำแนะนำลดค่าใช้จ่าย

---

## Level 77 — Infrastructure as Code & Automation สำหรับ Cloud/HCI

> พื้นฐานจาก Roadmap หลัก [L82, L85](../09-automation-operations.md)

**สิ่งที่ต้องรู้**
- Terraform providers: AWS, AzureRM, Nutanix, vSphere, Proxmox; Bicep/ARM, CloudFormation
- Ansible: VM provisioning, OS configuration, Nutanix/VMware collections
- PowerCLI, Nutanix API v4, Proxmox API
- Template/golden image (Packer), cloud-init/sysprep
- GitOps, pipeline approval

**แบบทดสอบ**
1. Packer ใช้ทำอะไร
2. cloud-init ทำอะไรตอน VM boot
3. ทำไมต้องเก็บ Terraform state ไว้ remote
4. Terraform vs Ansible ในงาน HCI
5. ข้อดีของ golden image

<details><summary>เฉลย</summary>

1. สร้าง VM template/image แบบอัตโนมัติและทำซ้ำได้
2. ตั้ง hostname, user, SSH key, network, รันสคริปต์ครั้งแรก
3. ทีมใช้ร่วมกันได้ มี locking ไม่ให้ state พัง
4. Terraform สร้าง VM/network/resource; Ansible ตั้งค่า OS/app ภายใน
5. ทุก VM เริ่มจากมาตรฐานเดียว (patch, hardening, agent) deploy เร็ว
</details>

**5 โปรเจค**
- ⭐⭐ P1: Packer สร้าง Ubuntu template (Proxmox/vSphere)
- ⭐⭐ P2: Terraform สร้าง 3 VM บน Proxmox/Nutanix CE จาก template
- ⭐⭐ P3: Ansible ติดตั้ง agent (monitoring, EDR, backup) ให้ VM ใหม่อัตโนมัติ
- ⭐⭐⭐ P4: Self-service VM request: form → pipeline → Terraform → ส่งอีเมลแจ้ง
- ⭐⭐⭐ P5: Terraform module เดียวสร้าง landing zone เล็กบน Azure หรือ AWS

---

## Level 78 — Containers & Kubernetes บน HCI/Cloud

> พื้นฐานจาก Roadmap หลัก [L76, L77](../08-datacenter-cloud.md)

**สิ่งที่ต้องรู้**
- Kubernetes บน HCI: Nutanix Kubernetes Platform (NKP), VMware vSphere Kubernetes Service (เดิมชื่อ Tanzu), Rancher/RKE2, OpenShift
- Managed: EKS, AKS, GKE; hybrid: Azure Arc-enabled Kubernetes, AKS on Azure Local
- Storage: CSI driver (Nutanix CSI, vSphere CSI), persistent volume
- VM + container: KubeVirt/OpenShift Virtualization (อีกทางเลือกหนึ่งสำหรับลูกค้าที่ย้ายออกจาก VMware)
- Network: CNI, ingress, load balancer (MetalLB)

**แบบทดสอบ**
1. CSI driver ทำหน้าที่อะไร
2. Managed Kubernetes ช่วยลดภาระอะไร
3. KubeVirt คืออะไร
4. ทำไม on-prem Kubernetes ต้องใช้ MetalLB หรือ LB ภายนอก
5. Persistent Volume ต่างจาก ephemeral storage อย่างไร

<details><summary>เฉลย</summary>

1. ให้ Kubernetes สร้าง/ต่อ volume จาก storage platform อัตโนมัติ
2. Control plane (upgrade, HA, etcd backup) ผู้ให้บริการดูแล
3. รัน VM เป็น workload ใน Kubernetes
4. Service type LoadBalancer ต้องมีผู้แจก external IP (ใน cloud มีอัตโนมัติ)
5. PV อยู่ต่อแม้ Pod ถูกลบ; ephemeral หายไปกับ Pod
</details>

**5 โปรเจค**
- ⭐⭐ P1: RKE2/k3s บน VM ใน Proxmox/Nutanix CE + MetalLB
- ⭐⭐ P2: CSI driver (Longhorn หรือ Nutanix CSI) + stateful app (PostgreSQL)
- ⭐⭐ P3: AKS หรือ EKS cluster + deploy app เดียวกัน เปรียบเทียบการจัดการ
- ⭐⭐⭐ P4: KubeVirt รัน VM ใน Kubernetes lab
- ⭐⭐⭐ P5: Backup/restore Kubernetes ด้วย Velero

---

## Level 79 — Hybrid Cloud Operations

**สิ่งที่ต้องรู้**
- Single pane of glass: Azure Arc (จัดการ server/K8s on-prem จาก Azure), Nutanix Prism Central + NC2, VMware Aria
- Monitoring/logging ข้าม on-prem และ cloud (Azure Monitor, CloudWatch, Grafana)
- Patch/update ข้าม environment (Azure Update Manager, SSM)
- Security posture ข้าม environment (Defender for Cloud + Arc)
- Workload placement: อะไรควรอยู่ on-prem/HCI อะไรควรอยู่ cloud (latency, cost, compliance)

**แบบทดสอบ**
1. Azure Arc ทำอะไรได้
2. ปัจจัยตัดสินว่า workload ควรอยู่ที่ไหน
3. ทำไมต้องมี monitoring ที่รวมศูนย์
4. Repatriation คืออะไร
5. Nutanix NC2 คืออะไร

<details><summary>เฉลย</summary>

1. จัดการ server/Kubernetes/SQL ที่อยู่นอก Azure ด้วย policy, update, monitoring, security ของ Azure
2. Latency, data residency/compliance, ค่าใช้จ่ายต่อเนื่อง, ความผันผวนของโหลด, dependency
3. ทีม Support เห็นปัญหาทั้งระบบในที่เดียว ลดเวลาวิเคราะห์
4. ย้าย workload กลับจาก cloud มา on-prem (มักเพราะค่าใช้จ่ายหรือ performance)
5. Nutanix Cloud Clusters: รัน Nutanix stack บน bare metal ใน AWS/Azure (ย้าย VM ไปกลับได้ง่าย)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Onboard server lab เข้า Azure Arc + Update Manager
- ⭐⭐ P2: Grafana dashboard รวม metric on-prem + cloud
- ⭐⭐ P3: Workload placement matrix ของลูกค้าสมมติ 30 ระบบ
- ⭐⭐ P4: Hybrid operations runbook (patch, backup, monitoring, incident)
- ⭐⭐⭐ P5: Cost comparison: ระบบเดียวกันบน HCI on-prem vs cloud 3 ปี (รวมคน/ไฟ/พื้นที่)

---

## Level 80 — Capstone Cloud & HCI

**โจทย์:** บริษัทค้าปลีก มี VMware vSphere 3 host + SAN อายุ 7 ปี (VM 150 ตัว, 40 TB) license กำลังหมด ต้องการย้ายไป HCI on-prem สำหรับระบบหลัก และย้ายเว็บขายของออนไลน์ + DR ไป cloud **โดย downtime ของแต่ละระบบไม่เกิน 30 นาที**

**แบบทดสอบ (Self-review)**
1. ทุก VM มี 7R decision และอยู่ใน move group ที่ถูกต้องตาม dependency หรือยัง
2. HCI ที่ size ไว้รองรับ N+1, rebuild และ growth 3 ปีหรือไม่
3. Cutover runbook ทดสอบแล้วใน pilot wave และ downtime ≤ 30 นาทีจริงหรือไม่
4. มี rollback ทุก wave และไม่ลบต้นทางก่อน acceptance ใช่หรือไม่
5. หลังย้าย monitoring/backup/DR พร้อมส่งต่อทีม Support 24x7 หรือไม่

**5 โปรเจค**
- ⭐⭐⭐ P1: Assessment + 7R + dependency + wave plan
- ⭐⭐⭐ P2: HCI design + sizing + network + BOM (2 ทางเลือก vendor)
- ⭐⭐⭐ P3: Cloud landing zone + hybrid connectivity + DR design
- ⭐⭐⭐ P4: Lab migration: ESXi → Nutanix CE/Proxmox (Move/import) + 1 VM → cloud พร้อมวัด downtime
- ⭐⭐⭐ P5: Handover: as-built, runbook, monitoring, backup/DR test, cost report
