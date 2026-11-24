# อธิบายละเอียด: Ping, Traceroute, Route, DNS และการทดสอบ Port

> คู่กับ cheat sheet [01-ping-traceroute-route.md](../01-ping-traceroute-route.md)
> อ่านจบแล้วจะ: เข้าใจว่าแต่ละคำสั่ง "ทำงานอย่างไรเบื้องหลัง" · อ่านผลลัพธ์ได้ทีละบรรทัด · รู้ว่าผลแบบไหนแปลว่าปัญหาอยู่ตรงไหน · เลือกคำสั่งให้เหมาะกับอาการ

---

## 1. ภาพรวม: ทำไมต้องเริ่มจากเครื่องผู้ใช้

ลองนึกถึงการส่งพัสดุ:
```
 [บ้านเรา] → [ป้อมยาม/ประตูหมู่บ้าน] → [ไปรษณีย์ในอำเภอ] → [ศูนย์คัดแยก] → ... → [บ้านผู้รับ]
 [เครื่องผู้ใช้] → [Gateway]        → [Firewall/Router]  → [ISP]          → ... → [Server]
```
ถ้าพัสดุไม่ถึง เราไล่ถามทีละจุดว่า "ผ่านจุดนี้ไปหรือยัง" — คำสั่งในบทนี้คือเครื่องมือ "ถามทีละจุด"

| คำสั่ง | เปรียบเหมือน | ตอบคำถาม |
|---|---|---|
| `ipconfig` / `ip a` | ดูว่าบ้านเรามีเลขที่บ้านไหม | เครื่องมี IP/gateway/DNS ถูกต้องไหม |
| `ping` | ตะโกนถาม "ได้ยินไหม" | ปลายทางตอบกลับไหม ใช้เวลาเท่าไร |
| `traceroute` | ถามทุกจุดระหว่างทาง | พัสดุผ่านจุดไหนบ้าง ติดตรงไหน |
| `route` | ดูแผนที่ว่าจะไปทางไหน | เครื่องจะส่งออกทางไหน |
| `nslookup` / `dig` | เปิดสมุดโทรศัพท์ | ชื่อเว็บนี้คือ IP อะไร |
| `Test-NetConnection` / `nc` | เคาะประตูห้องที่ต้องการ | บริการ (port) นั้นเปิดรับไหม |

---

## 2. ดูการตั้งค่าเครื่อง: `ipconfig /all` (Windows)

### ตัวอย่างผลลัพธ์
```
Ethernet adapter Ethernet:
   Description . . . . . . . . . . . : Intel(R) Ethernet Connection I219-LM
   Physical Address. . . . . . . . . : 3C-52-82-1A-2B-3C        ← (1) MAC address
   DHCP Enabled. . . . . . . . . . . : Yes                       ← (2) ได้ IP จาก DHCP
   IPv4 Address. . . . . . . . . . . : 10.0.20.55(Preferred)     ← (3) IP ของเครื่อง
   Subnet Mask . . . . . . . . . . . : 255.255.255.0             ← (4) ขนาดวง (/24)
   Lease Obtained. . . . . . . . . . : 24 November 2026 08:01:12
   Default Gateway . . . . . . . . . : 10.0.20.1                 ← (5) ประตูออกนอกวง
   DHCP Server . . . . . . . . . . . : 10.0.104.10               ← (6) ใครแจก IP
   DNS Servers . . . . . . . . . . . : 10.0.104.11               ← (7) ใช้ DNS ตัวไหน
                                       10.0.104.12
```
### อธิบายทีละจุด
1. **MAC address** — "เลขประจำตัว" ของการ์ดแลน ใช้ตามหาว่าเครื่องเสียบอยู่ที่พอร์ตไหนของ switch
2. **DHCP Enabled: Yes** — ได้ IP อัตโนมัติ (ถ้า No = ตั้ง IP เอง อาจตั้งผิด)
3. **IPv4 Address** — ต้องอยู่ในวงเดียวกับ gateway เช่น 10.0.20.x
4. **Subnet mask** — บอกว่าเครื่องไหน "อยู่วงเดียวกัน" (คุยตรงได้) เครื่องไหนต้องส่งผ่าน gateway
5. **Default Gateway** — ทุกอย่างที่ไม่อยู่ในวงเดียวกันจะถูกส่งมาที่นี่ (ถ้าว่าง = ออกนอกวงไม่ได้เลย)
6. **DHCP Server** — ถ้าแจก IP ผิดวง ให้ตามที่ตัวนี้
7. **DNS Servers** — ถ้าเข้าเว็บด้วยชื่อไม่ได้แต่ด้วย IP ได้ ปัญหามักอยู่ที่ตัวนี้

### สัญญาณผิดปกติที่เห็นบ่อย
| เห็น | แปลว่า | สาเหตุที่พบบ่อย |
|---|---|---|
| IP `169.254.x.x` | **ขอ IP จาก DHCP ไม่สำเร็จ** Windows เลยตั้งให้เอง | สายหลุด, พอร์ตอยู่ VLAN ผิด, DHCP pool เต็ม, ไม่มี DHCP relay, ไม่ผ่าน 802.1X |
| IP ไม่ตรงวงกับที่ควรเป็น (เช่น ได้ 192.168.1.x) | ได้ IP จาก DHCP "เถื่อน" | มีคนเสียบ router บ้านเข้ากับเครือข่าย |
| Default Gateway ว่าง | ออกนอกวงไม่ได้ | ตั้ง IP เองแล้วลืมใส่ / DHCP ไม่ได้แจก option 3 |
| DNS เป็น `8.8.8.8` ในองค์กร | ใช้ DNS ภายนอก | เข้าเว็บภายใน (เช่น intranet.corp) ไม่ได้ |
| มีหลาย adapter มี gateway หลายตัว | อาจออกผิดทาง | Wi-Fi + LAN พร้อมกัน, VPN client |

---

## 3. Ping — ทำงานอย่างไร

### เบื้องหลัง
ping ส่ง **ICMP Echo Request** ไปยังปลายทาง ถ้าปลายทางได้รับและอนุญาต จะส่ง **ICMP Echo Reply** กลับมา
```
 เครื่องเรา ── Echo Request ──► ปลายทาง
 เครื่องเรา ◄── Echo Reply ───  ปลายทาง
 เวลาไป-กลับ = RTT (Round Trip Time) ที่แสดงเป็น time=..ms
```
**สำคัญ:** ping ทดสอบ **ทั้งขาไปและขากลับ** — ถ้าขากลับไม่มี route ก็ timeout ได้ แม้ขาไปถึงแล้ว

### ตัวอย่างผลปกติ
```
C:\> ping 8.8.8.8
Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=14ms TTL=117
Reply from 8.8.8.8: bytes=32 time=13ms TTL=117
Reply from 8.8.8.8: bytes=32 time=15ms TTL=117
Reply from 8.8.8.8: bytes=32 time=14ms TTL=117

Ping statistics for 8.8.8.8:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 13ms, Maximum = 15ms, Average = 14ms
```
| ส่วน | ความหมาย |
|---|---|
| `bytes=32` | ขนาดข้อมูลที่ส่ง (Windows ค่าเริ่มต้น 32, Linux 56) |
| `time=14ms` | RTT — ภายใน LAN ปกติ < 1–2 ms · ในประเทศ 5–30 ms · ต่างประเทศใกล้ ๆ 30–80 ms · ข้ามทวีป 150–300 ms |
| `TTL=117` | ค่า TTL ที่เหลือเมื่อมาถึง (ดูหัวข้อถัดไป) |
| `Lost = 0 (0% loss)` | ไม่หาย — ถ้ามี loss แม้ 1–2% ก็ทำให้วิดีโอคอลกระตุก/TCP ช้าได้ |
| Min/Max/Average | ถ้า Max ห่างจาก Min มาก = **jitter** สูง (ไม่เสถียร) |

### TTL คืออะไร และบอกอะไรเรา
**TTL (Time To Live)** = ตัวเลขใน packet ที่ **ลดลง 1 ทุกครั้งที่ผ่าน router** ถ้าเหลือ 0 router จะทิ้ง packet (ป้องกันวนไม่รู้จบ)
- แต่ละ OS ตั้งค่าเริ่มต้นต่างกัน: Linux/macOS/อุปกรณ์หลายรุ่น **64**, Windows **128**, อุปกรณ์เครือข่ายบางรุ่น **255**
- `TTL=117` → ค่าเริ่มต้นที่ใกล้ที่สุดที่สูงกว่า 117 คือ 128 จึงน่าจะเริ่มที่ 128 และผ่านมา 11 hop — ใช้คะเนได้คร่าว ๆ ว่าปลายทางเป็นอะไรและไกลกี่ hop (server ใหญ่บางแห่งตั้งค่าเอง จึงเป็นแค่การคาดเดา)

### ผลผิดปกติแบบต่าง ๆ — อธิบายให้เห็นภาพ

**① Request timed out**
```
Request timed out.
Request timed out.
```
ส่งไปแล้ว **ไม่มีอะไรตอบกลับมาเลยภายใน 4 วินาที** เป็นไปได้หลายอย่าง:
- ปลายทางปิดเครื่อง / ไม่มีเครื่องนี้
- **Firewall บล็อก ICMP** (Windows Firewall บล็อก ping ขาเข้าเป็นค่าเริ่มต้นในหลายโปรไฟล์!)
- ขาไปถึงแต่ **ขากลับไม่มี route**
→ ต่อด้วย traceroute และทดสอบ port (ข้อ 7) ก่อนสรุปว่า "เครื่องดับ"

**② Destination host unreachable**
```
Reply from 10.0.20.55: Destination host unreachable.     ← มาจาก IP ของเครื่องเราเอง
```
- ถ้า "Reply from" เป็น **IP ของเครื่องเราเอง** → เครื่องเราพยายามหา MAC ของปลายทาง (ARP) ในวงเดียวกันแล้ว **ไม่มีใครตอบ** → ปลายทางไม่อยู่ในวง/ปิดอยู่/VLAN คนละวง
- ถ้า "Reply from" เป็น **IP ของ router** → router รู้ทางแล้วแต่หาเครื่องปลายทางในวงสุดท้ายไม่เจอ
→ จุดสำคัญ: **มีคนตอบ** (ต่างจาก timeout) จึงบอกตำแหน่งปัญหาได้ชัดกว่า

**③ TTL expired in transit**
```
Reply from 10.0.0.2: TTL expired in transit.
```
packet วนอยู่ระหว่าง router จน TTL หมด → **routing loop** (เช่น router A ชี้ไป B, B ชี้กลับ A) → traceroute จะเห็น IP สลับซ้ำไปมา

**④ General failure / Transmit failed**
เครื่องเรา **ส่งไม่ออกเลย** — สายไม่เสียบ, adapter ปิด, ไม่มี route, firewall บนเครื่องบล็อก

**⑤ Ping request could not find host www.xyz.com**
ยังไม่ได้ส่ง ping เลย เพราะ **แปลงชื่อเป็น IP ไม่ได้** → ปัญหา DNS (ข้อ 6)

**⑥ ผลปนกัน (บางอันได้ บางอันหาย)**
```
Reply from 10.40.1.5: time=35ms
Request timed out.
Reply from 10.40.1.5: time=210ms
Reply from 10.40.1.5: time=38ms
```
มี **packet loss + latency แกว่ง** → ลิงก์เต็ม (congestion), Wi-Fi สัญญาณอ่อน/คลื่นรบกวน, สาย/SFP เสีย → ใช้ `ping -t` หรือ `mtr` ดูนาน ๆ และดู error counter บนอุปกรณ์

### ping ทดสอบ MTU — ทำไมสำคัญ
**MTU** = ขนาด packet ใหญ่สุดที่ส่งได้บนลิงก์ (Ethernet ปกติ 1500 bytes) แต่ถ้าผ่าน VPN/PPPoE จะเล็กลง (เพราะต้องห่อ header เพิ่ม)
```
C:\> ping -f -l 1472 10.40.1.5        (-f = ห้ามแบ่งชิ้น, -l = ขนาดข้อมูล)
Packet needs to be fragmented but DF set.     ← ใหญ่เกินกว่าที่เส้นทางรับได้

C:\> ping -f -l 1400 10.40.1.5
Reply from 10.40.1.5: bytes=1400 time=22ms TTL=62   ← ขนาดนี้ผ่าน
```
ทำไม 1472: ข้อมูล 1472 + ICMP header 8 + IP header 20 = **1500 พอดี**
**อาการของปัญหา MTU:** ping ปกติ (32 bytes) ผ่าน, เปิดเว็บบางเว็บได้บางเว็บค้าง, login ได้แต่โหลดหน้าใหญ่ไม่ขึ้น, ส่งไฟล์ใหญ่ค้าง → ลดขนาดทีละน้อยจนผ่าน จะรู้ MTU จริงของเส้นทาง แล้วให้ทีม network ตั้ง **TCP MSS** บน VPN/router

---

## 4. Traceroute — ดูเส้นทางทีละ Hop

### เบื้องหลัง (ใช้ TTL อย่างฉลาด)
```
 ส่ง packet TTL=1 → router ตัวที่ 1 ลด TTL เป็น 0 → ทิ้ง และส่ง "TTL expired" กลับ → รู้ว่า hop 1 คือใคร
 ส่ง packet TTL=2 → ผ่าน router 1 ไปตายที่ router 2 → รู้ hop 2
 ส่ง TTL=3, 4, ... จนถึงปลายทาง
```
แต่ละ hop ส่ง 3 ครั้ง จึงเห็นเวลา 3 ค่า

### ตัวอย่างผลลัพธ์
```
C:\> tracert -d 8.8.8.8
Tracing route to 8.8.8.8 over a maximum of 30 hops
  1    <1 ms    <1 ms    <1 ms  10.0.20.1         ← gateway (core switch/firewall ภายใน)
  2     1 ms     1 ms     1 ms  10.0.0.254        ← firewall
  3     3 ms     2 ms     3 ms  203.0.113.1       ← router ของ ISP (หน้าบ้าน)
  4     *        *        *     Request timed out. ← router ที่ไม่ตอบ traceroute (ปกติ)
  5     5 ms     5 ms     6 ms  198.51.100.9      ← backbone ISP
  6    14 ms    13 ms    14 ms  8.8.8.8           ← ถึงปลายทาง
Trace complete.
```
### อ่านอย่างไร
- **hop 1 ควรเป็น gateway ของเรา** — ถ้าไม่ใช่ (เช่นเป็น 192.168.1.1 ของ router เถื่อน หรือ IP ของ VPN) แปลว่าออกผิดทาง
- **`* * *` แล้ว hop ถัดไปตอบตามปกติ** = router ตัวนั้นแค่ "ไม่ตอบ" traceroute (ตั้งค่าไว้เพื่อความปลอดภัย/ลดภาระ) **ไม่ใช่ปัญหา**
- **`* * *` ตั้งแต่ hop หนึ่งไปจนครบ 30 hop** = traffic หายตั้งแต่จุดนั้น (firewall บล็อก, ไม่มี route ต่อ) หรือปลายทางไม่ตอบ ICMP
- **latency กระโดดแล้วสูงค้างไปถึงปลายทาง** เช่น hop 5 = 5 ms, hop 6 = 180 ms, hop 7 = 182 ms → ช่วง 5→6 คือลิงก์ที่ช้า (อาจเป็นลิงก์ต่างประเทศ — ปกติ หรือ congestion — ผิดปกติ)
- **latency สูงเฉพาะ hop เดียว** แต่ hop ถัดไปกลับต่ำ → router ตัวนั้นตอบ traceroute ช้าเพราะให้ความสำคัญต่ำ (ไม่ใช่ปัญหา)
- **IP วนซ้ำ** (10.0.0.1 → 10.0.0.2 → 10.0.0.1 → 10.0.0.2 ...) = **routing loop**

> `-d` (Windows) / `-n` (Linux) = ไม่ต้องแปลง IP เป็นชื่อ ทำให้เร็วขึ้นมาก

### mtr / pathping — traceroute + ping ต่อเนื่อง (ดีที่สุดสำหรับปัญหาเป็นพัก ๆ)
```
$ mtr -rwbzc 100 8.8.8.8
HOST                         Loss%   Snt   Last   Avg  Best  Wrst StDev
1. 10.0.20.1                  0.0%   100    0.4   0.5   0.3   1.2   0.1
2. 10.0.0.254                 0.0%   100    1.1   1.0   0.8   2.0   0.2
3. 203.0.113.1                0.0%   100    3.0   3.1   2.5   9.8   0.9
4. 198.51.100.5              40.0%   100    5.2   5.5   4.9   7.1   0.4   ← loss เฉพาะ hop นี้
5. 198.51.100.9               0.0%   100    5.8   5.9   5.2   8.0   0.5
6. 8.8.8.8                    0.0%   100   14.1  14.3  13.5  20.2   0.8   ← ปลายทาง 0% = ปกติ
```
**กฎทอง:** ดู **loss ที่ปลายทาง** เป็นหลัก
- hop 4 loss 40% แต่ hop 5–6 = 0% → hop 4 แค่ **จำกัดการตอบ ICMP** (rate-limit) **ไม่ใช่ปัญหาจริง**
- ถ้า loss เริ่มที่ hop 4 **และต่อเนื่องถึงปลายทาง** (hop 4 = 10%, 5 = 10%, 6 = 10%) → ปัญหาจริงเริ่มที่ลิงก์ก่อนถึง hop 4
- **StDev สูง** = jitter สูง

---

## 5. Routing Table ของเครื่อง — เครื่องเลือกทางอย่างไร

### หลักการ
ทุกเครื่องมี "แผนที่" บอกว่าปลายทางแต่ละวงต้องส่งออกทางไหน และใช้กฎ **Longest Prefix Match** = เลือก route ที่ **เจาะจงที่สุด** (prefix ยาวที่สุด) ที่ครอบคลุมปลายทาง
```
 ปลายทาง 10.20.1.5
   route 0.0.0.0/0  (ทุกที่)            ← ครอบคลุม แต่กว้างสุด
   route 10.0.0.0/8 (ผ่าน VPN)         ← เจาะจงกว่า
   route 10.20.0.0/16 (ผ่าน LAN)       ← เจาะจงที่สุด → ถูกเลือก ✅
```

### ตัวอย่าง `route print` (Windows) — ส่วนสำคัญ
```
IPv4 Route Table
===========================================================================
Network Destination        Netmask          Gateway       Interface  Metric
          0.0.0.0          0.0.0.0        10.0.20.1      10.0.20.55     25   ← default route (ทุกที่ที่ไม่รู้จัก)
        10.0.20.0    255.255.255.0         On-link       10.0.20.55    281   ← วงของตัวเอง ส่งตรง ไม่ผ่าน gateway
        10.64.0.0      255.255.0.0      10.64.0.1      10.64.5.20      5   ← route ที่ VPN client เพิ่มให้
        127.0.0.0        255.0.0.0         On-link        127.0.0.1    331   ← loopback ของเครื่อง
```
| คอลัมน์ | ความหมาย |
|---|---|
| Network Destination + Netmask | วงปลายทาง |
| Gateway | ส่งให้ใคร (`On-link` = อยู่วงเดียวกัน ส่งตรง) |
| Interface | ส่งออกจาก IP/การ์ดไหนของเครื่อง |
| Metric | ถ้ามี route เจาะจงเท่ากันหลายอัน ค่าน้อยกว่าชนะ |

### คำสั่งที่มีประโยชน์ที่สุด: ถามว่า "ไป IP นี้ใช้ทางไหน"
```
$ ip route get 10.20.1.5
10.20.1.5 via 10.0.20.1 dev eth0 src 10.0.20.55
          └ ส่งให้ gateway นี้  └ ออกการ์ดนี้  └ ใช้ IP ต้นทางนี้
```
```
PS> Find-NetRoute -RemoteIPAddress 10.20.1.5 | Select-Object -Last 1
```
### ปัญหาที่พบบ่อย
| อาการ | สาเหตุ |
|---|---|
| ต่อ VPN แล้วเข้าระบบในออฟฟิศไม่ได้ | VPN ใช้ subnet ซ้ำกับวงที่บ้าน (เช่น 192.168.1.0/24 ทั้งคู่) → เครื่องเลือก on-link ที่บ้าน |
| เสียบ LAN + Wi-Fi พร้อมกัน แล้วบางเว็บช้า/เข้าไม่ได้ | มี default route สองอัน เลือกผิดการ์ด |
| ต่อ VPN แล้วอินเทอร์เน็ตช้ามาก | VPN แบบ full tunnel ดึง 0.0.0.0/0 ทั้งหมดไปที่ออฟฟิศ |

---

## 6. DNS — แปลงชื่อเป็น IP

### เบื้องหลัง
```
 เครื่อง → ถาม DNS ภายใน (10.0.104.11): "intranet.corp.local คือ IP อะไร"
   ถ้าเป็นชื่อภายนอก DNS ภายในจะไปถามต่อ (root → .com → DNS ของเว็บนั้น) แล้วส่งคำตอบกลับ + จำไว้ (cache) ตาม TTL
```
### อ่านผล nslookup
```
C:\> nslookup intranet.corp.local
Server:  dc01.corp.local            ← DNS server ที่ตอบ
Address:  10.0.104.11

Name:    intranet.corp.local
Address:  10.0.100.25               ← คำตอบ
```
```
C:\> nslookup www.example.com 8.8.8.8      ← บังคับถาม 8.8.8.8 เพื่อเปรียบเทียบ
Non-authoritative answer:                   ← ได้จาก cache ของ DNS ไม่ใช่เจ้าของโดเมนโดยตรง (ปกติ)
Name:    www.example.com
Addresses:  93.184.215.14
```
### อ่านผล dig (Linux/macOS)
```
$ dig www.example.com
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 4242     ← สถานะ: NOERROR = สำเร็จ
;; ANSWER SECTION:
www.example.com.     3600   IN   A   93.184.215.14           ← TTL 3600 วินาที (cache ได้ 1 ชั่วโมง)
;; Query time: 12 msec                                         ← ช้ามาก (หลายร้อย ms ขึ้นไป) = DNS ช้า
;; SERVER: 10.0.104.11#53
```
| สถานะ | ความหมาย | ทำอะไรต่อ |
|---|---|---|
| `NOERROR` + มี ANSWER | สำเร็จ | ตรวจว่า IP ที่ได้ถูกต้อง |
| `NXDOMAIN` | **ไม่มีชื่อนี้** | พิมพ์ผิด? record ยังไม่ถูกสร้าง? ถามผิด DNS (ภายใน vs ภายนอก)? |
| `SERVFAIL` | DNS server ตอบไม่ได้ | DNS server มีปัญหา/forwarder ล่ม/DNSSEC ผิด |
| `connection timed out; no servers could be reached` | ติดต่อ DNS ไม่ได้ | firewall บล็อก port 53, DNS server ล่ม, IP DNS ผิด |

**เทคนิค:** ถ้า `ping 8.8.8.8` ได้ แต่ `ping google.com` ไม่ได้ → **ปัญหา DNS แน่นอน** (เน็ตยังออกได้)
**Split DNS:** ชื่อเดียวกันอาจได้ IP ต่างกันจาก DNS ภายใน (IP ภายใน) กับ DNS ภายนอก (IP สาธารณะ) — เป็นการออกแบบที่ตั้งใจ แต่ถ้าเครื่องใช้ DNS ผิดตัวจะเข้าไม่ได้

---

## 7. ทดสอบ Port — สำคัญกว่า ping

### ทำไม ping อย่างเดียวไม่พอ
- ping ใช้ ICMP แต่แอปใช้ **TCP/UDP port** (เว็บ 443, RDP 3389, SQL 1433, SMB 445)
- firewall อาจ **อนุญาต ICMP แต่บล็อก port** หรือกลับกัน
- เครื่องปลายทาง "เปิด" แต่ **บริการไม่ทำงาน**

### หลักการ: TCP 3-way handshake
```
 เครื่องเรา ── SYN ──────► server:443     "ขอเชื่อมต่อ"
 เครื่องเรา ◄─ SYN-ACK ──  server          "ยินดี" → port เปิด ✅
 หรือ
 เครื่องเรา ◄─ RST ──────  server          "ไม่มีบริการที่ port นี้" → Connection refused
 หรือ
 (เงียบ ไม่มีอะไรกลับมา)                   → ถูก firewall drop / ไม่มี route → timeout
```
### ตัวอย่าง Test-NetConnection
```
PS> Test-NetConnection 10.0.100.25 -Port 443
ComputerName     : 10.0.100.25
RemoteAddress    : 10.0.100.25
RemotePort       : 443
InterfaceAlias   : Ethernet
SourceAddress    : 10.0.20.55
PingSucceeded    : False          ← ping ไม่ผ่าน (ICMP ถูกบล็อก)
TcpTestSucceeded : True           ← แต่ port 443 เปิด! → บริการใช้งานได้
```
นี่คือตัวอย่างที่ **ping ไม่ได้ แต่ระบบใช้งานได้ปกติ** — ถ้าดูแค่ ping จะสรุปผิด

### ตัวอย่าง nc (Linux)
```
$ nc -zv 10.0.100.25 443
Connection to 10.0.100.25 443 port [tcp/https] succeeded!     ← เปิด

$ nc -zv 10.0.100.25 3389
nc: connect to 10.0.100.25 port 3389 (tcp) failed: Connection refused   ← ถึงเครื่องแล้ว แต่ไม่มีบริการ/เครื่องปฏิเสธ

$ nc -zv -w 3 10.0.100.25 1433
nc: connect to 10.0.100.25 port 1433 (tcp) timed out          ← ถูก drop ระหว่างทาง → ไปดู firewall
```
| ผล | ปัญหาน่าจะอยู่ที่ | คุยกับใคร |
|---|---|---|
| succeeded | network ปกติ ถ้าแอปยังใช้ไม่ได้ ปัญหาอยู่ที่แอป/สิทธิ์/login | ทีมแอป |
| refused | ถึงเครื่องแล้ว บริการไม่ทำงาน/port ผิด/firewall บนเครื่องปฏิเสธ | ทีม server |
| timed out | firewall drop ระหว่างทาง หรือไม่มี route (ขาไปหรือกลับ) | ทีม network/security |

### curl — ดูละเอียดถึงระดับ HTTPS
```
$ curl -v https://intranet.corp.local
*   Trying 10.0.100.25:443...
* Connected to intranet.corp.local (10.0.100.25) port 443       ← TCP ผ่าน
* TLS handshake ...
* SSL certificate problem: certificate has expired              ← ปัญหาอยู่ที่ certificate ไม่ใช่ network
```
และวัดเวลาแต่ละช่วงเพื่อหาว่าช้าตรงไหน:
```
$ curl -o /dev/null -s -w "dns:%{time_namelookup} connect:%{time_connect} tls:%{time_appconnect} total:%{time_total}\n" https://site
dns:2.501 connect:2.520 tls:2.580 total:2.700
     └ ช้าที่ DNS 2.5 วินาที! (connect/tls เร็ว) → แก้ DNS
```

---

## 8. iperf3 — วัดความเร็วจริงระหว่าง 2 จุด

ต่างจาก speedtest บนเว็บ (วัดไปถึง server ของผู้ให้บริการ) — iperf3 วัด **ระหว่างสองเครื่องที่เราเลือก** เช่น สาขา ↔ HQ
```
$ iperf3 -c 10.0.100.50 -t 10
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-10.00  sec   575 MBytes   482 Mbits/sec   23     sender
[  5]   0.00-10.00  sec   573 MBytes   480 Mbits/sec          receiver
```
- **Bitrate** = ความเร็วที่ได้จริง (ลิงก์ 500 Mbps ได้ ~480 ถือว่าปกติ เพราะมี overhead)
- **Retr** (retransmission) = ต้องส่งซ้ำ → มี packet loss/congestion
- ใช้ `-R` วัดทิศกลับ (download vs upload มักไม่เท่ากัน), `-P 8` หลาย stream, `-u -b 50M` ทดสอบ UDP (ได้ค่า jitter และ loss สำหรับประเมินคุณภาพเสียง/วิดีโอ)
- ⚠️ อย่ารันเต็มลิงก์ production ในเวลาทำงานโดยไม่แจ้ง — กินแบนด์วิดท์ของทุกคน

---

## 9. tcpdump — ดู packet จริง (ขั้นสุดท้ายเมื่อทุกอย่างยังไม่ชัด)

```
$ sudo tcpdump -ni eth0 host 10.0.100.25 and port 443
10:15:01.100 IP 10.0.20.55.51544 > 10.0.100.25.443: Flags [S], seq 1000, ...      ← SYN ออกไป
10:15:02.101 IP 10.0.20.55.51544 > 10.0.100.25.443: Flags [S], seq 1000, ...      ← ส่ง SYN ซ้ำ (ไม่มีคำตอบ)
10:15:04.105 IP 10.0.20.55.51544 > 10.0.100.25.443: Flags [S], seq 1000, ...      ← ซ้ำอีก
```
ความหมายของ Flags: `[S]` SYN · `[S.]` SYN-ACK · `[.]` ACK · `[P.]` ส่งข้อมูล · `[F.]` ปิดปกติ · `[R]` ตัดการเชื่อมต่อ
→ ตัวอย่างข้างบนเห็นแต่ SYN ส่งซ้ำ ไม่มี SYN-ACK = **ขาไปออกจากเครื่องแล้ว แต่ไม่มีอะไรกลับ** → ปัญหาอยู่ระหว่างทาง/ที่ปลายทาง ไม่ใช่ที่เครื่องผู้ใช้
- `-n` ไม่แปลงชื่อ · `-i any` ทุก interface · `-w file.pcap` บันทึกไปเปิดใน Wireshark

---

## 10. สรุป: เลือกคำสั่งตามอาการ

| อาการ | เริ่มด้วย |
|---|---|
| ใช้อะไรไม่ได้เลย | `ipconfig /all` → `ping gateway` |
| เข้าเว็บด้วยชื่อไม่ได้ | `ping 8.8.8.8` + `nslookup` |
| เข้าระบบเดียวไม่ได้ | `Test-NetConnection -Port` / `nc -zv` → `tracert` |
| ช้า/กระตุก/หลุดเป็นช่วง | `mtr` หรือ `pathping`, `ping -t` ดูนาน ๆ |
| เว็บบางหน้าค้าง, VPN ใช้แอปไม่ได้ | ทดสอบ MTU ด้วย `ping -f -l` |
| ต่อ VPN แล้วมีปัญหา | `route print` / `ip route get` |
| ต้องการพิสูจน์ความเร็วลิงก์ | `iperf3` |
| ยังหาไม่เจอ | `tcpdump` / Wireshark |

---

## 11. แบบฝึกหัด (ทำบนเครื่องตัวเองได้)

1. รัน `ipconfig /all` แล้วระบุ IP, mask, gateway, DNS ของเครื่องคุณ — เครื่องอยู่วงขนาดเท่าไร (กี่ host)
2. `ping` gateway, `8.8.8.8` และเว็บไซต์หนึ่ง — เปรียบเทียบ time และ TTL เดาว่าปลายทางเป็น OS อะไร
3. `tracert -d 8.8.8.8` — นับว่ากี่ hop, hop ไหนคือ ISP ของคุณ
4. รัน `mtr` หรือ `pathping` ไปปลายทางเดิม — มี hop ไหนที่ loss แต่ไม่ใช่ปัญหาจริงไหม
5. ทดสอบ MTU: หาขนาด `ping -f -l` ที่ใหญ่ที่สุดที่ผ่านไป 8.8.8.8 (ถ้าใช้ PPPoE ที่บ้านมักได้ 1464)
6. `Test-NetConnection google.com -Port 443` และ port 25 — ผลต่างกันอย่างไร เพราะอะไร
7. `nslookup` ชื่อเว็บหนึ่งกับ DNS ของเครื่อง และกับ `1.1.1.1` — ได้ IP เดียวกันไหม

<details><summary><b>แนวคำตอบบางข้อ</b></summary>

1. เช่น 255.255.255.0 = /24 = 254 host
2. TTL ~117–120 มักเริ่มจาก 128 (Windows), ~50–60 มักเริ่มจาก 64 (Linux) — server ใหญ่ ๆ อาจตั้งค่าเอง
5. 1472 = Ethernet ปกติ (MTU 1500) · 1464 = PPPoE (MTU 1492)
6. 443 มักผ่าน · 25 (SMTP) ISP/องค์กรหลายแห่งบล็อกขาออกเพื่อกัน spam → timeout
7. อาจต่างกันได้ เพราะ CDN ตอบ IP ตามตำแหน่งของ DNS resolver
</details>

➡️ ต่อไป: [อธิบายคำสั่ง Cisco](02-cisco-explained.md)
