# Part 3 — Cybersecurity & Zero Trust · HCI · Enterprise Virtualization · Cloud & Hybrid Migration (Level 44–73)

> ตามขอบเขตงาน ISC:
> - **Cybersecurity & Zero Trust:** NGFW (Fortinet, Palo Alto) + IPS/IDS + DPI + SSL/TLS Inspection, ZTNA & Least Privilege ข้ามสาขา, EDR + Active Threat Hunting, Vulnerability Assessment & Hardening, ระบบเฝ้าระวังภัยคุกคาม, ISO/IEC 27001
> - **HCI:** Software-Defined Storage & Compute, Linear Scale-Out, Single-Pane Administration, ลด TCO
> - **Enterprise Virtualization:** VMware vSphere, Microsoft Hyper-V, KVM พร้อม HA และ Live Migration
> - **Cloud & Hybrid Migration:** Hybrid Architecture + VPN/Direct Connect, Workload Assessment, Zero-Downtime Migration, FinOps, Kubernetes & Microservices

## Level ที่ใช้เนื้อหาเดิม

| Level | หัวข้อ | เรียนจาก | ISC Checkpoint |
|---|---|---|---|
| 44 | Security fundamentals, กฎหมาย, ISO 27001 | [SI L41](../SI-Track/03-security-a.md), [SI L58](../SI-Track/04-security-b.md) | Map control ใน ISO/IEC 27001 Annex A กับงานที่ ISC ติดตั้ง |
| 45 | NGFW concepts & sizing | [SI L42](../SI-Track/03-security-a.md) | Size FortiGate/Palo Alto จาก threat protection throughput + SSL |
| 46 | FortiGate hands-on | [SI L43](../SI-Track/03-security-a.md) | ตรงกับคุณสมบัติตำแหน่ง Network & Security Engineer (Fortinet NSE → FCP Network Security) |
| 47 | Palo Alto hands-on | [SI L44](../SI-Track/03-security-a.md) | ทำ App-ID/User-ID policy และ HA |
| 48 | Firewall HA, upgrade & migration | [SI L45](../SI-Track/03-security-a.md) | Migrate firewall เก่าของลูกค้าภาครัฐโดยไม่กระทบบริการ |
| 49 | IPS/IDS, DPI, SSL/TLS inspection | [SI L46](../SI-Track/03-security-a.md), [Roadmap L64](../07-security.md) | เปิด SSL inspection พร้อมรายการยกเว้น (ธนาคาร/สุขภาพ) ตาม PDPA |
| 50 | ZTNA & least-privilege policy ข้ามสาขา | [SI L47–L48](../SI-Track/03-security-a.md) | ย้ายผู้ใช้จาก SSL VPN ไป ZTNA/IPsec + MFA |
| 51 | Zero Trust Segmentation & NAC | [SI L49–L50](../SI-Track/03-security-a.md) | Ringfence AD, backup, database จาก lateral movement |
| 52 | EDR & Active Threat Hunting | [SI L51](../SI-Track/04-security-b.md), [SI L54](../SI-Track/04-security-b.md) | Deploy EDR + เขียน hunting hypothesis 3 ข้อ |
| 53 | SIEM, NDR & threat monitoring | [SI L53](../SI-Track/04-security-b.md), [SI L55](../SI-Track/04-security-b.md) | ส่ง log FortiGate/PA/AD/EDR เข้า SIEM เก็บ ≥ 90 วัน |
| 54 | Vulnerability assessment & hardening | [SI L56](../SI-Track/04-security-b.md), [SI L58](../SI-Track/04-security-b.md) | ทำ VA ด้วย Nessus + hardening ตาม CIS แล้วออกรายงาน |
| 55 | Incident response & ransomware | [SI L57](../SI-Track/04-security-b.md), [SI L59](../SI-Track/04-security-b.md) | Ransomware playbook: Zero Trust + Immutable Backup (ตามบทความ ISC) |
| 57 | HCI concepts (3-tier → HCI) | [SI L62](../SI-Track/05-cloud-hci-a.md) | อธิบายให้ผู้บริหารเห็นว่า HCI ลด TCO อย่างไร พร้อมตัวเลขจริง |
| 58 | HCI platforms (Nutanix, vSAN, Azure Local, Proxmox/Ceph) | [SI L63–L65](../SI-Track/05-cloud-hci-a.md) | ติดตั้ง HCI อย่างน้อย 1 platform ใน lab |
| 59 | HCI sizing & design | [SI L66](../SI-Track/05-cloud-hci-a.md) | Size N+1 + rebuild + growth จากข้อมูลลูกค้า |
| 60 | HCI network design | [SI L67](../SI-Track/05-cloud-hci-a.md) | ToR คู่ 25G + VLAN/MTU สำหรับ HCI |
| 61 | HCI deployment & lifecycle | [SI L68](../SI-Track/05-cloud-hci-a.md) | Rolling upgrade และเพิ่ม node โดยไม่มี downtime |
| 63 | Hypervisor landscape | [SI L61](../SI-Track/05-cloud-hci-a.md) | เปรียบเทียบ vSphere/Hyper-V/KVM สำหรับลูกค้าที่จะต่อ license VMware |
| 67 | Cloud fundamentals & data residency | [SI L69](../SI-Track/05-cloud-hci-a.md) | เลือก region/ผู้ให้บริการตาม PDPA และงบ |
| 68 | AWS & Azure core | [SI L70](../SI-Track/05-cloud-hci-a.md) | สร้าง VPC/VNet + VM + IAM ตามมาตรฐาน |
| 69 | Hybrid architecture, VPN & Direct Connect/ExpressRoute | [SI L71](../SI-Track/06-cloud-hci-b.md) | ต่อ DC ลูกค้ากับ cloud ด้วย BGP + redundancy |
| 70 | Workload assessment & migration strategy | [SI L72](../SI-Track/06-cloud-hci-b.md) | จัด 7R + dependency + wave plan |
| 71 | Zero-downtime migration (tools & cutover) | [SI L73–L74](../SI-Track/06-cloud-hci-b.md) | Cutover runbook ที่ downtime วัดได้จริง + rollback |
| 72 | FinOps, governance & Kubernetes | [SI L76](../SI-Track/06-cloud-hci-b.md), [SI L78](../SI-Track/06-cloud-hci-b.md) | Cost report รายเดือน + deploy microservices บน K8s |
| 73 | Capstone Cloud & HCI migration | [SI L80](../SI-Track/06-cloud-hci-b.md) | ใช้โจทย์ PFO-VIRT-02 (ดู L62) ต่อยอดไป cloud |

---

## Level 56 — Capstone Cybersecurity (อ้างอิง PFO-SEC-03)

**โจทย์:** กลุ่มบริษัทการเงินและประกันภัย (สำนักงานใหญ่ + 15 สาขา + DC/DR) ต้องการ NGFW ใหม่, Zero Trust Architecture และระบบเฝ้าระวังภัยคุกคาม ตามมาตรฐาน ISO/IEC 27001 และแนวปฏิบัติของหน่วยงานกำกับ (คปภ./ธปท.)

**แบบทดสอบ (Self-review)**
1. NGFW policy ใช้ App-ID/User-ID, IPS, SSL inspection (มีรายการยกเว้น) และไม่มี any-any หรือไม่
2. ผู้ใช้สาขา/remote เข้าถึงระบบผ่าน ZTNA + MFA แบบ least privilege หรือไม่
3. Segmentation ป้องกัน lateral movement ไป core insurance system, AD และ backup ได้หรือไม่
4. Log ครบ เก็บ ≥ 90 วัน มี use case และ playbook ที่ทดสอบแล้วหรือไม่
5. มีหลักฐานสำหรับ ISO 27001 audit (policy, review, test result) ครบหรือไม่

**5 โปรเจค**
- ⭐⭐⭐ P1: Security assessment + gap analysis ตาม ISO 27001 + Zero Trust roadmap
- ⭐⭐⭐ P2: NGFW design (HQ/สาขา/DC) + HA + migration plan + test matrix
- ⭐⭐⭐ P3: ZTNA + segmentation design + lab demo
- ⭐⭐⭐ P4: Threat monitoring: SIEM + EDR + use case 15 ข้อ + playbook
- ⭐⭐⭐ P5: Executive report + audit evidence package

---

## Level 62 — Capstone HCI (อ้างอิง PFO-VIRT-02)

**โจทย์:** ท่าเรือ/บริษัทโลจิสติกส์ มี server 3 เครื่อง + SAN อายุ 8 ปี (VM 120 ตัว ระบบท่าเรือทำงาน 24x7) ต้องการเปลี่ยนเป็น HCI ลดค่าดูแลรักษา และเพิ่มความเร็วในการขยายระบบ

**แบบทดสอบ (Self-review)**
1. Sizing รองรับ N+1, rebuild และ growth 3–5 ปีหรือไม่
2. TCO 5 ปี เทียบระบบเดิมได้ตัวเลขเท่าไร (ระบุ assumption ชัดเจน ไม่ใช้ตัวเลขการตลาดอย่างเดียว)
3. Migration ระบบท่าเรือ 24x7 มี downtime เท่าไร ทำในช่วงไหน
4. Network ToR/VLAN/MTU ทดสอบแล้วหรือไม่
5. ทีม support รับต่อด้วย monitoring/runbook ได้ทันทีหรือไม่

**5 โปรเจค**
- ⭐⭐⭐ P1: Assessment (RVTools/Collector) + sizing + TCO 5 ปี
- ⭐⭐⭐ P2: HCI design (node, network, data protection, backup)
- ⭐⭐⭐ P3: Lab: HCI 3 node (Nutanix CE หรือ Proxmox/Ceph) + migrate VM จาก ESXi
- ⭐⭐⭐ P4: Migration runbook + วัด downtime จริง
- ⭐⭐⭐ P5: Handover + ROI report ฉบับผู้บริหาร

---

## Level 64 — Microsoft Hyper-V Enterprise

**สิ่งที่ต้องรู้**
- Hyper-V role บน Windows Server, Gen1/Gen2 VM, Integration Services, dynamic memory, checkpoint (production vs standard)
- Failover Cluster + Cluster Shared Volume (CSV), quorum/witness, Cluster-Aware Updating (CAU)
- Live Migration (Kerberos/CredSSP, SMB Direct), Storage Live Migration, Hyper-V Replica (async DR)
- Networking: Hyper-V virtual switch (external/internal/private), SET (Switch Embedded Teaming), VLAN per vNIC
- Management: Windows Admin Center, Failover Cluster Manager, SCVMM, PowerShell (`Get-VM`, `Move-VM`, `Test-Cluster`)
- License: Windows Server Datacenter (VM ไม่จำกัด) vs Standard

**แบบทดสอบ**
1. CSV ช่วยอะไรใน Hyper-V cluster
2. Production checkpoint ต่างจาก standard checkpoint อย่างไร
3. Hyper-V Replica เหมาะกับงานแบบไหน
4. SET ต่างจาก NIC teaming แบบเดิม (LBFO) อย่างไร
5. ทำไมต้องรัน `Test-Cluster` ก่อนสร้าง cluster

<details><summary>เฉลย</summary>

1. ทุก node เข้าถึง volume เดียวกันพร้อมกัน ทำให้ live migration ไม่ต้องย้าย storage
2. Production ใช้ VSS ใน guest (application-consistent); Standard เก็บ state memory ด้วย (ไม่เหมาะกับ production DB)
3. DR แบบ async ราคาประหยัดระหว่าง site หรือ host (RPO 30 วินาที – 15 นาที)
4. SET อยู่ใน Hyper-V switch โดยตรง รองรับ RDMA/SDN และเป็นแนวทางที่ Microsoft แนะนำสำหรับ Hyper-V
5. ตรวจ hardware, network, storage, config ว่าพร้อมและได้รับการรองรับก่อนสร้าง
</details>

**5 โปรเจค**
- ⭐⭐ P1: Hyper-V 2 node (nested) + iSCSI (จาก TrueNAS) + Failover Cluster + CSV
- ⭐⭐ P2: Live Migration + Storage Live Migration แล้ววัดเวลาที่ VM ไม่ตอบสนอง
- ⭐⭐ P3: Hyper-V Replica ไป host ที่ 3 + test failover
- ⭐⭐ P4: PowerShell report: VM, checkpoint เก่า, CSV ที่ใช้เกิน 80%
- ⭐⭐⭐ P5: Hyper-V build standard + Cluster-Aware Updating runbook

---

## Level 65 — KVM-based Virtualization (Proxmox VE, libvirt, oVirt/OLVM)

**สิ่งที่ต้องรู้**
- KVM + QEMU, libvirt (`virsh`, virt-manager), VirtIO drivers, qcow2 vs raw
- Proxmox VE: cluster (corosync), HA manager, storage (LVM-thin, ZFS, Ceph, NFS/iSCSI), backup (Proxmox Backup Server), SDN
- Enterprise KVM อื่น: Oracle Linux Virtualization Manager (oVirt), OpenShift Virtualization, Nutanix AHV
- Live migration (shared storage หรือ local + migrate disk), cluster quorum (≥ 3 node หรือ QDevice)
- Linux bridge / OVS, VLAN-aware bridge, bond

**แบบทดสอบ**
1. qcow2 ต่างจาก raw อย่างไร
2. ทำไม Proxmox cluster 2 node ต้องมี QDevice
3. Proxmox Backup Server เพิ่มอะไรจาก vzdump ปกติ
4. Live migration กับ local storage ทำได้อย่างไร
5. VirtIO driver สำคัญกับ Windows guest อย่างไร

<details><summary>เฉลย</summary>

1. qcow2 รองรับ snapshot/thin/compression แต่ overhead มากกว่า; raw เร็วกว่า เรียบง่าย
2. รักษา quorum เมื่อ node หนึ่งล่ม (ไม่เช่นนั้นเหลือ 1 ใน 2 เสียง cluster จะหยุด)
3. Incremental + deduplication, verify, encryption, sync ไป remote
4. Migrate disk ไปพร้อมกัน (storage migration) ใช้เวลานานกว่า
5. Windows ไม่มี driver VirtIO ในตัว ต้องติดตั้งเพื่อให้มองเห็นดิสก์/NIC และได้ performance
</details>

**5 โปรเจค**
- ⭐⭐ P1: Proxmox 3 node cluster + Ceph + HA (ต่อยอด SI L65)
- ⭐⭐ P2: libvirt บน Ubuntu: สร้าง VM ด้วย `virt-install`, bridge, snapshot, live migrate ด้วย `virsh migrate`
- ⭐⭐ P3: Proxmox Backup Server + restore + verify job
- ⭐⭐ P4: Migrate VM Windows จาก ESXi → Proxmox (ติดตั้ง VirtIO) แล้วบันทึกปัญหาที่เจอ
- ⭐⭐⭐ P5: เอกสารเปรียบเทียบ vSphere/Hyper-V/Proxmox ด้าน HA, live migration, backup ecosystem, license สำหรับลูกค้า

---

## Level 66 — Virtualization Performance & Troubleshooting (vSphere / Hyper-V / KVM)

**สิ่งที่ต้องรู้**
- CPU: ready time/co-stop (vSphere), oversize vCPU, NUMA; Hyper-V: `\Hyper-V Hypervisor Logical Processor\% Total Run Time`; KVM: `top`/steal time
- Memory: ballooning, swapping, compression; ห้าม overcommit สำหรับ DB
- Storage: latency (device/kernel/guest), queue depth, snapshot chain ยาว, datastore/CSV เต็ม
- Network: vNIC driver, dropped packets, teaming ผิด, MTU
- เครื่องมือ: esxtop, vCenter perf charts, Performance Monitor + WAC, `virsh domstats`, `iostat`, `sar`
- Methodology: วัด baseline, เทียบ host/guest, หา resource ที่เป็นคอขวด

**แบบทดสอบ**
1. CPU ready สูงหมายความว่าอะไร แก้อย่างไร
2. VM ได้ vCPU มากเกินจำเป็นมีผลเสียอย่างไร
3. Storage latency สูงที่ device แต่ไม่สูงที่ kernel บอกอะไร
4. ทำไม snapshot chain ยาวทำให้ช้า
5. Guest ใช้ CPU 100% แต่ host ว่าง สงสัยอะไร

<details><summary>เฉลย</summary>

1. VM พร้อมทำงานแต่รอ physical CPU — ลด vCPU ที่เกิน, ลด overcommit, ย้าย VM/เพิ่ม host
2. Scheduling ยากขึ้น (ready/co-stop สูง) ทำให้ช้ากว่าเดิม
3. คอขวดอยู่ที่ storage array/fabric ไม่ใช่ที่ hypervisor
4. ทุกการอ่านต้องไล่หลาย delta file และ delta โตเรื่อย ๆ
5. ปัญหาภายใน guest (process/app), หรือ vCPU ถูกจำกัดด้วย limit/ไม่พอ
</details>

**5 โปรเจค**
- ⭐⭐ P1: Cheat sheet metric + ค่าเกณฑ์ผิดปกติ ของทั้ง 3 hypervisor
- ⭐⭐ P2: Lab: สร้าง CPU contention (VM vCPU เกิน) แล้ววัด ready time ก่อน/หลังแก้
- ⭐⭐ P3: Lab: snapshot chain ยาว → วัด IO → consolidate
- ⭐⭐ P4: สคริปต์ (PowerCLI/PowerShell/Python) หา VM oversize/undersize จาก metric 7 วัน
- ⭐⭐⭐ P5: Performance health-check report ฉบับส่งลูกค้า (findings + rightsizing)
