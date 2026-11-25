# บทเรียน Level 29 — Cisco IOS พื้นฐาน (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจโหมดต่าง ๆ ของ IOS · ตั้งค่าเริ่มต้นและ hardening พื้นฐาน · เปิด SSH · ตั้ง IP ให้ interface · บันทึก/สำรอง config · ใช้ show command และเทคนิค CLI อย่างมืออาชีพ · เทียบคำสั่งกับยี่ห้ออื่น

---

## 1. ทำไมต้อง Cisco IOS

- Cisco มีส่วนแบ่งตลาดอุปกรณ์องค์กรสูง และ **CLI แบบ Cisco กลายเป็นต้นแบบ** ที่ยี่ห้ออื่นเลียนแบบ (Arista EOS, FRR, Ruijie, Huawei บางส่วน)
- เป็นเนื้อหาหลักของ CCNA ซึ่งเป็น cert ที่ตลาดงานถามหาบ่อยที่สุด
- ตระกูล OS: **IOS / IOS-XE** (router/switch องค์กร), **NX-OS** (Nexus data center), **IOS-XR** (ISP)

---

## 2. การเข้าถึงอุปกรณ์

| วิธี | ใช้เมื่อ |
|---|---|
| **Console** (สาย RJ45/USB → serial, 9600 8N1) | ตั้งค่าครั้งแรก, เมื่อเข้าผ่านเครือข่ายไม่ได้, password recovery |
| **SSH** (port 22) | การจัดการปกติผ่านเครือข่าย (เข้ารหัส) |
| Telnet (port 23) | **ห้ามใช้** — ส่งรหัสผ่านเป็น plain text |
| **AUX/OOB** | ผ่าน console server/เครือข่ายจัดการแยก |
| Web GUI / API (RESTCONF/NETCONF) | IOS-XE รุ่นใหม่ |

โปรแกรม: PuTTY, SecureCRT, MobaXterm, Windows Terminal (`ssh admin@10.0.0.1`)

---

## 3. โหมดของ IOS

```
 Router>                     User EXEC          ดูได้จำกัด
   │ enable
 Router#                     Privileged EXEC    show ทุกอย่าง, copy, reload, debug
   │ configure terminal
 Router(config)#             Global config      ตั้งค่าทั้งเครื่อง
   │ interface g0/0
 Router(config-if)#          Interface config
   │ router ospf 1 / line vty 0 4 / vlan 10 ...
 Router(config-router)#  Router(config-line)#  Switch(config-vlan)#

 exit = ถอยหนึ่งขั้น · end (หรือ Ctrl+Z) = กลับไป Privileged EXEC ทันที
```

**ใช้คำสั่ง show จากโหมด config:** ใส่ `do` ข้างหน้า → `Router(config)# do show ip interface brief`

---

## 4. เทคนิค CLI ที่ต้องใช้ให้คล่อง

| เทคนิค | ตัวอย่าง |
|---|---|
| **`?`** ดูคำสั่งที่ใช้ได้ | `show ?` · `show ip ?` · `sh ip int b?` |
| **ย่อคำสั่ง** (ไม่กำกวม) | `conf t` = configure terminal · `sh ip int br` · `int g0/1` |
| **Tab** เติมคำสั่งให้ครบ | `conf` + Tab |
| **ลูกศรขึ้น/Ctrl+P** | คำสั่งก่อนหน้า |
| **`no` + คำสั่ง** | ยกเลิกค่านั้น: `no shutdown`, `no ip address` |
| **กรองผลลัพธ์** | `show run \| include hostname` · `show run \| section interface` · `show log \| begin 10:15` · `\| exclude` |
| `terminal length 0` | แสดงผลยาวโดยไม่หยุดถาม --More-- (ใช้ตอนเก็บ log/สคริปต์) |
| `Ctrl+Shift+6` | หยุดคำสั่งที่ค้าง (ping/traceroute/DNS lookup) |
| `no ip domain-lookup` | พิมพ์คำสั่งผิดแล้วไม่ค้างรอ DNS |

---

## 5. Running-config vs Startup-config

| | running-config | startup-config |
|---|---|---|
| อยู่ที่ | **RAM** | **NVRAM** |
| คือ | ค่าที่ทำงานอยู่ตอนนี้ | ค่าที่จะโหลดตอนบูต |
| แก้แล้ว | มีผลทันที | ต้องบันทึกจาก running |
| ไฟดับ/reload | **หายถ้าไม่ได้บันทึก** | คงอยู่ |

```
copy running-config startup-config      (หรือ write memory / wr)
show running-config                     ค่าปัจจุบัน
show startup-config
```
> 💡 **เทคนิคความปลอดภัยเมื่อแก้ผ่าน remote:** ก่อนแก้ค่าที่เสี่ยง (ACL, IP ของ interface ที่ใช้ SSH) ใช้ `reload in 10` — ถ้าแก้ผิดจนเข้าไม่ได้ เครื่องจะ reload กลับไปใช้ startup-config ใน 10 นาที ถ้าแก้สำเร็จให้ `reload cancel` แล้วจึงบันทึก

---

## 6. ตั้งค่าเริ่มต้น (Day-0 Baseline)

```
enable
configure terminal
 hostname BKK-CORE-SW01
 no ip domain-lookup
 service password-encryption               ! เข้ารหัส password แบบอ่อน (type 7) ไม่ให้เห็นเป็นข้อความเปล่า
 enable secret Str0ng!Enable               ! รหัสเข้า privileged (hash) — ใช้ secret ไม่ใช่ password
 username netadmin privilege 15 secret Str0ng!Admin
 banner motd ^Authorized access only. Activities are logged.^
 clock timezone ICT 7 0
 ntp server 10.0.0.123
 logging host 10.0.0.50
 service timestamps log datetime msec localtime
!
line console 0
 login local
 exec-timeout 10 0
 logging synchronous                       ! log ไม่แทรกกลางบรรทัดที่กำลังพิมพ์
!
end
write memory
```

### `enable password` vs `enable secret`
- `enable password` → เก็บเป็นข้อความหรือ type 7 (ถอดกลับได้ง่าย) **ไม่ควรใช้**
- `enable secret` → เก็บเป็น **hash** (type 5/8/9) ปลอดภัยกว่า ถ้ามีทั้งคู่ secret จะถูกใช้

---

## 7. เปิด SSH และปิด Telnet

```
configure terminal
 ip domain-name corp.local                       ! ต้องมี hostname + domain ก่อนสร้าง key
 crypto key generate rsa modulus 2048            ! (หรือ 4096)
 ip ssh version 2
 ip ssh time-out 60
 ip ssh authentication-retries 3
 username netadmin privilege 15 secret Str0ng!Admin
!
 ip access-list standard MGMT-ONLY
  permit 10.0.99.0 0.0.0.255                     ! อนุญาตเฉพาะ management network
!
line vty 0 15
 login local                                     ! ใช้ user ในเครื่อง (หรือ AAA - Level 56)
 transport input ssh                             ! ปิด Telnet
 access-class MGMT-ONLY in
 exec-timeout 10 0
end
write memory
show ip ssh
show ssh
```

---

## 8. ตั้ง IP ให้ Interface

### Router
```
interface GigabitEthernet0/0
 description Link to ISP
 ip address 203.0.113.2 255.255.255.252
 no shutdown                                     ! interface ของ router ปิดอยู่เป็นค่าเริ่มต้น!
```
### Switch (L2) — ตั้ง IP สำหรับจัดการที่ SVI
```
interface vlan 99
 description MGMT
 ip address 10.0.99.11 255.255.255.0
 no shutdown
ip default-gateway 10.0.99.1                     ! switch L2 ใช้ default-gateway (ไม่ใช่ ip route)
```

---

## 9. Show Commands ที่ใช้ทุกวัน

| คำสั่ง | ดูอะไร |
|---|---|
| **`show ip interface brief`** | ทุก interface: IP, Status, Protocol (คำสั่งแรกที่ใช้เสมอ) |
| `show interfaces g0/1` | รายละเอียด: speed/duplex, input/output errors, CRC, drops |
| `show interfaces status` | (switch) พอร์ต, VLAN, duplex, speed |
| `show running-config` / `show run interface g0/1` | config |
| `show version` | รุ่น, IOS version, uptime, serial, เหตุผลที่ reload ครั้งล่าสุด |
| `show ip route` | routing table |
| `show vlan brief` / `show interfaces trunk` | VLAN และ trunk |
| `show mac address-table` | ตาราง MAC |
| `show cdp neighbors [detail]` / `show lldp neighbors` | อุปกรณ์ข้างเคียง |
| `show logging` | log |
| `show inventory` | serial ของ chassis/module/SFP |
| `show processes cpu sorted` | CPU |

### อ่าน `show ip interface brief`
```
Interface          IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0 203.0.113.2     YES manual up                    up        ← ✅ ปกติ
GigabitEthernet0/1 10.0.10.1       YES manual administratively down down      ← ยังไม่ได้ no shutdown
GigabitEthernet0/2 unassigned      YES unset  down                  down      ← L1: สาย/อีกฝั่ง
Serial0/0/0        10.255.0.1      YES manual up                    down      ← L2: encapsulation/clock/keepalive ไม่ตรง
```

| Status / Protocol | ความหมาย |
|---|---|
| up / up | ทำงานปกติ |
| administratively down / down | ถูก `shutdown` → ใส่ `no shutdown` |
| down / down | ปัญหาชั้นกายภาพ (สาย, SFP, อีกฝั่งปิด) |
| up / down | ชั้นกายภาพได้ แต่ชั้น Data Link มีปัญหา |
| err-disabled | ถูกปิดอัตโนมัติจาก security feature (port security, BPDU guard) |

---

## 10. Backup / Restore Config

```
copy running-config tftp:                    ! ระบุ IP server และชื่อไฟล์
copy running-config scp://user@10.0.0.50/backup/sw01.cfg
copy tftp: running-config                    ! merge config กลับ (ไม่ใช่แทนที่ทั้งหมด)
configure replace flash:sw01-baseline.cfg    ! แทนที่ทั้งหมด (IOS-XE)
archive / kron                               ! สำรองอัตโนมัติตามเวลา (หรือใช้ Ansible/Oxidized - Tier 9)
```

---

## 11. Password Recovery (หลักการ)

ลืมรหัส enable ต้องเข้าทาง **console** แล้วขัดจังหวะการบูต (Break) → ตั้ง config register ให้ข้าม startup-config (`0x2142`) → บูตเข้าได้โดยไม่มีรหัส → `copy startup-config running-config` → ตั้งรหัสใหม่ → คืนค่า register `0x2102` → บันทึก
(ขั้นตอนแต่ละรุ่นต่างกัน ดูเอกสารของรุ่นนั้น; ต้องเข้าถึงตัวอุปกรณ์ จึงต้องควบคุมการเข้าห้อง server)

---

## 12. เทียบคำสั่งกับยี่ห้ออื่น

| งาน | Cisco IOS | Juniper Junos | Arista EOS | MikroTik RouterOS |
|---|---|---|---|---|
| เข้าโหมดตั้งค่า | `configure terminal` | `configure` | `configure` | (พิมพ์ path เช่น `/ip address`) |
| ดู interface | `show ip int brief` | `show interfaces terse` | `show ip int brief` | `/interface print` |
| ดู route | `show ip route` | `show route` | `show ip route` | `/ip route print` |
| ดู config | `show run` | `show configuration` | `show run` | `/export` |
| บันทึก | `write memory` | `commit` (มี `commit confirmed`) | `write` | บันทึกอัตโนมัติ |
| ยกเลิกค่า | `no ...` | `delete ...` | `no ...` | `remove` |

> 💡 Junos ใช้แนวคิด **candidate config + commit** (แก้หลายอย่างแล้ว commit ทีเดียว และ `commit confirmed 5` ย้อนกลับอัตโนมัติถ้าไม่ยืนยัน) ซึ่งปลอดภัยกว่าการแก้แล้วมีผลทันทีแบบ IOS

---

## 13. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| แก้ config แล้ว reboot ค่ายังอยู่ | ต้อง `write memory` ก่อน |
| `service password-encryption` ทำให้ปลอดภัย | แค่ซ่อนจากสายตา (type 7 ถอดได้) ต้องใช้ secret |
| interface ของ router เปิดอยู่แล้ว | ต้อง `no shutdown` |
| switch L2 ใช้ `ip route` สำหรับ gateway | ใช้ `ip default-gateway` |

---

## 14. Cheat Sheet

```
> user · # privileged (enable) · (config)# conf t · (config-if)# int X · end/Ctrl+Z
? · Tab · ย่อคำสั่ง · do show ... · | include / section / begin · terminal length 0 · Ctrl+Shift+6
running (RAM) → write memory → startup (NVRAM) · reload in 10 / reload cancel
Baseline: hostname · no ip domain-lookup · enable secret · username secret · banner · NTP · logging
SSH: ip domain-name → crypto key generate rsa modulus 2048 → ip ssh version 2 → line vty: login local, transport input ssh, access-class
show ip int brief: admin down = shutdown · down/down = L1 · up/down = L2 · err-disabled = security
```

---

## 15. แบบทดสอบ 10 ข้อ

1. เรียงโหมดของ IOS จาก User EXEC ไปจนถึง Interface config พร้อมคำสั่งที่ใช้เข้า
2. คำสั่งบันทึก config และถ้าไม่บันทึกแล้ว reload จะเกิดอะไร
3. `enable secret` ดีกว่า `enable password` อย่างไร
4. ขั้นตอนเปิด SSH v2 บน router
5. ทำไมต้องใส่ `transport input ssh` และ `access-class` ที่ line vty
6. interface แสดง `administratively down` แก้อย่างไร
7. interface แสดง `up / down` บ่งบอกปัญหาชั้นใด
8. switch L2 ตั้ง IP จัดการและ gateway อย่างไร
9. คำสั่งแสดงเฉพาะส่วน config ของ interface ทั้งหมดจาก running-config
10. `reload in 10` มีประโยชน์อย่างไรเมื่อแก้ config ผ่าน SSH

<details><summary><b>เฉลย</b></summary>

1. `>` → `enable` → `#` → `configure terminal` → `(config)#` → `interface g0/0` → `(config-if)#`
2. `copy running-config startup-config` (หรือ `write memory`) — ถ้าไม่บันทึก ค่าที่แก้จะหายหลัง reload
3. secret เก็บเป็น hash ที่ถอดกลับไม่ได้ง่าย; password เก็บเป็นข้อความหรือ type 7 ที่ถอดได้
4. ตั้ง hostname + `ip domain-name` → `crypto key generate rsa modulus 2048` → `ip ssh version 2` → สร้าง username/secret → line vty: `login local`, `transport input ssh`
5. ปิด Telnet ที่ไม่เข้ารหัส และจำกัดให้เข้าได้เฉพาะจาก management network
6. เข้า interface แล้วสั่ง `no shutdown`
7. Data Link (L2) — เช่น encapsulation/keepalive ไม่ตรงกัน
8. ตั้ง IP ที่ `interface vlan <mgmt>` + `no shutdown` และใช้ `ip default-gateway <IP>`
9. `show running-config | section interface`
10. ถ้าแก้ผิดจนเข้าเครื่องไม่ได้ อุปกรณ์จะ reload กลับไปใช้ startup-config เดิมเองใน 10 นาที (ถ้าสำเร็จใช้ `reload cancel`)
</details>

---

➡️ ต่อไป: **Level 30 — วิธีการ Troubleshoot อย่างเป็นระบบ**
