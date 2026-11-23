# บทเรียน Level 62 — Firewall: Stateful, NGFW, iptables/nftables (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจวิวัฒนาการของ firewall · การทำงานแบบ stateful (session table) · zone และ policy · ลำดับการประมวลผล (NAT/route/policy) · ความสามารถของ NGFW · HA · ตั้ง nftables บน Linux · ดูแล rule base ให้สะอาด (rule hygiene)

---

## 1. Firewall คืออะไร

**Firewall** = อุปกรณ์/ซอฟต์แวร์ที่ **ควบคุมการเชื่อมต่อระหว่างเครือข่าย (หรือ zone) ตามนโยบาย** — อนุญาตเฉพาะสิ่งที่ต้องการ และปฏิเสธที่เหลือ

**วางไว้ที่**
- **Perimeter (ขอบเครือข่าย)** — ระหว่างอินเทอร์เน็ตกับภายใน
- **ระหว่าง zone ภายใน** — user ↔ server, DMZ, OT, Guest (internal segmentation firewall)
- **Data center** — east-west ระหว่างแอป
- **Cloud** — security group, cloud firewall, NGFW VM
- **บนเครื่อง (host firewall)** — Windows Defender Firewall, nftables

---

## 2. วิวัฒนาการของ Firewall

| รุ่น | ตรวจอะไร | ข้อจำกัด |
|---|---|---|
| **Packet filter (stateless)** | header ทีละ packet: IP, port, protocol (= ACL) | ไม่จำ session ต้องอนุญาตขากลับเอง, ถูกหลอกง่าย |
| **Stateful firewall** | + **ติดตามสถานะ session** อนุญาตขากลับอัตโนมัติ | ยังดูแค่ L3/L4 — "port 443 = เว็บ" |
| **Application/Proxy firewall** | เป็นตัวกลางของการเชื่อมต่อ ตรวจ L7 | ช้า รองรับโปรโตคอลจำกัด |
| **NGFW (Next-Generation)** | stateful + **ระบุแอป + ผู้ใช้ + ตรวจเนื้อหา (IPS, AV, URL, SSL inspection, sandbox)** | ต้องการทรัพยากรสูงเมื่อเปิดฟีเจอร์ครบ |
| WAF | ป้องกัน web application (OWASP Top 10) — Level 72 | เฉพาะ HTTP/S |

---

## 3. Stateful Firewall ทำงานอย่างไร

```
 ① PC 10.0.10.5:51544 → 93.184.216.34:443  SYN
    → firewall ตรวจ policy: "Users → Internet, HTTPS = allow" ✅
    → สร้างรายการใน SESSION TABLE:
       [TCP 10.0.10.5:51544 ↔ 93.184.216.34:443  state: SYN_SENT  timeout: ...]
 ② server ตอบ SYN-ACK กลับมา
    → firewall ค้นใน session table → พบ session ที่ตรงกัน → อนุญาตทันที (ไม่ต้องมี rule ขาเข้า)
 ③ ข้อมูลไหลไปมา · firewall ติดตาม seq/flag/state
 ④ FIN/RST หรือ idle เกิน timeout → ลบ session
```
- **ไม่มี rule ขาเข้าจากอินเทอร์เน็ต** แต่ผู้ใช้ภายในเปิดเว็บได้ เพราะขากลับตรงกับ session ที่ภายในเป็นฝ่ายเริ่ม
- packet ขาเข้าที่ไม่ตรงกับ session ใด และไม่มี rule อนุญาต → **drop**
- **Session timeout:** TCP established มักนาน (ชั่วโมง), UDP/ICMP สั้น (วินาที) — แอปที่เงียบนานอาจถูกตัด ต้องใช้ keepalive
- **Session table มีขนาดจำกัด** → เป็นค่าสำคัญตอน sizing (concurrent sessions, new sessions/second) และเป็นเป้าของ DDoS แบบ state exhaustion

---

## 4. Zone และ Security Policy

### Zone
จัดกลุ่ม interface ตามระดับความเชื่อถือ แล้วเขียน policy **ระหว่าง zone**
```
            [ INTERNET ] (untrust)
                  │
            ┌─── FW ───┐
   [ DMZ ] ─┤          ├─ [ USERS ] (trust)
            │          ├─ [ SERVERS ]
            └──────────┴─ [ GUEST ] · [ MGMT ] · [ OT ]
```

### Security Policy (Rule)
```
 ลำดับ | ชื่อ                 | Src zone | Src         | Dst zone | Dst            | Service/App      | Action | Log | Profile
 1     | Users-to-Web         | USERS    | Users-Net   | INTERNET | any            | web-browsing,ssl | allow  | ✅  | AV, IPS, URL
 2     | Users-to-ERP         | USERS    | Finance-Grp | SERVERS  | ERP-Server     | tcp/443          | allow  | ✅  | IPS
 3     | Internet-to-WebDMZ   | INTERNET | any         | DMZ      | Web-VIP        | tcp/443          | allow  | ✅  | IPS, WAF
 4     | Guest-to-Internet    | GUEST    | Guest-Net   | INTERNET | any            | web, dns         | allow  | ✅  | URL
 ...
 last  | Deny-All             | any      | any         | any      | any            | any              | deny   | ✅  |
```
**หลักการ**
- **ประมวลผลบนลงล่าง first match** (เหมือน ACL) — rule เจาะจงไว้บน
- **Implicit deny** ท้ายสุด (ใส่ rule deny + log ให้ชัดเจน เพื่อเห็นสิ่งที่ถูกบล็อก)
- ใช้ **object/group** (address, service, user group) แทน IP ดิบ — อ่านง่ายและแก้ที่เดียว
- **ทุก rule มี log** และเปิด **security profile** ที่เหมาะสม
- **Intra-zone:** traffic ภายใน zone เดียวกันมักอนุญาตเป็นค่าเริ่มต้น (ตรวจของแต่ละยี่ห้อ)

---

## 5. ลำดับการประมวลผลใน Firewall (สำคัญเวลาแก้ปัญหา)

ลำดับทั่วไป (แต่ละยี่ห้อมีรายละเอียดต่างกัน):
```
 ① รับ packet → ② ตรวจ session table (มีอยู่แล้ว → ข้ามไป fast path)
 ③ (packet แรกของ session) Destination NAT → ④ Route lookup → หา egress interface/zone
 ⑤ Security policy lookup → ⑥ Source NAT → ⑦ Security profile (IPS/AV/URL…) → ⑧ ส่งออก
```
**ประเด็นที่มักพลาด**
- **Palo Alto:** security policy ใช้ **IP ก่อน NAT (pre-NAT) แต่ zone หลัง NAT (post-NAT zone)** สำหรับ destination NAT
- **FortiGate:** ใช้ IP ของ VIP (mapped) ใน policy ตามโหมดที่ใช้ (VIP object ใน destination)
- ถ้า **ไม่มี route** ไปยังปลายทาง (หรือ route ออกผิด interface) → policy ไม่ match ตามที่คิด

---

## 6. NGFW — ความสามารถเพิ่มเติม

| ฟีเจอร์ | ทำอะไร |
|---|---|
| **Application identification** (App-ID/Application Control) | รู้ว่าเป็น Facebook, Teams, BitTorrent, SSH-over-443 ไม่ว่าใช้ port ไหน → เขียน policy ตามแอป |
| **User identification** (User-ID/FSSO) | ผูก IP กับผู้ใช้/กลุ่ม AD → policy ตามแผนก |
| **IPS** | ตรวจ signature การโจมตี/ช่องโหว่ แล้ว block |
| **Anti-virus / Anti-malware** | สแกนไฟล์ที่ส่งผ่าน |
| **URL filtering** | บล็อกหมวดเว็บ (malware, phishing, การพนัน) |
| **DNS security** | บล็อกโดเมนอันตราย/C2, ตรวจ DNS tunneling |
| **SSL/TLS inspection** | ถอดรหัสเพื่อตรวจ (Level 49 SI/ISC Level 46) |
| **Sandboxing** | รันไฟล์ที่ไม่รู้จักในสภาพแวดล้อมจำลอง (WildFire, FortiSandbox) |
| **File blocking / DLP** | บล็อกชนิดไฟล์/ข้อมูลอ่อนไหว |
| VPN, SD-WAN, NAT, routing | ในกล่องเดียว |

> 🔑 **การ sizing NGFW:** ดู **threat protection / NGFW throughput** (เปิด IPS+AV+App-ID) และ **SSL inspection throughput** — ไม่ใช่ "firewall throughput" ที่วัดแบบไม่เปิดอะไรเลย ตัวเลขอาจต่างกันหลายเท่า

---

## 7. Firewall High Availability

| โหมด | ลักษณะ |
|---|---|
| **Active/Passive** ⭐ | ตัวหนึ่งทำงาน อีกตัวรอ · sync config + **session** → failover แล้ว session ไม่หลุด · ง่ายและพบมากที่สุด |
| **Active/Active** | ทั้งสองทำงานพร้อมกัน · ซับซ้อน (asymmetric traffic) · ต้องคิดเรื่องโหลดรวมเมื่ออีกตัวล่ม (แต่ละตัวต้องรับได้ 100%) |
| **Cluster (หลายตัว)** | ในรุ่นใหญ่/data center |

**องค์ประกอบ:** heartbeat/HA link (ควร 2 เส้น), config sync, session sync, **link/path monitoring** (failover เมื่อ interface สำคัญหรือ next-hop ล่ม), preempt (ตามความเหมาะสม)
ผลิตภัณฑ์: FortiGate FGCP, Palo Alto HA (HA1/HA2), Check Point ClusterXL, Cisco FTD HA

---

## 8. Linux Firewall: nftables (แทน iptables)

```bash
# /etc/nftables.conf — host firewall ของ web server
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;          # ค่าเริ่มต้น: drop
    ct state established,related accept                      # ⭐ อนุญาตขากลับ (stateful)
    ct state invalid drop
    iif "lo" accept
    ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded } limit rate 10/second accept
    ip6 nexthdr ipv6-icmp accept                              # IPv6 ต้องการ ICMPv6
    tcp dport { 80, 443 } accept                              # เว็บ
    ip saddr 10.0.99.0/24 tcp dport 22 accept                 # SSH เฉพาะ management
    log prefix "nft-drop: " limit rate 5/minute counter drop
  }
  chain forward { type filter hook forward priority 0; policy drop; }
  chain output  { type filter hook output priority 0; policy accept; }
}
```
```bash
sudo nft -f /etc/nftables.conf ; sudo nft list ruleset ; sudo systemctl enable --now nftables
```
- `ct state` = **connection tracking (conntrack)** — ทำให้ Linux เป็น stateful firewall
- Front-end: **ufw** (Ubuntu), **firewalld** (RHEL) · ระบบ firewall แบบ appliance บน open source: **pfSense, OPNsense**

> ⚠️ ตั้ง `policy drop` ที่ input ผ่าน SSH → ต้องมี rule อนุญาต SSH และ `established` **ก่อน** apply ไม่เช่นนั้นจะตัดตัวเองออก

---

## 9. Rule Hygiene — ดูแล rule base

rule base ที่ไม่ได้ดูแลจะบวมขึ้นทุกปี เต็มไปด้วยกฎกว้างเกิน กฎซ้ำ และกฎที่ไม่มีใครรู้ว่ามีไว้ทำไม

**ปัญหาที่ต้องหา**
- **Any-any rule** (src any, dst any, service any) — โดยเฉพาะ allow
- **Shadowed rule** — ไม่มีวัน match เพราะ rule ก่อนหน้าครอบหมด
- **Redundant/duplicate rule**
- **Unused rule** — hit count = 0 นาน 90 วันขึ้นไป
- **Rule ที่ไม่มี log/ไม่มี security profile**
- **Rule ชั่วคราวที่ไม่เคยถูกลบ**
- Object ที่ไม่ได้ใช้, ชื่อไม่สื่อความหมาย

**แนวปฏิบัติ**
- ทุก rule มี **ชื่อ, คำอธิบาย, เจ้าของ, เลข ticket/change, วันหมดอายุ** (ถ้าเป็นชั่วคราว)
- **ทบทวน rule base เป็นระยะ** (เช่น ทุก 6 เดือน) — เป็นข้อกำหนดของ ISO 27001/PCI DSS
- ลบ rule แบบปลอดภัย: **disable ก่อน → เฝ้าดู → ลบ**
- ใช้เครื่องมือวิเคราะห์ (Policy Optimizer, FortiAnalyzer, Tufin, AlgoSec, หรือสคริปต์ของตัวเอง)

---

## 10. แก้ปัญหา Firewall

```
 ① มี session สร้างไหม? (session table/log)
 ② traffic เข้า policy ไหน? allow หรือ deny? (policy lookup tool: FortiGate "Policy Lookup", Palo Alto "test security-policy-match")
 ③ Route ถูกไหม? (ออก interface/zone ที่คาดไว้)
 ④ NAT ถูกไหม? (SNAT/DNAT/no-NAT)
 ⑤ Security profile บล็อกไหม? (IPS/AV/URL/App log)
 ⑥ ขากลับ: asymmetric routing (ขาไปผ่าน FW1 ขากลับผ่าน FW2) → FW2 ไม่มี session → drop
 ⑦ จับ packet ที่ firewall (diagnose sniffer / packet capture) — Level 23
```
FortiGate: `diagnose debug flow` · Palo Alto: `show session all filter ...`, `show counter global filter delta yes`

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ต้องเขียน rule ขากลับใน stateful firewall | session table อนุญาตขากลับอัตโนมัติ |
| port 443 = HTTPS ปลอดภัย | แอป/มัลแวร์ใช้ 443 ได้ ต้องใช้ App-ID/IPS/SSL inspection |
| Firewall throughput บน datasheet คือที่ได้จริง | เมื่อเปิด IPS/AV/SSL ลดลงมาก |
| มี firewall ที่ขอบแล้วพอ | ต้องมี internal segmentation ด้วย |
| rule ที่มีอยู่แล้วทุกข้อจำเป็น | ต้องทบทวนและลบ rule ที่ไม่ใช้ |

---

## 12. Cheat Sheet

```
Packet filter (stateless) → Stateful (session table) → NGFW (App + User + IPS/AV/URL/SSL/sandbox)
Stateful: packet แรกตรวจ policy → สร้าง session → ขากลับผ่านอัตโนมัติ · timeout · session table จำกัด
Zone-based policy: first match · implicit deny (ใส่ deny+log ชัด) · object/group · log ทุก rule
ลำดับ: session lookup → DNAT → route → policy → SNAT → profile
NGFW sizing = threat protection + SSL inspection throughput
HA: active/passive (sync config+session, link monitoring) · active/active ต้องรับโหลดรวมได้
nftables: policy drop + ct state established,related accept + อนุญาตเฉพาะที่ต้องการ
Rule hygiene: any-any · shadowed · unused (hit 0) · ไม่มี log · owner/ticket/expiry · disable→ลบ
แก้ปัญหา: session → policy lookup → route → NAT → profile → asymmetric → packet capture
```

---

## 13. แบบทดสอบ 10 ข้อ

1. Stateless packet filter ต่างจาก stateful firewall อย่างไร
2. ทำไม stateful firewall ไม่ต้องมี rule ขาเข้าเพื่อให้ผู้ใช้เปิดเว็บได้
3. Zone-based policy คืออะไร
4. ทำไม rule ที่เจาะจงต้องอยู่เหนือ rule ที่กว้าง
5. NGFW เพิ่มความสามารถอะไรจาก stateful firewall (5 อย่าง)
6. ทำไม sizing NGFW ต้องดู threat protection throughput
7. HA แบบ active/passive ต้อง sync อะไรบ้าง และ link monitoring มีไว้ทำไม
8. ใน nftables บรรทัด `ct state established,related accept` มีหน้าที่อะไร
9. ยกตัวอย่างปัญหาใน rule base ที่ต้องทำความสะอาด (4 อย่าง)
10. Asymmetric routing ทำให้เกิดปัญหาอะไรกับ stateful firewall

<details><summary><b>เฉลย</b></summary>

1. Stateless ตรวจทีละ packet ไม่จำ session; stateful ติดตามสถานะการเชื่อมต่อและอนุญาตขากลับอัตโนมัติ
2. Traffic ขากลับตรงกับ session ที่ผู้ใช้ภายในเป็นผู้เริ่ม firewall จึงอนุญาตจาก session table
3. จัด interface เป็นกลุ่มตามระดับความเชื่อถือ แล้วเขียน policy ระหว่าง zone
4. Firewall ประมวลผลแบบ first match — rule กว้างที่อยู่ข้างบนจะจับ traffic ไปก่อน rule เจาะจงไม่มีวันถูกใช้
5. Application ID, User ID, IPS, AV/anti-malware, URL filtering, SSL inspection, sandbox, DNS security
6. เมื่อเปิด IPS/AV/App-ID/SSL inspection throughput ลดลงมากจากค่า firewall throughput
7. Config และ session (และสถานะ) — link monitoring ทำให้ failover เมื่อ interface/ลิงก์สำคัญของตัว active ล่ม แม้ตัวเครื่องยังทำงาน
8. อนุญาต packet ที่เป็นส่วนหนึ่งของการเชื่อมต่อที่มีอยู่แล้ว (ขากลับ) — ทำให้เป็น stateful
9. Any-any rule, shadowed rule, rule ที่ไม่มีการใช้งาน (hit 0), rule ที่ไม่มี log/profile, rule ชั่วคราวที่ไม่ถูกลบ, rule ซ้ำ
10. Firewall ที่เห็นแค่ขากลับไม่มี session ของการเชื่อมต่อนั้นจึง drop
</details>

---

➡️ ต่อไป: **Level 63 — Layer 2 Security**
