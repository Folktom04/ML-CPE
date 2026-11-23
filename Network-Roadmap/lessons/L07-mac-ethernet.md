# บทเรียน Level 7 — MAC Address & Ethernet Frame (ฉบับละเอียด)

> อ่านจบแล้วจะ: อ่าน MAC address ได้ · แยก unicast/multicast/broadcast · อ่านทุก field ของ Ethernet frame · เข้าใจ MTU, duplex และปัญหาที่พบบ่อยในชั้น Data Link

---

## 1. MAC Address คืออะไร

**MAC (Media Access Control) Address** คือ **ที่อยู่ประจำการ์ดเครือข่าย (NIC)** ใช้ระบุอุปกรณ์ **ภายในเครือข่ายเดียวกัน (Layer 2)**

- ยาว **48 บิต = 6 byte** เขียนเป็น hex 12 ตัว
- รูปแบบการเขียน (ค่าเดียวกัน):
  - `00:1A:2B:3C:4D:5E` (Linux/macOS)
  - `00-1A-2B-3C-4D-5E` (Windows)
  - `001a.2b3c.4d5e` (Cisco)
- บางครั้งเรียก Physical address, Hardware address, BIA (Burned-In Address)

> 💡 **เปรียบเทียบ:** MAC = **เลขบัตรประชาชน** (ติดตัวอุปกรณ์ ใช้ระบุตัว) ส่วน IP = **ที่อยู่บ้าน** (เปลี่ยนตามที่อยู่) ไปรษณีย์ใช้ที่อยู่ส่งข้ามเมือง แต่ส่งถึงมือคนในบ้านโดยเรียกชื่อ

### โครงสร้าง MAC

```
   00 : 1A : 2B   :   3C : 4D : 5E
  └──── OUI ────┘   └── NIC Specific ──┘
   24 บิตแรก           24 บิตหลัง
   รหัสผู้ผลิต          เลขเฉพาะของการ์ด
   (IEEE แจกให้)        (ผู้ผลิตกำหนด)
```

- **OUI (Organizationally Unique Identifier):** บอกยี่ห้อผู้ผลิต เช่น ค้นหา OUI ได้ว่าเป็น Cisco, Dell, Apple, Intel
- **ประโยชน์ในงาน:** เห็น MAC แปลกในเครือข่ายก็ค้น OUI ได้ทันทีว่าเป็นอุปกรณ์ยี่ห้ออะไร

### บิตพิเศษในไบต์แรก

```
 ไบต์แรก:  x x x x x x  b1  b0
                         │   └─ I/G bit: 0 = Unicast, 1 = Multicast/Group
                         └───── U/L bit: 0 = Global (จากโรงงาน), 1 = Local (ตั้งเอง/สุ่ม)
```

---

## 2. ประเภทของ MAC ปลายทาง

| ประเภท | ส่งถึงใคร | ลักษณะ | ตัวอย่าง |
|---|---|---|---|
| **Unicast** | เครื่องเดียว | บิตสุดท้ายของไบต์แรก = 0 | `00:1A:2B:3C:4D:5E` |
| **Multicast** | กลุ่มที่สมัครรับ | บิตสุดท้ายของไบต์แรก = 1 | `01:00:5E:xx:xx:xx` (IPv4 multicast), `33:33:xx:xx:xx:xx` (IPv6), `01:80:C2:00:00:00` (STP) |
| **Broadcast** | ทุกเครื่องในเครือข่าย | ทุกบิตเป็น 1 | **`FF:FF:FF:FF:FF:FF`** |

---

## 3. Ethernet Frame — โครงสร้าง

```
┌──────────┬─────┬──────────┬──────────┬──────────┬───────────────────┬──────┐
│ Preamble │ SFD │  Dst MAC │  Src MAC │ EtherType│     Payload       │ FCS  │
│  7 byte  │  1  │  6 byte  │  6 byte  │  2 byte  │  46 – 1500 byte   │  4   │
└──────────┴─────┴──────────┴──────────┴──────────┴───────────────────┴──────┘
 └─ L1 (ซิงก์สัญญาณ) ─┘ └────────────── Ethernet Frame (64 – 1518 byte) ─────────┘
```

| Field | ขนาด | หน้าที่ |
|---|---|---|
| **Preamble + SFD** | 8 byte | รูปแบบ 1010... ให้ผู้รับซิงก์สัญญาณ และบอกว่า frame กำลังจะเริ่ม (ไม่แสดงใน Wireshark) |
| **Destination MAC** | 6 byte | ส่งถึงใคร (อยู่ก่อน source เพื่อให้ switch ตัดสินใจได้เร็ว) |
| **Source MAC** | 6 byte | ใครส่ง (switch ใช้เรียนรู้ตาราง MAC) |
| **EtherType** | 2 byte | บอกว่าข้างในเป็นโปรโตคอลอะไร |
| **Payload** | 46–1500 byte | ข้อมูลจากชั้นบน (เช่น IP packet) ถ้าน้อยกว่า 46 จะเติม padding |
| **FCS** | 4 byte | ค่า CRC สำหรับตรวจความเสียหาย ถ้าคำนวณไม่ตรง ผู้รับจะ **ทิ้ง frame** |

### EtherType ที่ต้องจำ

| ค่า | โปรโตคอล |
|---|---|
| `0x0800` | IPv4 |
| `0x86DD` | IPv6 |
| `0x0806` | ARP |
| `0x8100` | VLAN tag (802.1Q) |
| `0x88CC` | LLDP |
| `0x8847` | MPLS |

### Frame ที่มี VLAN Tag (802.1Q)
มีการแทรก tag 4 byte ระหว่าง Source MAC กับ EtherType ภายในมี **VLAN ID 12 บิต** (1–4094) และ **Priority (CoS) 3 บิต** (รายละเอียดใน Level 33)

---

## 4. MTU — ขนาดสูงสุดของ Payload

- **MTU (Maximum Transmission Unit) ของ Ethernet = 1500 byte** (ขนาด IP packet สูงสุดที่ใส่ได้ใน frame เดียว)
- **Jumbo Frame:** MTU ประมาณ **9000 byte** ใช้ใน Data Center/storage network เพื่อลดภาระ CPU และเพิ่ม throughput **ต้องตั้งเท่ากันทุกอุปกรณ์ตลอดเส้นทาง**
- packet ใหญ่เกิน MTU → ต้องแบ่งย่อย (fragment) หรือถูกทิ้ง (เมื่อห้าม fragment)
- **ทดสอบ MTU:**
```bash
# Linux: 1472 + header IP 20 + ICMP 8 = 1500
ping -M do -s 1472 8.8.8.8
# Windows
ping -f -l 1472 8.8.8.8
```
ถ้า 1472 ผ่าน แต่ 1473 ไม่ผ่าน แสดงว่า MTU ของเส้นทางคือ 1500

---

## 5. Duplex และ Speed

- **Half-duplex:** ส่งหรือรับได้ทีละทาง (เหมือนวิทยุสื่อสาร) ใช้กับ hub ซึ่งมีการชนกัน
- **Full-duplex:** ส่งและรับพร้อมกัน (เหมือนโทรศัพท์) ใช้กับ switch ไม่มีการชน
- **Auto-negotiation:** ทั้งสองฝั่งตกลง speed/duplex กันเอง ควรเปิดไว้ทั้งสองฝั่ง
- **Duplex mismatch:** ฝั่งหนึ่ง full อีกฝั่ง half (มักเกิดเพราะฝั่งหนึ่งตั้งค่าตายตัว อีกฝั่ง auto) ทำให้
  - ช้าลงมาก แต่ยังใช้งานได้ จึงหาสาเหตุยาก
  - counter ของ **late collision** และ **CRC/FCS error** เพิ่มขึ้น
  - แก้: ตั้งทั้งสองฝั่งเป็น auto หรือตั้งตายตัวให้ตรงกันทั้งสองฝั่ง

```bash
ethtool eth0                      # Linux: ดู speed/duplex
show interfaces gi0/1             # Cisco: ดู duplex, errors, CRC
```

---

## 6. MAC ในชีวิตจริง

### ดู MAC ของเครื่อง
```bash
ipconfig /all        # Windows (Physical Address)
ip link              # Linux (link/ether)
ifconfig en0         # macOS (ether)
```

### MAC Randomization (Private Wi-Fi Address)
- iOS, Android, Windows รุ่นใหม่ **สุ่ม MAC** ต่อเครือข่าย Wi-Fi เพื่อความเป็นส่วนตัว (ป้องกันการติดตามตัว)
- **ผลกระทบต่อองค์กร:** ระบบที่จองสิทธิ์หรือ IP ตาม MAC (MAC filtering, DHCP reservation, captive portal ที่จำเครื่อง) จะจำอุปกรณ์ไม่ได้ ควรใช้การยืนยันตัวตนแบบ 802.1X แทน

### MAC ปลอมได้ไหม?
ได้ง่ายมาก (MAC spoofing) จึง **ไม่ควรใช้ MAC เป็นการยืนยันตัวตนเพียงอย่างเดียว**

### MAC ไม่ข้าม Router
MAC ใช้ได้เฉพาะภายในเครือข่ายเดียวกัน เมื่อ packet ผ่าน router จะถูกห่อด้วย frame ใหม่ที่มี MAC ใหม่ทุก hop

---

## 7. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| MAC ไม่ซ้ำกันแน่นอนและเปลี่ยนไม่ได้ | เปลี่ยนได้ด้วยซอฟต์แวร์ และมือถือสุ่มเองด้วย |
| รู้ MAC ของเว็บไซต์ปลายทางได้ | MAC ไม่ข้าม router; เห็นได้แค่ MAC ของ gateway |
| MTU ยิ่งใหญ่ยิ่งเร็วเสมอ | ต้องเท่ากันทั้งเส้นทาง ไม่งั้นเกิดปัญหา packet หาย |
| Duplex mismatch ทำให้ใช้งานไม่ได้เลย | ยังใช้ได้แต่ช้าและ error สูง จึงหายาก |

---

## 8. Cheat Sheet

```
MAC = 48 บิต = 6 byte = 12 hex · OUI 24 บิตแรก = ผู้ผลิต
Broadcast FF:FF:FF:FF:FF:FF · Multicast: บิตสุดท้ายไบต์แรก = 1 (01:00:5E, 33:33)
Frame: Preamble | Dst MAC | Src MAC | EtherType | Payload 46-1500 | FCS(CRC)
EtherType: 0800 IPv4 · 86DD IPv6 · 0806 ARP · 8100 VLAN
MTU 1500 · Jumbo 9000 (ต้องเท่ากันทั้งเส้นทาง) · ทดสอบ ping -M do -s 1472
Duplex mismatch = ช้า + late collision + CRC error
```

---

## 9. แบบทดสอบ 10 ข้อ

1. MAC address มีกี่บิต และส่วน OUI บอกอะไร
2. `FF:FF:FF:FF:FF:FF` คือ MAC ประเภทใด
3. `01:00:5E:00:00:05` เป็น unicast หรือ multicast เพราะอะไร
4. EtherType `0x0806` คือโปรโตคอลอะไร
5. ทำไม Destination MAC อยู่ก่อน Source MAC ใน frame
6. FCS ใช้ทำอะไร และถ้าตรวจไม่ผ่านจะเกิดอะไรขึ้น
7. MTU มาตรฐานของ Ethernet คือเท่าไร และ Jumbo frame ประมาณเท่าไร
8. คำสั่ง ping ทดสอบว่าเส้นทางรองรับ MTU 1500 บน Linux
9. อาการของ duplex mismatch
10. ทำไมระบบ Wi-Fi องค์กรที่จำอุปกรณ์จาก MAC จึงมีปัญหากับมือถือรุ่นใหม่

<details><summary><b>เฉลย</b></summary>

1. 48 บิต; OUI (24 บิตแรก) บอกผู้ผลิต
2. Broadcast
3. Multicast — บิตสุดท้ายของไบต์แรก (0x01 = 00000001) เป็น 1
4. ARP
5. ให้ switch อ่านปลายทางได้ก่อนและเริ่มตัดสินใจส่งต่อได้เร็ว
6. ตรวจความเสียหายของ frame ด้วย CRC — ไม่ผ่านจะถูกทิ้ง (นับเป็น CRC/FCS error)
7. 1500 byte; ประมาณ 9000 byte
8. `ping -M do -s 1472 <ปลายทาง>`
9. ช้ามาก, late collision และ CRC error เพิ่มขึ้น แต่ link ยัง up
10. มือถือสุ่ม MAC (private address) ต่อเครือข่าย ระบบจึงจำอุปกรณ์เดิมไม่ได้
</details>

---

➡️ ต่อไป: **Level 8 — IPv4 Addressing**
