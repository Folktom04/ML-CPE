# บทเรียน Level 28 — ตั้ง Lab: Packet Tracer, GNS3, EVE-NG, Containerlab (ฉบับละเอียด)

> อ่านจบแล้วจะ: เลือกเครื่องมือ lab ให้เหมาะกับสิ่งที่จะเรียน · ติดตั้งและสร้าง lab แรกได้ · ใช้ FRRouting เป็น router ฟรี · สร้าง lab แบบ "topology เป็นโค้ด" ด้วย Containerlab · มีแนวปฏิบัติในการจัดการ lab

---

## 1. ทำไมต้องมี Lab

- **ฝึกโดยไม่เสี่ยง** ทำระบบจริงพัง
- **ทดสอบ change ก่อนลงระบบจริง** (เช่น ลอง config OSPF/firewall ใหม่)
- **จำลองปัญหา** เพื่อฝึก troubleshoot
- **เตรียมสอบ cert** (CCNA/CCNP ต้องลงมือทำ)
- **สร้าง portfolio** แสดงทักษะ

> 💡 Network engineer ที่เก่งมักมี "homelab" — ยิ่งพิมพ์ config เองบ่อยยิ่งจำได้

---

## 2. เปรียบเทียบเครื่องมือ

| เครื่องมือ | ประเภท | ข้อดี | ข้อจำกัด | เหมาะกับ |
|---|---|---|---|---|
| **Cisco Packet Tracer** | **Simulator** (จำลองพฤติกรรม) | ฟรี เบามาก ติดตั้งง่าย มี simulation mode ดู packet ทีละขั้น | ฟีเจอร์ไม่ครบเท่าของจริง มีแต่ Cisco | **CCNA, มือใหม่** |
| **GNS3** | **Emulator** (รัน OS จริงของอุปกรณ์) | ฟรี รัน image จริงหลายยี่ห้อ ต่อเข้า VM/เครือข่ายจริงได้ | ต้องมี image (ลิขสิทธิ์), กิน RAM | CCNP, multi-vendor |
| **EVE-NG** (Community ฟรี / Pro เสียเงิน) | Emulator บน Linux VM/bare metal | ใช้ผ่านเว็บ รองรับยี่ห้อมาก นิยมในองค์กร/ผู้สอน | ต้องการทรัพยากรมาก, image เอง | Security (FortiGate, Palo Alto), multi-vendor |
| **Cisco CML** (Modeling Labs) | Emulator ของ Cisco (มีรุ่นฟรีจำกัด node) | image Cisco ถูกกฎหมายมาให้ | เน้น Cisco | CCNP/CCIE |
| **Containerlab** | Lab ด้วย **container** | เร็ว เบา **topology เป็นไฟล์ YAML** เหมาะ automation/CI | อุปกรณ์ต้องมี container image (Arista cEOS, Nokia SR Linux, FRR, Cisco XRd) | DC fabric, BGP/EVPN, NetDevOps |
| **Linux netns + FRR** | ทำเองด้วย Linux | ฟรีสุด เบาสุด | ต้องเขียนสคริปต์เอง | เรียน routing พื้นฐาน |
| **Vendor Sandbox / Hands-on Labs** | Lab ออนไลน์ของ vendor | ไม่ต้องใช้เครื่องตัวเอง | จำกัดเวลา | Cisco DevNet Sandbox, VMware HOL, Fortinet/Palo Alto labs |

**Simulator vs Emulator**
- **Simulator** = โปรแกรมเลียนแบบพฤติกรรม (บางคำสั่ง/ฟีเจอร์ไม่มี หรือทำงานต่างจากของจริง)
- **Emulator** = รัน **ระบบปฏิบัติการจริง** ของอุปกรณ์ ใน VM/container (พฤติกรรมเหมือนของจริง)

---

## 3. ทรัพยากรที่ต้องใช้

| สิ่งที่รัน | RAM โดยประมาณต่อ node |
|---|---|
| Packet Tracer ทั้ง lab | < 1 GB |
| Cisco IOSv (router) | 512 MB – 1 GB |
| Cisco IOSvL2 (switch) | 768 MB – 1 GB |
| Cisco CSR1000v/Catalyst 8000v | 4 GB |
| FortiGate VM / Palo Alto VM | 2 – 7 GB |
| Arista cEOS (container) | ~1–1.5 GB |
| FRR (container) | < 100 MB |

**แนะนำ:** RAM 16 GB สำหรับเริ่มต้น, 32 GB ขึ้นไปสำหรับ EVE-NG/GNS3 แบบหลายยี่ห้อ, CPU รองรับ **virtualization (Intel VT-x/AMD-V)** และเปิดใน BIOS, ดิสก์ SSD

> ⚠️ **ลิขสิทธิ์ image:** image ของ Cisco/Fortinet/Palo Alto ต้องได้มาอย่างถูกต้อง (CML, ช่องทาง trial/eval ของ vendor, สัญญาขององค์กร) อย่าดาวน์โหลดจากแหล่งที่ไม่ได้รับอนุญาต

---

## 4. Packet Tracer — เริ่มต้น

1. สมัคร Cisco Networking Academy (ฟรี) → ดาวน์โหลด Packet Tracer
2. ลาก router, switch, PC มาวาง → เลือกสาย (Copper Straight-through, หรือ "Automatic")
3. คลิกอุปกรณ์ → แท็บ **CLI** พิมพ์คำสั่ง IOS / แท็บ **Desktop** ของ PC ตั้ง IP และเปิด Command Prompt
4. โหมด **Simulation** (มุมขวาล่าง) → ส่ง ping แล้วกด Play ดู packet เดินทีละ hop คลิก packet ดูทุก layer

**Lab แรกที่ควรทำ:** PC 2 เครื่อง – switch – router – switch – PC 2 เครื่อง (2 subnet) ตั้ง IP และ gateway ให้ ping ข้ามวงได้

---

## 5. GNS3 / EVE-NG — ขั้นตอนโดยย่อ

**GNS3:** ติดตั้ง GNS3 GUI + **GNS3 VM** (VMware/VirtualBox) → import appliance (.gns3a) + image → ลากอุปกรณ์ → เชื่อมสาย → Start → คลิกขวา Console
- ต่อ lab ออกเครือข่ายจริงด้วย **Cloud/NAT node**

**EVE-NG:** ติดตั้งเป็น VM (OVA/ISO) → เข้าผ่าน browser → อัปโหลด image ไปที่ `/opt/unetlab/addons/qemu/<ชื่อโฟลเดอร์ตามรูปแบบที่กำหนด>/` → รัน `/opt/unetlab/wrappers/unl_wrapper -a fixpermissions` → สร้าง lab ผ่านเว็บ

---

## 6. FRRouting (FRR) — Router ฟรีบน Linux

**FRR** = ชุดซอฟต์แวร์ routing open-source (OSPF, BGP, IS-IS, EVPN, BFD ฯลฯ) ใช้จริงใน data center (SONiC, Cumulus) มี CLI คล้าย Cisco (`vtysh`)

```bash
sudo apt install frr
sudo sed -i 's/^ospfd=no/ospfd=yes/; s/^bgpd=no/bgpd=yes/' /etc/frr/daemons
sudo systemctl restart frr
sudo vtysh
```
```
router# configure terminal
router(config)# router ospf
router(config-router)# network 10.0.12.0/30 area 0
router(config-router)# end
router# show ip ospf neighbor
router# write memory
```

---

## 7. Containerlab — Lab เป็นโค้ด

**แนวคิด:** เขียน topology เป็นไฟล์ YAML แล้วสั่งสร้างทั้ง lab ในคำสั่งเดียว เก็บใน Git แชร์ให้ทีมได้ ทำซ้ำได้เหมือนเดิมทุกครั้ง

```bash
# ติดตั้ง (ต้องมี Docker) — ดูวิธีล่าสุดที่ containerlab.dev
bash -c "$(curl -sL https://get.containerlab.dev)"
```
```yaml
# ospf-lab.clab.yml
name: ospf-lab
topology:
  nodes:
    r1:
      kind: linux
      image: quay.io/frrouting/frr:10.2.1
      binds: [r1/daemons:/etc/frr/daemons, r1/frr.conf:/etc/frr/frr.conf]
    r2:
      kind: linux
      image: quay.io/frrouting/frr:10.2.1
      binds: [r2/daemons:/etc/frr/daemons, r2/frr.conf:/etc/frr/frr.conf]
  links:
    - endpoints: ["r1:eth1", "r2:eth1"]
```
```bash
sudo containerlab deploy -t ospf-lab.clab.yml     # สร้าง lab
sudo containerlab inspect -t ospf-lab.clab.yml    # ดูรายการ node + IP management
docker exec -it clab-ospf-lab-r1 vtysh            # เข้า router
sudo containerlab graph -t ospf-lab.clab.yml      # ดูแผนภาพ
sudo containerlab destroy -t ospf-lab.clab.yml    # ลบ lab
```
(ตรวจเวอร์ชัน image ล่าสุดก่อนใช้งาน)

---

## 8. แนวปฏิบัติที่ดีในการทำ Lab

1. **วาดแผนผังและ IP plan ก่อน** ลงมือ (ฝึกนิสัยทำเอกสารแบบงานจริง)
2. **เก็บ lab ใน Git:** topology, config ของแต่ละอุปกรณ์, README อธิบายวัตถุประสงค์และวิธีทดสอบ
3. **บันทึก config เริ่มต้น (baseline)** เพื่อรีเซ็ต lab ได้เร็ว
4. **สร้าง break/fix:** ให้เพื่อนทำให้ lab พังแล้วเราแก้ — ฝึก troubleshoot ได้ดีที่สุด
5. **ปิด lab เมื่อไม่ใช้** (ประหยัดทรัพยากร), **ไม่ต่อ lab เข้าเครือข่ายองค์กร** โดยไม่ได้รับอนุญาต
6. **ใช้ vendor sandbox/hands-on labs** สำหรับของที่เครื่องรันไม่ไหว (Cisco DevNet Sandbox, VMware HOL, Nutanix test drive)

### ตัวอย่างโครงสร้าง repo
```
network-labs/
├── 01-vlan-trunk/       (Packet Tracer .pkt + README)
├── 02-ospf-3-routers/   (containerlab yml + configs/)
├── 03-bgp-dual-isp/
└── README.md            (รายการ lab, ทรัพยากรที่ต้องใช้, วิธีเริ่ม)
```

---

## 9. แผน Lab ตาม Roadmap

| Tier | เครื่องมือแนะนำ |
|---|---|
| 1–4 (พื้นฐาน, switching) | Packet Tracer → GNS3 (IOSvL2) |
| 5 (routing) | Packet Tracer / Containerlab + FRR / GNS3 IOSv |
| 6–7 (WAN, VPN, security) | EVE-NG/GNS3 + FortiGate VM/pfSense/strongSwan |
| 8 (DC, VXLAN/EVPN) | Containerlab + Arista cEOS / Nokia SR Linux |
| 9 (automation) | Containerlab + Ansible/Python, DevNet Sandbox |

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Packet Tracer ทำได้ทุกอย่างเหมือนของจริง | เป็น simulator ฟีเจอร์ไม่ครบ ใช้ emulator เมื่อต้องการความสมจริง |
| ต้องซื้ออุปกรณ์จริงถึงจะเรียนได้ | Emulator/container/sandbox ครอบคลุมเกือบทั้งหมด |
| ทำ lab แล้วไม่ต้องจดบันทึก | เอกสาร lab คือ portfolio และฝึกนิสัยงานจริง |

---

## 11. Cheat Sheet

```
Simulator: Packet Tracer (CCNA, ง่าย, simulation mode)
Emulator: GNS3 · EVE-NG · Cisco CML (OS จริง, กิน RAM)
Container: Containerlab (YAML, Git, เร็ว) · FRR = router ฟรี (vtysh)
ทรัพยากร: RAM 16-32GB+, VT-x/AMD-V, SSD · image ต้องถูกลิขสิทธิ์
containerlab deploy/inspect/destroy -t file.clab.yml · docker exec -it node vtysh
Best practice: วาดแผน+IP plan ก่อน · เก็บใน Git · baseline · break/fix
```

---

## 12. แบบทดสอบ 10 ข้อ

1. Simulator กับ Emulator ต่างกันอย่างไร ยกตัวอย่างอย่างละ 1
2. เครื่องมือใดเหมาะที่สุดสำหรับผู้เริ่มเรียน CCNA เพราะอะไร
3. ข้อดีของ Containerlab เทียบกับ GNS3
4. FRR คืออะไร ใช้คำสั่งใดเข้า CLI
5. ทำไมต้องเปิด VT-x/AMD-V ใน BIOS
6. ทรัพยากรใดสำคัญที่สุดเมื่อรัน VM อุปกรณ์จำนวนมาก
7. ทำไมควรเก็บ topology และ config ของ lab ใน Git
8. ต้องการทดลอง FortiGate โดยเครื่องไม่แรงพอ มีทางเลือกอะไร
9. Break/fix lab คืออะไร มีประโยชน์อย่างไร
10. ข้อควรระวังเรื่อง image ของอุปกรณ์

<details><summary><b>เฉลย</b></summary>

1. Simulator เลียนแบบพฤติกรรม (Packet Tracer); Emulator รัน OS จริงของอุปกรณ์ (GNS3/EVE-NG)
2. Packet Tracer — ฟรี เบา ครอบคลุมเนื้อหา CCNA และมี simulation mode ดู packet ทีละขั้น
3. เบา เร็ว topology เป็นไฟล์ YAML เก็บใน Git ทำซ้ำได้ เหมาะกับ automation/CI
4. ชุดซอฟต์แวร์ routing open-source บน Linux — `vtysh`
5. ให้ hypervisor รัน VM ได้มีประสิทธิภาพ (emulator ส่วนใหญ่ต้องใช้)
6. RAM
7. ทำซ้ำได้ แชร์ทีมได้ ติดตามการเปลี่ยนแปลง และเป็น portfolio
8. ใช้ hands-on lab/eval ของ vendor หรือ cloud lab ชั่วคราว หรือใช้ทางเลือกที่เบากว่า (pfSense) เพื่อฝึกแนวคิด
9. ให้คนอื่นทำ lab ให้เสียแล้วเราหาสาเหตุ/แก้ — ฝึกทักษะ troubleshoot ที่ใกล้เคียงงานจริง
10. ต้องได้มาอย่างถูกลิขสิทธิ์ (CML, trial/eval, สัญญาองค์กร)
</details>

---

➡️ ต่อไป: **Level 29 — Cisco IOS พื้นฐาน**
