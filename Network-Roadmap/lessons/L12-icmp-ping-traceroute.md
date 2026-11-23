# บทเรียน Level 12 — ICMP, ping, traceroute (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ ICMP และข้อความที่สำคัญ · อ่านผล ping/traceroute/mtr ได้ถูกต้อง · ไม่ตีความผิดเรื่อง "* * *" · รู้ว่าทำไมไม่ควร block ICMP ทั้งหมด

---

## 1. ICMP คืออะไร

**ICMP (Internet Control Message Protocol)** คือ **โปรโตคอลสำหรับส่งข้อความแจ้งสถานะและข้อผิดพลาด** ของ IP ทำงานในชั้น Network (L3) ร่วมกับ IP (IP protocol number = 1)

- ICMP **ไม่มี port** (ไม่ใช่ TCP/UDP)
- ใช้ทั้ง **ทดสอบการเชื่อมต่อ** (ping) และ **แจ้งปัญหา** (ส่งไม่ถึง, TTL หมด, packet ใหญ่เกิน)

> 💡 **เปรียบเทียบ:** ICMP คือ **ใบแจ้งจากไปรษณีย์** เช่น "ไม่พบผู้รับ", "ที่อยู่ไม่ถูกต้อง", "พัสดุใหญ่เกินกำหนด" ไม่ได้เป็นตัวพัสดุ แต่บอกว่าเกิดอะไรขึ้น

### ICMP Type ที่ต้องจำ

| Type | ชื่อ | ความหมาย |
|---|---|---|
| **0** | Echo Reply | ตอบ ping |
| **3** | Destination Unreachable | ส่งไม่ถึง (มีหลาย Code) |
| **5** | Redirect | router บอกว่ามีเส้นทางที่ดีกว่า |
| **8** | Echo Request | ping ออกไป |
| **11** | Time Exceeded | TTL หมดระหว่างทาง (traceroute ใช้) |

**Type 3 Code ที่เจอบ่อย:** 0 Network unreachable · 1 Host unreachable · 3 **Port unreachable** · **4 Fragmentation needed and DF set** (ใช้ใน PMTUD) · 13 Administratively prohibited (ถูก ACL/firewall ปฏิเสธ)

---

## 2. ping

ส่ง **Echo Request (Type 8)** แล้วรอ **Echo Reply (Type 0)** เพื่อทดสอบว่า **ไปถึงไหม** และ **ใช้เวลาไป-กลับ (RTT) เท่าไร**

```bash
ping 8.8.8.8                 # Windows ส่ง 4 ครั้ง, Linux ส่งไม่หยุด (Ctrl+C)
ping -c 10 8.8.8.8           # Linux ส่ง 10 ครั้ง
ping -t 8.8.8.8              # Windows ส่งไม่หยุด
ping -n 100 -l 1400 host     # Windows 100 ครั้ง ขนาด 1400 byte
ping -i 0.2 host             # Linux ทุก 0.2 วินาที
```

### อ่านผล
```
64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=12.4 ms
...
--- 8.8.8.8 ping statistics ---
10 packets transmitted, 10 received, 0% packet loss
rtt min/avg/max/mdev = 11.9/12.6/14.1/0.6 ms
```
- **time** = RTT · **packet loss** = % ที่หาย · **mdev** ≈ ความแกว่ง (jitter)
- **ttl** ที่ได้กลับมาเดาได้ว่าห่างกี่ hop และบางครั้งเดา OS ได้ (Linux เริ่ม 64, Windows 128, อุปกรณ์เครือข่ายมัก 255)

### ข้อความที่ต้องแยกให้ออก

| ข้อความ | ความหมาย | สาเหตุที่เป็นไปได้ |
|---|---|---|
| **Reply from ปลายทาง** | ✅ ถึงและตอบกลับ | — |
| **Request timed out** | ไม่มีคำตอบใด ๆ กลับมาภายในเวลา | ปลายทางปิด/firewall บล็อก ICMP/ทางกลับไม่มี route |
| **Destination host unreachable** | มีอุปกรณ์บอกว่าส่งไม่ถึง (บางครั้งเครื่องตัวเองแจ้ง) | ARP หาปลายทางไม่เจอในวงเดียวกัน, ไม่มี route |
| **Reply from 192.168.1.1: Destination host unreachable** | router 192.168.1.1 บอกว่าส่งต่อไม่ได้ | router ไม่มี route ไปปลายทาง |
| **TTL expired in transit** | packet วนจน TTL หมด | **routing loop** |
| **General failure / Transmit failed** | เครื่องตัวเองส่งไม่ออก | ไม่มี IP, NIC/ไดรเวอร์มีปัญหา, firewall ในเครื่อง |

### ลำดับการ ping เพื่อไล่ปัญหา
```
1) ping 127.0.0.1          → TCP/IP stack ในเครื่องปกติไหม
2) ping IP ของตัวเอง        → NIC/การตั้ง IP ปกติไหม
3) ping default gateway     → ออกจากเครื่องถึง router ได้ไหม (L1-L3 ในวง)
4) ping 8.8.8.8 / 1.1.1.1   → ออกอินเทอร์เน็ตได้ไหม
5) ping google.com          → DNS ทำงานไหม (ถ้าข้อ 4 ผ่านแต่ข้อ 5 ไม่ผ่าน = DNS)
```

> ⚠️ **ping ไม่ผ่าน ≠ เครื่องล่มเสมอไป** เช่น Windows Firewall ปิดรับ ping เป็นค่าเริ่มต้นในหลายกรณี, cloud server ปิด ICMP ไว้ ควรทดสอบ port ของบริการจริงประกอบด้วย (เช่น `Test-NetConnection host -Port 443`)

---

## 3. TTL และ traceroute

### TTL (Time To Live)
- field ใน IP header (8 บิต) ผู้ส่งตั้งค่าเริ่มต้น (เช่น 64/128)
- **router ทุกตัวลด TTL ลง 1** ถ้าเหลือ **0** จะ **ทิ้ง packet** และส่ง **ICMP Time Exceeded (Type 11)** กลับไปหาผู้ส่ง
- มีไว้ป้องกัน packet วนไม่สิ้นสุดเมื่อเกิด routing loop

### traceroute ทำงานอย่างไร

```
 ส่ง packet TTL=1 → router ตัวที่ 1 ลดเป็น 0 → ตอบ Time Exceeded → รู้ hop 1
 ส่ง packet TTL=2 → router ตัวที่ 2 ตอบ                         → รู้ hop 2
 ส่ง packet TTL=3 → ...                                          → รู้ hop 3
 ... จนถึงปลายทาง (ปลายทางตอบ Echo Reply หรือ Port Unreachable)
 ส่ง 3 ครั้งต่อ hop จึงเห็นเวลา 3 ค่า
```

| | Windows `tracert` | Linux/macOS `traceroute` |
|---|---|---|
| packet ที่ส่ง | ICMP Echo | **UDP** port สูง (ค่าเริ่มต้น), เลือก `-I` ICMP หรือ `-T` TCP ได้ |
| ปลายทางตอบ | Echo Reply | ICMP Port Unreachable |

```bash
tracert 8.8.8.8                    # Windows
tracert -d 8.8.8.8                 # ไม่ resolve ชื่อ (เร็วขึ้น)
traceroute -n 8.8.8.8              # Linux
traceroute -T -p 443 example.com   # ใช้ TCP 443 (ผ่าน firewall ได้ดีกว่า)
```

### อ่านผล traceroute
```
 1   1 ms   1 ms   1 ms  192.168.1.1        ← router บ้าน
 2   5 ms   4 ms   5 ms  100.64.0.1         ← ISP (CGNAT)
 3   *      *      *                        ← router นี้ไม่ตอบ ICMP (ไม่ใช่ปัญหาเสมอไป)
 4   8 ms   7 ms   9 ms  ix.example.net
 5  32 ms  31 ms  33 ms  sg-router...       ← เวลาเพิ่ม = ข้ามไปสิงคโปร์ (ระยะทาง)
 6  33 ms  32 ms  32 ms  8.8.8.8
```

**กฎการตีความที่สำคัญ**
1. **`* * *` ตรงกลาง แต่ hop ถัดไปตอบได้** → router นั้นแค่ไม่ตอบหรือจำกัดอัตราการตอบ ICMP **ไม่ใช่ปัญหา**
2. **`* * *` ต่อเนื่องจนจบ** → ทางถูกตัดหรือ firewall บล็อกตั้งแต่จุดนั้น (เป็นเบาะแสว่าปัญหาอยู่แถวนั้น)
3. **เวลาที่ hop กลางทางสูง แต่ hop ถัดไปปกติ** → router นั้นให้ความสำคัญกับการตอบ ICMP ต่ำ ไม่ใช่ปัญหา
4. **เวลาเพิ่มขึ้นแล้วสูงต่อเนื่องถึงปลายทาง** → จุดนั้นมีความหน่วงจริง (ระยะทางไกลหรือ congestion)
5. **IP ซ้ำวนไปมา** (A → B → A → B) → **routing loop**
6. เส้นทาง **ขาไปกับขากลับอาจไม่เหมือนกัน** (asymmetric) traceroute เห็นแค่ขาไป

---

## 4. mtr — ping + traceroute ต่อเนื่อง

`mtr` (Linux/macOS) หรือ `WinMTR`/`pathping` (Windows) ส่งต่อเนื่องไปทุก hop แล้วสรุป loss และเวลา เหมาะกับปัญหาเป็น ๆ หาย ๆ

```bash
mtr -rwc 100 8.8.8.8          # report 100 รอบ
pathping 8.8.8.8              # Windows (ช้า แต่มีในเครื่อง)
```
```
 Host               Loss%  Snt   Last   Avg  Best  Wrst StDev
 1. 192.168.1.1      0.0%  100    1.0   1.1   0.9   2.3   0.2
 2. 100.64.0.1       0.0%  100    5.2   5.0   4.1   9.8   0.8
 3. 10.10.10.1      60.0%  100    6.1   6.3   5.9   8.0   0.4   ← loss เฉพาะ hop นี้
 4. ix.example.net   0.0%  100    8.0   7.9   7.2   9.1   0.3   ← hop ถัดไปปกติ
 5. 8.8.8.8          0.0%  100   32.1  32.4  31.0  35.2   0.7
```
**กฎ:** loss ที่ hop กลางทางแต่ **ปลายทาง 0%** = router นั้นจำกัดการตอบ ICMP **ไม่ใช่ปัญหาจริง** ดูที่ loss ของ **ปลายทาง** เป็นหลัก

---

## 5. Path MTU Discovery (PMTUD) — เหตุผลที่ห้าม block ICMP ทั้งหมด

- เครื่องส่ง packet ขนาดใหญ่โดยตั้ง **DF (Don't Fragment)** ไว้
- ถ้าเจอลิงก์ที่ MTU เล็กกว่า (เช่น VPN, PPPoE 1492) router จะทิ้งแล้วส่ง **ICMP Type 3 Code 4 "Fragmentation needed"** บอกขนาดที่รับได้
- ผู้ส่งลดขนาด packet แล้วส่งใหม่

**ถ้า firewall block ICMP ทั้งหมด:** ผู้ส่งไม่เคยได้รับข้อความนั้น ส่ง packet ใหญ่ซ้ำแล้วหายไปเรื่อย ๆ → อาการ **"MTU black hole"**: ping ได้, เว็บบางเว็บโหลดได้บางส่วนแล้วค้าง, ไฟล์ใหญ่โอนไม่ได้, VPN ใช้งานแปลก ๆ

**แนวปฏิบัติ:** อนุญาต ICMP ที่จำเป็นอย่างน้อย Type 3 (โดยเฉพาะ Code 4), Type 11, Type 0/8 จากแหล่งที่เชื่อถือได้ และใช้ rate-limit แทนการ block ทั้งหมด (IPv6 ยิ่งต้องเปิด ICMPv6 เพราะ NDP พึ่ง ICMPv6)

---

## 6. ICMP กับความปลอดภัย

- **ICMP flood / Ping of death (เก่า) / Smurf attack** → ป้องกันด้วย rate-limit
- **การสำรวจเครือข่าย** ด้วย ping sweep → จำกัด ICMP จากอินเทอร์เน็ตเข้า (แต่ไม่ใช่ปิดทั้งหมด)
- **ICMP Redirect** ปลอมเปลี่ยนเส้นทางได้ → มักปิดรับบน host/router

---

## 7. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ping ไม่ได้ = เครื่องล่ม | อาจแค่ firewall บล็อก ICMP ให้ทดสอบ port ของบริการจริง |
| `* * *` ใน traceroute = จุดเสีย | ถ้า hop ถัดไปตอบได้ เป็นแค่ router ไม่ตอบ ICMP |
| ICMP ใช้ port | ไม่มี port |
| ปิด ICMP ทั้งหมดปลอดภัยกว่า | ทำให้ PMTUD พัง และ troubleshoot ยาก |
| traceroute แสดงเส้นทางทั้งไปและกลับ | แสดงเฉพาะขาไป |

---

## 8. Cheat Sheet

```
ICMP = แจ้งสถานะ/ข้อผิดพลาดของ IP · ไม่มี port · IP protocol 1
Type 0 Echo Reply · 3 Unreachable (code 4 = Frag needed) · 8 Echo Request · 11 Time Exceeded
ping: 127.0.0.1 → IP ตัวเอง → gateway → 8.8.8.8 → ชื่อโดเมน
Timed out = ไม่มีคำตอบ · Unreachable = มีคนบอกว่าไปไม่ถึง · TTL expired = loop
traceroute = ส่ง TTL 1,2,3... รับ Time Exceeded · Win=ICMP · Linux=UDP
* * * กลางทาง (hop ถัดไปตอบ) = ไม่ใช่ปัญหา · loss ดูที่ปลายทาง
อย่า block ICMP ทั้งหมด → MTU black hole
```

---

## 9. แบบทดสอบ 10 ข้อ

1. ICMP Type 8 และ Type 0 คืออะไร
2. "Request timed out" ต่างจาก "Destination host unreachable" อย่างไร
3. ping 8.8.8.8 ได้ แต่ ping google.com ไม่ได้ ปัญหาอยู่ที่ไหน
4. traceroute ใช้ field อะไรของ IP และข้อความ ICMP ใด
5. traceroute บน Linux กับ Windows ส่ง packet ต่างกันอย่างไร
6. traceroute hop 4 เป็น `* * *` แต่ hop 5–8 ตอบปกติถึงปลายทาง แปลว่าอะไร
7. mtr แสดง loss 40% ที่ hop 3 แต่ปลายทาง loss 0% ควรสรุปว่าอย่างไร
8. "TTL expired in transit" บอกปัญหาอะไร
9. ทำไมการ block ICMP ทั้งหมดที่ firewall ทำให้บางเว็บค้าง
10. server บน cloud ping ไม่ได้ จะตรวจว่าเว็บยังทำงานอยู่อย่างไร

<details><summary><b>เฉลย</b></summary>

1. Type 8 = Echo Request (ping ออก), Type 0 = Echo Reply (ตอบกลับ)
2. Timed out = ไม่มีคำตอบใดกลับมา; Unreachable = มีอุปกรณ์ (หรือเครื่องตัวเอง) แจ้งว่าส่งไปไม่ถึง
3. DNS
4. TTL; ICMP Time Exceeded (Type 11)
5. Windows ใช้ ICMP Echo; Linux ใช้ UDP port สูงเป็นค่าเริ่มต้น
6. router hop 4 ไม่ตอบ ICMP (หรือจำกัดอัตรา) — ไม่ใช่ปัญหา
7. hop 3 แค่จำกัดการตอบ ICMP ไม่มี loss จริงถึงปลายทาง
8. Routing loop (packet วนจน TTL หมด)
9. PMTUD ใช้ ICMP Type 3 Code 4 เมื่อถูกบล็อก ผู้ส่งไม่รู้ว่าต้องลดขนาด packet → packet ใหญ่หายตลอด (MTU black hole)
10. ทดสอบ port ของบริการ เช่น `curl -I https://...`, `Test-NetConnection host -Port 443`, `nc -zv host 443`
</details>

---

➡️ ต่อไป: **Level 13 — TCP**
