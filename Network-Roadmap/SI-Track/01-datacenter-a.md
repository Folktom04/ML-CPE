# Part 1 — วางระบบศูนย์ข้อมูล (Data Center) ตอน A: Server & Storage (Level 21–30)

> ตามบริการ: **ออกแบบโครงสร้างพื้นฐาน Server, Storage SAN, High-Availability Cluster**

---

## Level 21 — พื้นฐาน Data Center: มาตรฐาน, ไฟ, ความเย็น, Rack

**สิ่งที่ต้องรู้**
- Uptime Institute Tier I–IV: Tier III = Concurrently Maintainable (~99.982%), Tier IV = Fault Tolerant (~99.995%); มาตรฐาน TIA-942
- ไฟ: UPS (online double-conversion), PDU/rPDU, A+B feed, generator, ATS, N / N+1 / 2N
- ความเย็น: hot aisle / cold aisle containment, CRAC/CRAH, in-row cooling, PUE = พลังงานทั้งหมด / พลังงาน IT
- Rack: 42U/48U, ความลึก, น้ำหนัก, kW ต่อ rack, cable management, labeling
- Physical security: access control, CCTV, ระบบดับเพลิง (FM-200/Novec)

**แบบทดสอบ**
1. Tier III ต่างจาก Tier IV อย่างไร
2. PUE 1.5 หมายความว่าอะไร
3. ทำไม server ต้องมี PSU 2 ตัว ต่อ PDU คนละ feed
4. ข้อดีของ hot/cold aisle containment
5. Server 10 เครื่อง เครื่องละ 600 W ต้องใช้ UPS อย่างน้อยกี่ kW (เผื่อ 25%)

<details><summary>เฉลย</summary>

1. Tier III ซ่อมบำรุงได้โดยไม่ต้องปิดระบบ (มีเส้นทางสำรอง); Tier IV ทนความเสียหายจุดเดียวได้โดยอัตโนมัติ (2N เต็มรูปแบบ)
2. ใช้พลังงานรวมเป็น 1.5 เท่าของพลังงานอุปกรณ์ IT (อีก 0.5 ไปกับความเย็น ไฟ และการสูญเสีย)
3. ถ้า feed หรือ PDU ใดเสีย server ยังทำงานต่อได้
4. ไม่ให้ลมร้อนกับลมเย็นผสมกัน ระบายความร้อนได้มีประสิทธิภาพขึ้น ลด PUE
5. 6 kW × 1.25 = 7.5 kW
</details>

**5 โปรเจค**
- ⭐ P1: วาด floor plan ห้อง server 4 rack (hot/cold aisle, UPS, PDU, ทางเดินสาย)
- ⭐ P2: Rack elevation diagram (draw.io/NetBox) ของ rack ที่มี server, storage, switch และ patch panel
- ⭐⭐ P3: Power budget spreadsheet: อุปกรณ์ทุกชิ้น (W, BTU/hr), UPS runtime และการแบ่ง A/B feed
- ⭐⭐ P4: Checklist สำรวจหน้างาน (site survey) ห้อง server ลูกค้าก่อนเสนอราคา
- ⭐⭐ P5: เปรียบเทียบ colocation ในไทย 3 แห่ง (Tier, ราคา/rack, carrier neutral)

---

## Level 22 — Server Hardware

**สิ่งที่ต้องรู้**
- รุ่นหลัก: Dell PowerEdge, HPE ProLiant, Lenovo ThinkSystem, Cisco UCS, Supermicro
- CPU (socket, core, NUMA), RAM (channel, DIMM population, ECC), local disk (SAS/SATA/NVMe, BOSS/boot), RAID controller (PERC/Smart Array), NIC (1/10/25/100G, OCP), HBA (FC)
- Out-of-band management: iDRAC, iLO, XClarity (XCC), CIMC; protocol Redfish/IPMI
- Firmware/BIOS/driver ต้องตรงกับ compatibility matrix (VMware HCL, Nutanix HCL)
- Warranty/support: ProSupport, HPE Foundation Care, NBD vs 4-hour

**แบบทดสอบ**
1. iDRAC/iLO ใช้ทำอะไร และทำไมต้องอยู่ VLAN แยก
2. ทำไมต้องใส่ DIMM ให้ครบทุก channel
3. HCL คืออะไร
4. BOSS card (Dell) ใช้ทำอะไร
5. Warranty 4-hour vs NBD เลือกอย่างไร

<details><summary>เฉลย</summary>

1. จัดการ server จากระยะไกล (console, power, ดู hardware log, ติดตั้ง OS) แยก VLAN เพื่อความปลอดภัยและให้ยังเข้าถึงได้แม้ OS ล่ม
2. ได้ memory bandwidth สูงสุด และ balance ตาม NUMA
3. Hardware Compatibility List: รายการ hardware/firmware ที่ vendor software รองรับ
4. Boot device แบบ M.2 RAID1 สำหรับ hypervisor (แยกจาก data disk)
5. ระบบ production สำคัญใช้ 4-hour ระบบทั่วไปใช้ NBD ได้ โดยพิจารณาจาก SLA ที่ให้ลูกค้า
</details>

**5 โปรเจค**
- ⭐ P1: ตั้งค่า iDRAC/iLO (หรือใช้ simulator/demo) ได้แก่ IP, user, alert email/SNMP
- ⭐⭐ P2: Spec sheet server 3 แบบ (web, DB, virtualization host) พร้อมเหตุผล
- ⭐⭐ P3: Python + Redfish API ดึง health, serial, firmware ของ server (ใช้ DMTF Redfish mockup server)
- ⭐⭐ P4: Checklist ติดตั้ง server ใหม่ (unbox → rack → cable → firmware update → RAID → OS → monitoring)
- ⭐⭐⭐ P5: เทียบ TCO 5 ปีของ server 2 ยี่ห้อ (ราคา, warranty, ไฟ, license)

---

## Level 23 — Server OS & Workload Sizing

**สิ่งที่ต้องรู้**
- Windows Server (AD, DNS, DHCP, File, Hyper-V), Linux (RHEL, Ubuntu, Rocky)
- Sizing: vCPU:pCPU ratio (เช่น 4:1 สำหรับงานทั่วไป), RAM (ไม่ควร overcommit มาก), IOPS, throughput, capacity + growth
- เก็บข้อมูลจากของเดิม: RVTools, Dell Live Optics, perfmon, sar/iostat
- Peak vs average, 95th percentile, N+1 สำหรับ host
- License: Windows Server Datacenter/Standard นับตาม core, SQL Server per core

**แบบทดสอบ**
1. ลูกค้ามี VM รวม 400 vCPU ใช้ ratio 4:1 ต้องมี physical core เท่าไร
2. ทำไมต้อง size ตาม peak ไม่ใช่ average
3. RVTools ใช้ทำอะไร
4. N+1 ใน cluster หมายความว่าอะไร
5. Windows Server Standard กับ Datacenter ต่างกันเรื่อง virtualization อย่างไร

<details><summary>เฉลย</summary>

1. 100 core (บวกเผื่อ N+1 และการเติบโต)
2. ถ้า size ตาม average ช่วง peak (ปิดงบ, เปิดเทอม) ระบบจะไม่พอ
3. Export inventory ของ vSphere (VM, vCPU, RAM, disk, datastore) เพื่อใช้ sizing และ migration
4. ถ้า host ใดเสีย 1 เครื่อง host ที่เหลือยังรับโหลดทั้งหมดได้
5. Standard ได้สิทธิ์ 2 VM ต่อชุด license; Datacenter ได้ VM ไม่จำกัดบน host ที่ license ครบ core
</details>

**5 โปรเจค**
- ⭐ P1: ติดตั้ง Windows Server lab (AD + DNS) และ Linux server (SSH, firewall)
- ⭐⭐ P2: ใช้ RVTools กับ vCenter lab (หรือไฟล์ตัวอย่าง) สรุป VM inventory ด้วย Excel pivot
- ⭐⭐ P3: Sizing calculator (Excel/Python) ที่รับ VM list แล้วคำนวณจำนวน host, core, RAM และ storage (N+1, growth 3 ปี)
- ⭐⭐ P4: วัด IOPS/latency ของ disk ด้วย fio/diskspd แล้วทำรายงาน
- ⭐⭐⭐ P5: ทำเอกสาร sizing proposal ให้ลูกค้าสมมติ 150 VM พร้อม assumptions และ BOM

---

## Level 24 — Storage Fundamentals

**สิ่งที่ต้องรู้**
- DAS / NAS (file: NFS, SMB) / SAN (block: FC, iSCSI, NVMe-oF) / Object (S3)
- RAID 0/1/5/6/10, write penalty (RAID5 = 4, RAID6 = 6, RAID10 = 2), hot spare, rebuild time
- Metric: IOPS, throughput (MB/s), latency (ms/µs), block size, read/write ratio
- Media: HDD (7.2k/10k), SAS SSD, NVMe; tiering, caching
- Thin vs thick provisioning, snapshot ≠ backup, dedupe/compression

**แบบทดสอบ**
1. Block กับ File storage ต่างกันอย่างไร ยกตัวอย่างการใช้
2. Frontend 10,000 IOPS, write 30%, RAID5 ต้องได้ backend IOPS เท่าไร
3. ทำไมดิสก์ขนาดใหญ่ไม่ควรใช้ RAID5
4. ความเสี่ยงของ thin provisioning
5. ทำไม snapshot ไม่ใช่ backup

<details><summary>เฉลย</summary>

1. Block = OS เห็นเป็นดิสก์ (DB, VMFS datastore); File = แชร์เป็นไฟล์ผ่านเครือข่าย (file share, NFS datastore)
2. Read 7,000 + Write 3,000 × 4 = 19,000 IOPS
3. Rebuild นาน มีโอกาสดิสก์ตัวที่ 2 เสียหรือเจอ URE ระหว่าง rebuild จนข้อมูลหาย ควรใช้ RAID6/10
4. Overcommit แล้ว pool เต็มจริง ทำให้ VM ทุกตัวหยุดเขียนได้ จึงต้อง monitor และตั้ง alert
5. อยู่บนอุปกรณ์เดียวกัน ถ้า array เสียหรือโดน ransomware ก็หายไปด้วย
</details>

**5 โปรเจค**
- ⭐ P1: ตาราง RAID level (ขนาดใช้ได้, write penalty, ทนดิสก์เสียกี่ลูก, ใช้กับงานไหน)
- ⭐⭐ P2: Linux mdadm ทำ RAID1/5 บน VM แล้วจำลองดิสก์เสียและ rebuild
- ⭐⭐ P3: ตั้ง TrueNAS lab ให้บริการ NFS, SMB และ iSCSI
- ⭐⭐ P4: RAID/IOPS calculator (Python/Excel)
- ⭐⭐⭐ P5: Benchmark NFS vs iSCSI บน TrueNAS ด้วย fio (4k random, 64k seq) พร้อมรายงาน

---

## Level 25 — SAN: Fibre Channel

**สิ่งที่ต้องรู้**
- FC speed 16/32/64G, HBA, WWNN/WWPN, FC switch (Brocade, Cisco MDS)
- Fabric A / Fabric B แยกกันสมบูรณ์ (ไม่เชื่อมกัน)
- Zoning: single-initiator, single-target (หรือ peer zoning), alias, zoneset/config activate
- LUN masking / host group บน storage
- Multipathing: MPIO, ALUA, Round Robin (VMware NMP), PowerPath
- ปัญหาบ่อย: zoning ผิด, path down, slow drain, SFP เสีย

**แบบทดสอบ**
1. ทำไมต้องมี Fabric A/B แยกกัน
2. Single-initiator zoning คืออะไร
3. Zoning กับ LUN masking ต่างกันอย่างไร
4. Host เห็น LUN ซ้ำ 4 ตัว แปลว่าอะไร
5. ALUA คืออะไร

<details><summary>เฉลย</summary>

1. ให้มีเส้นทางสำรองที่ไม่มี failure ร่วมกัน (switch/config ผิดฝั่งหนึ่งไม่กระทบอีกฝั่ง)
2. แต่ละ zone มี initiator (HBA) แค่ 1 ตัว ลด RSCN และการรบกวนกัน
3. Zoning ควบคุมที่ FC switch ว่าใครเห็นใคร; LUN masking ควบคุมที่ storage ว่า host ไหนเห็น LUN ไหน
4. ไม่ได้เปิด multipathing (เห็นทีละ path)
5. Asymmetric Logical Unit Access: บอก host ว่า path ไหนเป็น optimized (controller เจ้าของ LUN)
</details>

**5 โปรเจค**
- ⭐⭐ P1: ออกแบบ SAN diagram (2 host, 2 FC switch, storage 2 controller) พร้อมตาราง WWPN และ zone
- ⭐⭐ P2: เขียนคำสั่ง zoning ของ Brocade (`alicreate`, `zonecreate`, `cfgadd`, `cfgenable`) และ Cisco MDS จากตาราง P1
- ⭐⭐ P3: สคริปต์ Python สร้างคำสั่ง zoning อัตโนมัติจาก CSV (WWPN, alias)
- ⭐⭐ P4: Runbook "เพิ่ม host ใหม่เข้า SAN" ตั้งแต่ต้นจนจบ
- ⭐⭐⭐ P5: Troubleshooting guide: path down, slow drain, CRC error พร้อมคำสั่งตรวจ (`porterrshow`, `esxcli storage core path list`)

---

## Level 26 — iSCSI, NVMe-oF & Storage Networking

**สิ่งที่ต้องรู้**
- iSCSI: initiator/target, IQN, portal, CHAP, port binding (VMware)
- Network design: VLAN/subnet แยก, jumbo frame 9000 end-to-end, ไม่ route, ไม่ใช้ LACP กับ iSCSI (ใช้ MPIO แทน), flow control
- NFS v3/v4.1 สำหรับ datastore, SMB3 (Hyper-V/SOFS)
- NVMe-oF (NVMe/TCP, NVMe/RoCE, NVMe/FC): latency ต่ำมาก
- DCB/PFC สำหรับ RoCE

**แบบทดสอบ**
1. ทำไม iSCSI ใช้ MPIO แทน LACP
2. ตรวจว่า jumbo frame ทำงาน end-to-end บน ESXi อย่างไร
3. IQN คืออะไร
4. ทำไม storage network ไม่ควร route ผ่าน firewall
5. NVMe/TCP ดีกว่า iSCSI อย่างไร

<details><summary>เฉลย</summary>

1. MPIO รู้จักแต่ละ path ใน storage stack ทำ failover/load balance ได้ดีกว่า; LACP hash session เดียวลง link เดียว
2. `vmkping -I vmk1 -d -s 8972 <target-ip>` (-d = don't fragment)
3. iSCSI Qualified Name: ชื่อเฉพาะของ initiator/target
4. เพิ่ม latency, firewall เป็น bottleneck/จุดเสีย, session หลุดตอน failover
5. Protocol ออกแบบมาสำหรับ flash, queue จำนวนมาก, overhead ต่ำ ทำให้ latency ต่ำกว่า
</details>

**5 โปรเจค**
- ⭐⭐ P1: TrueNAS iSCSI target + Windows/Linux initiator + MPIO 2 path
- ⭐⭐ P2: ESXi (nested lab) software iSCSI + port binding + Round Robin
- ⭐⭐ P3: ทดสอบ jumbo frame ไม่ตรงกัน (switch 1500) ดูอาการแล้วแก้
- ⭐⭐ P4: Storage network design doc (VLAN, IP, MTU, switch config) สำหรับ cluster 4 node
- ⭐⭐⭐ P5: Lab NVMe/TCP บน Linux (nvmet) เทียบ latency กับ iSCSI

---

## Level 27 — Enterprise Storage Arrays

**สิ่งที่ต้องรู้**
- Vendor: Dell PowerStore/PowerMax/Unity, NetApp ONTAP (AFF/FAS), HPE Alletra/Primera, Pure Storage FlashArray, Huawei OceanStor
- Concept: pool, volume/LUN, host group, QoS, data reduction (dedupe + compression)
- Snapshot (redirect-on-write), clone, replication sync/async, metro cluster (active-active)
- Unified storage (block + file), SVM (NetApp)
- Non-disruptive upgrade (NDU), controller failover

**แบบทดสอบ**
1. Sync กับ Async replication ต่างกันอย่างไร
2. Metro cluster / stretched storage ใช้ทำอะไร
3. Data reduction ratio 4:1 หมายความว่าอะไร และควรใช้ตัวเลขนี้ตอน sizing หรือไม่
4. ทำไมต้องตั้ง QoS ใน storage
5. ข้อควรตรวจก่อน upgrade firmware storage

<details><summary>เฉลย</summary>

1. Sync ยืนยันการเขียนเมื่อทั้งสองฝั่งเขียนเสร็จ (RPO=0, ต้อง latency ต่ำ/ระยะใกล้); Async ส่งตามหลัง (RPO > 0, ระยะไกลได้)
2. ให้ข้อมูล active ทั้ง 2 site ทำ HA ข้าม site (เช่นกับ vSphere stretched cluster)
3. ข้อมูล 4 TB ใช้พื้นที่จริง 1 TB; ตอน sizing ควรใช้ค่าที่ vendor รับประกันหรือประเมินแบบระมัดระวัง (ข้อมูลที่เข้ารหัส/บีบอัดแล้วจะลดได้น้อย)
4. ป้องกัน noisy neighbor ที่ VM/LUN เดียวกิน IOPS ทั้งระบบ
5. Compatibility matrix (host/HBA/OS), health ทุก controller, path redundancy ของ host, backup config, release notes
</details>

**5 โปรเจค**
- ⭐⭐ P1: ทดลอง NetApp ONTAP Simulator หรือ demo/virtual lab ของ vendor สร้าง SVM, volume, LUN และ snapshot
- ⭐⭐ P2: ตารางเปรียบเทียบ storage 4 ยี่ห้อ (สถาปัตยกรรม, data reduction guarantee, replication, ราคา)
- ⭐⭐ P3: Snapshot/replication policy สำหรับลูกค้า (ระดับ tier ของข้อมูล, RPO)
- ⭐⭐ P4: Storage capacity report อัตโนมัติผ่าน REST API (ONTAP/PowerStore API หรือ TrueNAS API)
- ⭐⭐⭐ P5: Upgrade plan ของ storage array (pre-check, NDU steps, rollback, ประกาศลูกค้า)

---

## Level 28 — Server Virtualization: VMware vSphere

**สิ่งที่ต้องรู้**
- ESXi, vCenter (VCSA), datastore (VMFS/NFS/vSAN/vVols), VM hardware, VMware Tools
- Networking: vSS vs vDS, port group, VLAN, uplink teaming (route based on originating port, LBT, IP hash ใช้คู่กับ EtherChannel), VMkernel (mgmt, vMotion, storage, vSAN)
- Template, clone, content library, snapshot (ไม่ควรเก็บนาน)
- License หลัง Broadcom (ปี 2024 ขึ้นไป): ขายแบบ subscription (VCF/VVF) ทำให้ลูกค้าจำนวนมากพิจารณาย้ายไป Nutanix/Hyper-V/Proxmox (ดู Part 3)
- ทางเลือกอื่น: Microsoft Hyper-V, Proxmox VE, Nutanix AHV

**แบบทดสอบ**
1. vSS กับ vDS ต่างกันอย่างไร
2. ทำไม snapshot VM ไม่ควรเก็บไว้หลายวัน
3. VMkernel port ใช้ทำอะไร
4. IP hash teaming ต้องตั้ง switch อย่างไร
5. ทำไม Broadcom licensing ทำให้มีงาน migration มากขึ้น

<details><summary>เฉลย</summary>

1. vSS ตั้งแยกทีละ host; vDS จัดการจาก vCenter ศูนย์กลาง มี LBT, NetFlow, port mirroring
2. delta disk โตเรื่อย ๆ ทำให้ performance ตก, datastore เต็ม, consolidate นาน
3. Traffic ของ hypervisor เอง เช่น management, vMotion, iSCSI/NFS, vSAN, FT
4. Static EtherChannel (mode on) บน vSS (vDS รองรับ LACP)
5. ราคาเพิ่มและเปลี่ยนรูปแบบ license ลูกค้าจึงประเมินทางเลือกและย้าย platform
</details>

**5 โปรเจค**
- ⭐⭐ P1: Nested lab: ESXi 2–3 host + vCenter (ใช้ VMUG Advantage หรือ eval)
- ⭐⭐ P2: ตั้ง vDS + port group หลาย VLAN + VMkernel แยกตามหน้าที่
- ⭐⭐ P3: PowerCLI script รายงาน VM ที่มี snapshot เก่ากว่า 3 วัน และ datastore ที่ใช้ > 80%
- ⭐⭐ P4: Proxmox VE cluster 3 node (ทางเลือก open-source) เปรียบเทียบกับ vSphere
- ⭐⭐⭐ P5: Build guide มาตรฐานของ host/cluster (naming, network, storage, security hardening)

---

## Level 29 — High-Availability Cluster

**สิ่งที่ต้องรู้**
- vSphere HA (restart VM เมื่อ host ล่ม), admission control, heartbeat datastore, isolation response
- DRS (balance โหลด), vMotion / Storage vMotion, Fault Tolerance (FT)
- Windows Server Failover Clustering (WSFC): quorum (node majority, file share witness, cloud witness), CSV
- Linux: Pacemaker + Corosync, STONITH/fencing
- Split-brain และการป้องกัน: quorum, witness, fencing
- Anti-affinity rule (DC1/DC2 ห้ามอยู่ host เดียวกัน)

**แบบทดสอบ**
1. vSphere HA ต่างจาก FT อย่างไร
2. Quorum ใช้ป้องกันอะไร
3. Cluster 2 node ต้องมีอะไรเพิ่ม
4. Admission control คืออะไร
5. ยกตัวอย่างที่ต้องใช้ anti-affinity rule

<details><summary>เฉลย</summary>

1. HA restart VM บน host อื่น (downtime เป็นนาที); FT มี VM สำรองทำงานคู่กันตลอด (ไม่มี downtime)
2. Split-brain (สองฝั่งคิดว่าตัวเองเป็น primary แล้วเขียนข้อมูลชนกัน)
3. Witness (file share/cloud/disk) เป็นเสียงที่ 3
4. สงวน resource ไว้ให้ VM restart ได้เมื่อ host เสีย
5. Domain controller 2 ตัว, node ของ DB cluster, firewall VM คู่ HA
</details>

**5 โปรเจค**
- ⭐⭐ P1: vSphere HA/DRS lab แล้วปิด host ทดลอง จับเวลา VM restart
- ⭐⭐ P2: WSFC 2 node + file share witness + clustered file server
- ⭐⭐⭐ P3: Pacemaker cluster (VIP + Nginx) + fencing ใน lab
- ⭐⭐ P4: ทดสอบ split-brain scenario (ตัด heartbeat) แล้วบันทึกพฤติกรรม
- ⭐⭐⭐ P5: HA test plan ฉบับส่งลูกค้า (20 test case: ดึงสาย, ปิด host, ปิด switch, ปิด controller storage)

---

## Level 30 — Application & Database High Availability

**สิ่งที่ต้องรู้**
- SQL Server Always On Availability Groups (listener, sync/async replica), Failover Cluster Instance
- Oracle RAC / Data Guard, PostgreSQL (Patroni, streaming replication), MySQL Group Replication/InnoDB Cluster
- Load balancer สำหรับ web/app tier (F5, Citrix ADC, HAProxy, FortiADC) + health check
- Stateless app, session ใน Redis/DB
- Active-active vs active-passive, RTO/RPO ของแต่ละ tier

**แบบทดสอบ**
1. AG listener ทำหน้าที่อะไร
2. FCI ต่างจาก AG อย่างไร
3. ทำไม app ที่เก็บ session ใน memory ทำ HA ยาก
4. Patroni ใช้อะไรเลือก primary
5. ระบบ 3 tier (LB-App-DB) ต้องทำ HA ที่จุดไหนบ้าง

<details><summary>เฉลย</summary>

1. ชื่อ/IP เดียวที่ app ใช้ ชี้ไป primary replica อัตโนมัติ
2. FCI ใช้ shared storage (instance ย้ายเครื่อง); AG ทำสำเนาข้อมูลไปหลายเครื่อง (ไม่ต้อง shared storage)
3. Failover แล้ว session หาย ผู้ใช้หลุด ต้องใช้ sticky session หรือย้าย session ไป store กลาง
4. DCS (etcd/Consul/ZooKeeper) ทำ leader election
5. ทุกชั้น: LB คู่, app ≥ 2 node, DB replication/cluster, network/storage ด้านล่าง
</details>

**5 โปรเจค**
- ⭐⭐ P1: PostgreSQL + Patroni + HAProxy 3 node (docker/VM) ทดลอง failover
- ⭐⭐ P2: SQL Server AG 2 node (Developer Edition) + listener
- ⭐⭐ P3: Web app 2 node + HAProxy + Redis session แล้วทดลองปิด node
- ⭐⭐ P4: วิเคราะห์ RTO/RPO ของระบบ 3 tier แล้วเสนอการปรับปรุง
- ⭐⭐⭐ P5: เอกสาร HA architecture ของระบบ ERP ลูกค้าสมมติ (diagram, failover flow, test plan)
