# Tier 4 — Switching (Level 31–40)

> เป้าหมายของ Tier: ออกแบบ/ตั้งค่า/แก้ปัญหา LAN ระดับองค์กร (VLAN, Trunk, STP, EtherChannel, Port Security)

---

## Level 31 — การทำงานของ Switch & MAC Address Table

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L31-switch-mac-table.md](lessons/L31-switch-mac-table.md)

**สิ่งที่ต้องรู้**
- Learning (src MAC), Forwarding (dst MAC รู้จัก), Flooding (unknown unicast/broadcast/multicast), Filtering
- MAC aging 300 วินาที, CAM table
- Store-and-forward vs Cut-through
- MAC flapping = สัญญาณ loop หรือ dual-homing ผิด
- `show mac address-table`, `show interfaces status`, `show interfaces counters errors`

**แบบทดสอบ**
1. Switch เรียนรู้ MAC จาก field ไหน
2. Frame ที่ไม่รู้จัก dst MAC จะทำอย่างไร
3. log "MAC flapping between port X and Y" สาเหตุที่เป็นไปได้
4. หา port ที่เครื่อง MAC aaaa.bbbb.cccc เสียบอยู่อย่างไร
5. CRC error เพิ่มขึ้นที่พอร์ตหนึ่ง สงสัยอะไร

<details><summary>เฉลย</summary>

1. Source MAC
2. Flood ออกทุกพอร์ตใน VLAN ยกเว้นพอร์ตที่รับเข้ามา
3. L2 loop, VM migrate, NIC teaming ผิด mode
4. `show mac address-table address aaaa.bbbb.cccc` ไล่ตาม uplink/CDP ไปจนถึง access port
5. สาย/หัว/SFP เสีย, EMI, duplex mismatch
</details>

**5 โปรเจค**
- ⭐ P1: Packet Tracer: ดู MAC table เปลี่ยนแปลงขณะ ping
- ⭐⭐ P2: Python (Netmiko) "หาเครื่องจาก MAC/IP" ไล่หลาย switch อัตโนมัติ
- ⭐⭐ P3: Lab สร้าง MAC flapping แล้วอ่าน log + แก้
- ⭐⭐ P4: สคริปต์รวบรวม interface error ทุก switch → รายงานพอร์ตที่มีปัญหา
- ⭐⭐⭐ P5: จำลอง switch learning/forwarding ด้วย Python (simulation class)

---

## Level 32 — VLAN

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L32-vlan.md](lessons/L32-vlan.md)

**สิ่งที่ต้องรู้**
- VLAN แบ่ง broadcast domain แบบ logical, VLAN ID 1–4094 (normal 1–1005, extended 1006–4094)
- Access port, Voice VLAN, Native VLAN, Management VLAN
- Best practice: ไม่ใช้ VLAN 1, ปิดพอร์ตที่ไม่ใช้ + ใส่ parking VLAN
- ออกแบบ VLAN ตามหน้าที่: User, Voice, Printer, Server, Mgmt, Guest, IoT, CCTV

```
vlan 10
 name USERS
interface range g0/1-20
 switchport mode access
 switchport access vlan 10
 switchport voice vlan 110
 spanning-tree portfast
```

**แบบทดสอบ**
1. 2 เครื่องคนละ VLAN บน switch เดียวกัน ping กันได้ไหมโดยไม่มี router
2. Voice VLAN ทำงานอย่างไรเมื่อ PC ต่อผ่าน IP phone
3. ทำไมไม่ควรใช้ VLAN 1
4. คำสั่งดู VLAN ทั้งหมด
5. ข้อดีของการแยก IoT/CCTV ไว้ VLAN ต่างหาก

<details><summary>เฉลย</summary>

1. ไม่ได้ (ต้อง L3 routing)
2. phone ใช้ tagged voice VLAN, PC ใช้ untagged data VLAN บนพอร์ตเดียว
3. เป็น default ทุกพอร์ต + control protocol ใช้ เสี่ยงด้าน security (VLAN hopping)
4. `show vlan brief`
5. จำกัดการโจมตี lateral movement, ควบคุม policy ได้, ลด broadcast
</details>

**5 โปรเจค**
- ⭐ P1: Packet Tracer: 3 VLAN บน switch เดียว ทดสอบ isolation
- ⭐⭐ P2: ออกแบบ VLAN plan องค์กร (ID, ชื่อ, subnet, gateway) — ใช้ต่อทั้ง Tier
- ⭐⭐ P3: Lab IP phone + PC บนพอร์ตเดียว (voice VLAN)
- ⭐⭐ P4: สคริปต์ตรวจ compliance: พอร์ตที่ไม่ใช้ต้อง shutdown + VLAN 999
- ⭐⭐⭐ P5: Python สร้าง config VLAN อัตโนมัติจาก CSV ด้วย Jinja2

---

## Level 33 — Trunk 802.1Q & DTP

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L33-trunk-8021q.md](lessons/L33-trunk-8021q.md)

**สิ่งที่ต้องรู้**
- 802.1Q tag 4 byte (TPID 0x8100, PCP 3 bit, VID 12 bit)
- Native VLAN ส่ง untagged; native mismatch → CDP warning + traffic รั่ว
- `switchport trunk allowed vlan` จำกัด VLAN ที่ผ่าน (pruning)
- DTP: dynamic auto/desirable — ควรปิด (`switchport nonegotiate`)
- VTP: server/client/transparent — หลายองค์กรใช้ transparent/off เพื่อลดความเสี่ยง

```
interface g0/24
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,20,30,110
 switchport nonegotiate
```

**แบบทดสอบ**
1. VLAN ID มีกี่บิต
2. ผลของ native VLAN mismatch
3. dynamic auto ทั้ง 2 ฝั่ง เกิด trunk ไหม
4. ทำไม VTP อันตราย
5. คำสั่งดูว่า trunk อนุญาต VLAN อะไรบ้าง

<details><summary>เฉลย</summary>

1. 12 บิต (4096 ค่า)
2. traffic untagged ของ VLAN หนึ่งไปโผล่อีก VLAN, STP inconsistency
3. ไม่ (เป็น access)
4. switch ที่มี revision สูงกว่าเสียบเข้ามาลบ VLAN ทั้งโดเมนได้
5. `show interfaces trunk`
</details>

**5 โปรเจค**
- ⭐ P1: Packet Tracer: 2 switch trunk 3 VLAN
- ⭐⭐ P2: Wireshark ดู 802.1Q tag (GNS3/Linux VLAN)
- ⭐⭐ P3: Lab native VLAN mismatch และ VLAN hopping (double tagging) + การป้องกัน
- ⭐⭐ P4: Linux bridge VLAN-aware ทำ trunk ไป switch/VM
- ⭐⭐⭐ P5: สคริปต์ audit trunk ทุก switch: allowed VLAN, native, DTP — แสดงความไม่สอดคล้อง

---

## Level 34 — Inter-VLAN Routing

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L34-inter-vlan-routing.md](lessons/L34-inter-vlan-routing.md)

**สิ่งที่ต้องรู้**
- Router-on-a-stick (subinterface `encapsulation dot1Q 10`)
- L3 switch + SVI (`interface vlan 10`, `ip routing`)
- Routed port (`no switchport`)
- ข้อดีข้อเสียของแต่ละแบบ (bottleneck, ราคา, ความเร็ว)
- Gateway อยู่ที่ไหน = จุดบังคับ policy (ACL/firewall)

```
interface g0/0.10
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0
! หรือ L3 switch
ip routing
interface vlan 10
 ip address 192.168.10.1 255.255.255.0
```

**แบบทดสอบ**
1. ข้อเสียของ router-on-a-stick
2. SVI ขึ้น up/up ต้องมีเงื่อนไขอะไร
3. คำสั่งที่ลืมบ่อยบน L3 switch
4. Routed port ต่างจาก SVI อย่างไร
5. ถ้าต้องการให้ VLAN Guest ออกได้แค่ internet จะวาง policy ที่ไหน

<details><summary>เฉลย</summary>

1. ลิงก์เดียวเป็น bottleneck + single point of failure
2. VLAN มีอยู่ และมีพอร์ต (access/trunk) ใน VLAN นั้น up อย่างน้อย 1
3. `ip routing`
4. Routed port = พอร์ตจริงเป็น L3 ไม่มี VLAN; SVI = interface เสมือนของ VLAN
5. ACL บน SVI หรือให้ gateway ของ Guest อยู่ที่ firewall
</details>

**5 โปรเจค**
- ⭐ P1: Router-on-a-stick 3 VLAN + DHCP
- ⭐⭐ P2: แทนด้วย L3 switch SVI เปรียบเทียบผล traceroute
- ⭐⭐ P3: ทำ Guest VLAN ที่เข้าระบบภายในไม่ได้ (ACL)
- ⭐⭐ P4: Linux router-on-a-stick (VLAN subinterface + forwarding)
- ⭐⭐⭐ P5: ทำ Lab แผนก 5 VLAN + server farm + policy matrix ใครเข้าอะไรได้ + test script

---

## Level 35 — Spanning Tree Protocol (STP 802.1D)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L35-stp.md](lessons/L35-stp.md)

**สิ่งที่ต้องรู้**
- ทำไมต้องมี: broadcast storm, MAC instability, duplicate frame
- Root bridge election: Bridge ID ต่ำสุด (priority 32768 + VLAN + MAC)
- Root port, Designated port, Blocked port; path cost (1G=4, 10G=2)
- Port states: Blocking → Listening → Learning → Forwarding (~30–50 วินาที)
- PVST+ (Cisco: STP ต่อ VLAN)
- **ต้องกำหนด root เอง** ไว้ที่ core/distribution

```
spanning-tree vlan 1-4094 root primary   ! หรือ priority 4096
show spanning-tree vlan 10
```

**แบบทดสอบ**
1. Root bridge เลือกจากอะไร
2. ทำไมต้องตั้ง root เอง
3. Path cost ของ 1 Gbps (short method)
4. port ที่ไม่ใช่ root/designated จะเป็นอะไร
5. STP 802.1D converge นานเท่าไร

<details><summary>เฉลย</summary>

1. Bridge ID ต่ำสุด (priority แล้วจึง MAC)
2. ถ้าปล่อยอัตโนมัติ switch เก่าสุด (MAC ต่ำ) อาจเป็น root → traffic ไหลผิดทาง
3. 4
4. Blocking (alternate)
5. 30–50 วินาที
</details>

**5 โปรเจค**
- ⭐ P1: Packet Tracer 3 switch สามเหลี่ยม ทาย root/port role ก่อน แล้วตรวจ
- ⭐⭐ P2: Lab บังคับ root primary/secondary ต่อ VLAN (load-share)
- ⭐⭐ P3: Wireshark ดู BPDU fields
- ⭐⭐ P4: สร้าง loop ใน lab (ปิด STP) สังเกต broadcast storm แล้วเขียนรายงาน
- ⭐⭐⭐ P5: Python คำนวณ STP topology จาก graph (networkx) → บอก root/port role

---

## Level 36 — RSTP, MST & STP Toolkit

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L36-rstp-mst-stp-toolkit.md](lessons/L36-rstp-mst-stp-toolkit.md)

**สิ่งที่ต้องรู้**
- RSTP 802.1w: converge เร็ว (proposal/agreement), port roles: alternate/backup, states: discarding/learning/forwarding
- MST 802.1s: map หลาย VLAN → instance (region name/revision ต้องตรงกัน)
- PortFast (edge port), BPDU Guard, BPDU Filter, Root Guard, Loop Guard, UDLD
- Storm control

```
spanning-tree mode rapid-pvst
interface range g0/1-20
 spanning-tree portfast
 spanning-tree bpduguard enable
interface g0/24
 spanning-tree guard root
```

**แบบทดสอบ**
1. BPDU Guard ทำอะไรเมื่อได้รับ BPDU
2. Root Guard ใส่ที่พอร์ตไหน
3. Loop Guard ป้องกันปัญหาอะไร
4. MST region ต้องตรงกันในเรื่องใด
5. PortFast ห้ามใส่พอร์ตแบบไหน

<details><summary>เฉลย</summary>

1. err-disable พอร์ต
2. Downlink ที่ไม่ควรมี root อยู่ฝั่งนั้น (เช่น ไปยัง access switch)
3. Unidirectional link ทำให้ blocked port กลายเป็น forwarding
4. Region name, revision, VLAN-to-instance mapping
5. พอร์ตที่ต่อกับ switch/bridge อื่น (trunk ไป switch)
</details>

**5 โปรเจค**
- ⭐ P1: วัดเวลา converge STP vs RSTP (ping -t ระหว่างดึงสาย)
- ⭐⭐ P2: ตั้ง MST 2 instance (VLAN คู่/คี่) load-share
- ⭐⭐ P3: ทดลองเสียบ switch แปลกปลอมที่พอร์ต BPDU Guard → err-disable → recovery
- ⭐⭐ P4: เขียน "STP Standard" ขององค์กร (root placement, guard features)
- ⭐⭐⭐ P5: สคริปต์ตรวจ STP ทุก switch: root ของแต่ละ VLAN ถูกตัวไหม, TCN ล่าสุด, edge port ไม่มี BPDU Guard

---

## Level 37 — EtherChannel / Link Aggregation (LACP)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L37-etherchannel-lacp.md](lessons/L37-etherchannel-lacp.md)

**สิ่งที่ต้องรู้**
- รวมหลายลิงก์เป็น logical link: bandwidth + redundancy, STP มองเป็นลิงก์เดียว
- LACP (802.3ad: active/passive), PAgP (Cisco), Static (on)
- เงื่อนไข: speed/duplex/VLAN/mode ต้องตรงกัน
- Load-balancing hash (src-dst-ip, src-dst-mac, L4) — 1 flow ใช้ได้แค่ 1 ลิงก์
- MLAG / vPC / StackWise Virtual: EtherChannel ข้าม 2 switch

```
interface range g0/1-2
 channel-group 1 mode active
interface port-channel 1
 switchport mode trunk
show etherchannel summary
```

**แบบทดสอบ**
1. passive + passive ทำงานไหม
2. ทำไม 1 flow ใหญ่ไม่ได้ bandwidth 2 เท่า
3. ถ้าพอร์ตหนึ่งใน bundle มี VLAN ต่างกัน จะเกิดอะไร
4. MLAG/vPC แก้ปัญหาอะไร
5. flag "SU" และ "P" ใน `show etherchannel summary` หมายถึง

<details><summary>เฉลย</summary>

1. ไม่
2. hash ส่ง flow เดียวกันลงลิงก์เดียว (รักษาลำดับ packet)
3. พอร์ตนั้นถูก suspend ไม่เข้า bundle
4. dual-homing ไป 2 switch โดย active-active ไม่ถูก STP block
5. S=Layer2, U=in use; P=bundled in port-channel
</details>

**5 โปรเจค**
- ⭐ P1: LACP 2 ลิงก์ระหว่าง 2 switch
- ⭐⭐ P2: Linux bond mode 4 ต่อ switch (GNS3) ตรวจ LACP state
- ⭐⭐ P3: ทดสอบ load-balance algorithm ต่าง ๆ ด้วย iperf หลาย flow
- ⭐⭐ P4: Lab misconfig 5 แบบ (mode, VLAN, speed) แล้วหาสาเหตุ
- ⭐⭐⭐ P5: Lab vPC/MLAG (Nexus 9000v หรือ Arista cEOS) + dual-homed server

---

## Level 38 — Port Security & Access Control บน Switch

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L38-port-security.md](lessons/L38-port-security.md)

**สิ่งที่ต้องรู้**
- Port security: maximum MAC, sticky, violation mode (protect/restrict/shutdown)
- err-disable recovery
- 802.1X (Level 66) เป็นทางเลือกที่ดีกว่าในองค์กรใหญ่
- Private VLAN (isolated/community/promiscuous)
- Protected port, storm-control

```
interface g0/5
 switchport port-security
 switchport port-security maximum 2
 switchport port-security mac-address sticky
 switchport port-security violation restrict
errdisable recovery cause psecure-violation
```

**แบบทดสอบ**
1. violation mode ไหนส่ง log + นับ counter แต่ไม่ปิดพอร์ต
2. sticky MAC ทำอะไร
3. พอร์ต IP phone + PC ต้องตั้ง maximum เท่าไรอย่างน้อย
4. Private VLAN isolated ใช้กับสถานการณ์ไหน
5. ข้อจำกัดของ port security เทียบ 802.1X

<details><summary>เฉลย</summary>

1. restrict
2. เรียน MAC แล้วใส่ใน running-config อัตโนมัติ
3. 2 (บางรุ่น phone ใช้ MAC ใน voice VLAN ด้วย อาจตั้ง 3)
4. Hotel/guest/DMZ ที่ไม่ให้ host คุยกันเอง
5. MAC ปลอมได้ง่าย, ไม่ยืนยันตัวตนผู้ใช้, จัดการยากเมื่อขนาดใหญ่
</details>

**5 โปรเจค**
- ⭐ P1: ตั้ง port security + ทดสอบ violation ทั้ง 3 mode
- ⭐⭐ P2: ทำ Private VLAN ใน DMZ (GNS3 IOSvL2)
- ⭐⭐ P3: สคริปต์ดึงรายการ err-disabled ports ทุกตัว + สาเหตุ ส่ง Slack/LINE
- ⭐⭐ P4: เขียน Access-port standard template (portfast, bpduguard, port-security, storm-control)
- ⭐⭐⭐ P5: Self-service portal เล็ก ๆ (Flask) ให้ helpdesk reset err-disable ได้อย่างปลอดภัย (มี audit log)

---

## Level 39 — CDP, LLDP & เอกสารเครือข่าย

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L39-cdp-lldp-documentation.md](lessons/L39-cdp-lldp-documentation.md)

**สิ่งที่ต้องรู้**
- CDP (Cisco), LLDP (มาตรฐาน 802.1AB), LLDP-MED (voice VLAN, PoE)
- ใช้ทำ topology discovery และหาว่า "พอร์ตนี้ต่อไปไหน"
- ความเสี่ยง: เปิดเผยข้อมูลอุปกรณ์ → ปิดที่พอร์ต edge/internet
- เอกสารที่ต้องมี: L1 (cabling/rack), L2 (VLAN/trunk/STP), L3 (IP/routing), IPAM, port mapping

```
show cdp neighbors detail
lldp run
show lldp neighbors
```

**แบบทดสอบ**
1. CDP กับ LLDP ต่างกันอย่างไร
2. LLDP-MED ใช้กับอุปกรณ์อะไร
3. ทำไมควรปิด CDP บนพอร์ตที่ต่อ ISP
4. ข้อมูลอะไรได้จาก `show cdp neighbors detail`
5. ใช้ LLDP บน Linux ด้วยโปรแกรมอะไร

<details><summary>เฉลย</summary>

1. CDP เป็น Cisco proprietary, LLDP เป็นมาตรฐานเปิด
2. IP phone/endpoint สื่อสาร VLAN, PoE, location
3. ไม่ให้ภายนอกรู้รุ่น/OS/IP อุปกรณ์
4. hostname, IP, platform, IOS version, local/remote port, native VLAN
5. lldpd (`lldpcli show neighbors`)
</details>

**5 โปรเจค**
- ⭐ P1: วาด topology จากข้อมูล CDP ด้วยมือ
- ⭐⭐ P2: Python ไล่ CDP/LLDP แบบ crawl จาก core → สร้าง topology อัตโนมัติ
- ⭐⭐ P3: แปลงผล P2 เป็นภาพด้วย Graphviz/networkx/D2
- ⭐⭐ P4: ทำชุดเอกสาร L1/L2/L3 ของ lab ใหญ่ที่สุดที่เคยทำ
- ⭐⭐⭐ P5: ส่งผล discovery เข้า NetBox อัตโนมัติ (ต่อยอด Level 89)

---

## Level 40 — L3 Switching & Campus Design

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L40-campus-design.md](lessons/L40-campus-design.md)

**สิ่งที่ต้องรู้**
- Hierarchical: Access / Distribution / Core, Collapsed core (บริษัทเล็ก-กลาง)
- L2 access vs Routed access (L3 ถึง access, ไม่มี STP ระหว่าง layer)
- Stacking (StackWise), chassis, VSS/StackWise Virtual
- Oversubscription ratio (access→distribution 20:1, distribution→core 4:1)
- Redundancy: dual uplink, dual PSU, FHRP (Level 50)
- Wireless และ PoE ใน campus

**แบบทดสอบ**
1. Collapsed core คืออะไร เหมาะกับใคร
2. ข้อดีของ routed access
3. Access switch 48×1G uplink 2×10G oversubscription เท่าไร
4. Stack switch ต่างจาก MLAG/VSS อย่างไร
5. ปัจจัยที่ใช้เลือกจำนวน/รุ่น access switch

<details><summary>เฉลย</summary>

1. รวม core+distribution ในชั้นเดียว — องค์กรขนาดเล็ก-กลาง/ตึกเดียว
2. ไม่มี STP loop ข้าม layer, converge เร็วด้วย routing, ECMP
3. 48G / 20G = 2.4:1
4. Stack = control plane เดียว (ทุกตัวเหมือน switch เดียว); MLAG = control plane แยก ประสานกัน
5. จำนวนพอร์ต+เผื่อโต 20–30%, PoE budget, uplink speed, รองรับ 802.1X/feature, งบ
</details>

**5 โปรเจค**
- ⭐⭐ P1: ออกแบบ campus 3 ตึก 1,000 users (HLD: diagram + เหตุผล)
- ⭐⭐ P2: ทำ LLD: VLAN, IP, port map, STP root, รุ่นอุปกรณ์ + BOM
- ⭐⭐ P3: Implement ย่อส่วนใน GNS3/Packet Tracer
- ⭐⭐⭐ P4: เปรียบเทียบ L2 access vs routed access ใน lab: converge time + ความซับซ้อน
- ⭐⭐⭐ P5: Capstone Tier 4: เครือข่ายโรงเรียน/โรงพยาบาลจำลอง ครบ VLAN, trunk, RSTP, LACP, port security + เอกสาร + test plan
