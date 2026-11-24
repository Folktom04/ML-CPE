# ลำดับการตรวจเช็คเมื่อ "เข้าไม่ได้ / ใช้งานไม่ได้ / ช้า"

> ใช้คำสั่งจาก [Ping/Route](01-ping-traceroute-route.md) · [Cisco](02-cisco.md) · [FortiGate](03-fortigate.md) · [Palo Alto / Check Point](04-paloalto-checkpoint.md) · หลักการละเอียดดู [Level 30](../lessons/L30-troubleshooting-methodology.md) และ [Level 91](../lessons/L91-advanced-troubleshooting.md)

---

## 1. ถามก่อนลงมือ (2 นาทีที่ประหยัดได้ 2 ชั่วโมง)

- **ใคร:** คนเดียว / ทั้งแผนก / ทั้งสาขา / ทุกคน?
- **อะไร:** ทุกเว็บ/แอป หรือเฉพาะระบบเดียว?
- **ที่ไหน:** สาย LAN / Wi-Fi / VPN / ที่บ้าน?
- **เมื่อไร:** เริ่มกี่โมง เป็นตลอดหรือเป็นช่วง ๆ?
- **มีอะไรเปลี่ยน:** มีใครแก้ config, อัปเดต, ย้ายโต๊ะ, เปลี่ยน ISP, cert หมดอายุ?
- **ใครไม่เป็น:** เปรียบเทียบเครื่องที่ใช้ได้กับเครื่องที่ใช้ไม่ได้

---

## 2. ไล่จากเครื่องผู้ใช้ออกไป (ทีละ Layer)

```
 [เครื่องผู้ใช้] → [Switch/AP] → [Gateway] → [Firewall] → [Router/WAN/ISP] → [ปลายทาง]
```
| ขั้น | ตรวจ | คำสั่ง | ถ้าไม่ผ่าน → ดูที่ |
|---|---|---|---|
| 1 | มี IP ถูก subnet, gateway, DNS | `ipconfig /all` · `ip a` | DHCP, VLAN ของพอร์ต, สาย, 802.1X |
| 2 | ถึง gateway | `ping <gateway>` | พอร์ต switch (`show int status`), VLAN/trunk, ARP |
| 3 | ถึง IP ภายนอก | `ping 8.8.8.8` | route บน gateway/firewall, NAT, policy, ISP |
| 4 | DNS ใช้ได้ | `nslookup example.com` | DNS server, firewall port 53 |
| 5 | ติดที่ hop ไหน | `tracert -d` / `mtr` | อุปกรณ์ที่ hop นั้น |
| 6 | port ของบริการเปิดไหม | `Test-NetConnection -Port` / `nc -zv` | firewall policy, บริการบน server |
| 7 | ปัญหาขนาด packet | `ping -f -l 1472` / `ping -M do -s 1472` | MTU/MSS บน VPN/PPPoE |
| 8 | ช้า | `mtr`, `iperf3`, กราฟ utilization | congestion, Wi-Fi, errors, QoS |

---

## 3. สถานการณ์ที่พบบ่อยและคำสั่งที่ใช้

### A. ผู้ใช้คนเดียวใช้เน็ตไม่ได้ (สาย LAN)
```
เครื่อง:   ipconfig /all → ได้ 169.254.x.x?
Switch:    show mac address-table interface Gi1/0/10     ! เห็น MAC เครื่องไหม
           show interfaces Gi1/0/10                        ! up? errors? duplex?
           show interfaces Gi1/0/10 switchport             ! VLAN ถูกไหม
           show interfaces status err-disabled             ! โดนปิดเพราะ port-security/BPDU?
           show access-session interface Gi1/0/10 details  ! ผ่าน 802.1X ไหม
DHCP:      show ip dhcp binding | include <MAC>  หรือ  FortiGate: execute dhcp lease-list
```

### B. ทั้ง VLAN/ชั้นใช้ไม่ได้
```
show interfaces trunk                ! VLAN นี้อยู่ใน allowed list ของ uplink ไหม
show vlan brief                      ! VLAN มีอยู่ไหม
show ip interface brief | include Vlan   ! SVI up?
show spanning-tree vlan 20           ! loop/STP block?
show logging                         ! มี link flap, err-disable, MAC flapping?
```

### C. ภายในใช้ได้ แต่ออกอินเทอร์เน็ตไม่ได้
```
FortiGate: get router info routing-table all           ! มี default route ไหม
           diagnose sys link-monitor status            ! gateway ISP ตอบไหม
           execute ping 8.8.8.8 · execute ping-options source <IP ภายใน> → execute ping 8.8.8.8
           diagnose debug flow filter addr <IP ผู้ใช้> → trace → ดูว่าตก policy/NAT ไหม
           diagnose sys sdwan health-check status      ! ลิงก์ ISP ไหนเสีย
Cisco:     show ip route 0.0.0.0 · show ip nat translations · ping 8.8.8.8 source <inside>
```

### D. เข้าระบบภายใน (server) ไม่ได้ ข้าม firewall
```
1. ผู้ใช้:    Test-NetConnection <server> -Port 443        → timeout = ถูก drop / refused = ถึงแล้วแต่บริการไม่ฟัง
2. Firewall: จำลอง policy (Policy Lookup / test security-policy-match)
             ดู session (diagnose sys session list / show session all filter ...)
             debug flow / counter drop → เหตุผลที่ทิ้ง
3. Server:   มี route กลับไปหา subnet ผู้ใช้ไหม (route print / ip r), Windows Firewall/iptables บน server
4. ถ้า firewall เห็น SYN ออกไปแต่ไม่เห็นขากลับ → server ไม่ตอบ หรือ route ขากลับไปทางอื่น (asymmetric)
```

### E. VPN Site-to-Site ใช้ไม่ได้
```
ขึ้นไหม:     FortiGate get vpn ipsec tunnel summary · Cisco show crypto ikev2 sa · PA show vpn ike-sa
ไม่ขึ้น:     debug IKE → proposal / PSK / UDP 500,4500 / IP peer
ขึ้นแต่ไม่ผ่าน: phase 2 selector ตรงกันไหม · มี route ผ่าน tunnel ไหม · มี policy ไหม · NAT ไม่ควร NAT traffic VPN
             diagnose vpn tunnel list → ดู enc/dec: enc เพิ่ม dec ไม่เพิ่ม = อีกฝั่งไม่ตอบ/ไม่มี route กลับ
ping ได้แต่แอปค้าง: MTU → ping df-bit size 1400… · ตั้ง TCP MSS
ทดสอบ:       ping จาก source เป็น IP ภายใน (ไม่ใช่ IP ของ WAN)
```

### F. ช้า / หลุดเป็นพัก ๆ
```
mtr -rwbzc 300 <ปลายทาง>                    ! loss/latency เริ่มที่ hop ไหน
Cisco:     show interfaces | include line protocol|errors|drops   ! errors/drops เพิ่มขึ้น?
           show interfaces transceiver detail ! แสงไฟเบอร์ต่ำ?
           show processes cpu sorted
FortiGate: get system performance status · diagnose sys top · diagnose hardware deviceinfo nic portX
           diagnose sys sdwan health-check status   ! jitter/loss ของแต่ละลิงก์
ดูกราฟ:    utilization ของ uplink/WAN ช่วงที่ช้า (≥ 80% = congestion)
Wi-Fi:     สัญญาณ (RSSI), channel utilization, จำนวน client ต่อ AP
```

### G. หาว่าเครื่อง IP นี้อยู่ที่ไหน
```
1. Router/L3 switch/FortiGate: show ip arp <IP> / get system arp → ได้ MAC
2. Core switch: show mac address-table address <MAC> → ได้พอร์ต
3. ถ้าพอร์ตเป็น uplink/trunk: show cdp neighbors <port> detail → ไป switch ถัดไป ทำซ้ำข้อ 2
4. จนเจอพอร์ต access → ดู description/ผังพอร์ต
```

---

## 4. Checklist ก่อนบอกว่า "Network ไม่ผิด"

- [ ] ping + port test จากต้นทางจริง (ไม่ใช่จากเครื่องเรา)
- [ ] traceroute ทั้ง **ขาไปและขากลับ** (จาก server กลับมาหาผู้ใช้)
- [ ] firewall: policy match, session มี reply, ไม่มี drop counter
- [ ] interface ใน path ไม่มี errors/drops เพิ่มขึ้น, utilization ไม่เต็ม
- [ ] DNS ได้ IP ที่ถูกต้อง (ภายใน vs ภายนอก)
- [ ] MTU ผ่านด้วย packet เต็มขนาด
- [ ] เวลาของอุปกรณ์ตรงกัน (สำคัญต่อ log, cert, VPN, 802.1X)
- [ ] บันทึกผลทุกคำสั่ง + เวลา ไว้ใน ticket (ใช้ต่อกับทีมอื่น/TAC)

---

## 5. ข้อควรระวังบนระบบจริง

- คำสั่ง `show`/`get`/ping/traceroute ปลอดภัย · คำสั่ง `debug`, `clear`, `diagnose ... clear`, `reboot` **ต้องระวัง**
- debug: ตั้ง filter ก่อนเสมอ, จำกัดจำนวน, **ปิดเมื่อเสร็จ** (`undebug all` / `diagnose debug disable` + `reset`)
- `diagnose sys session clear` ที่ไม่มี filter = **ตัด session ทุกคน**
- การแก้ config บนอุปกรณ์ production ทำผ่าน change และตั้ง safety net (`reload in`, `cfg-revert`, `commit confirmed`)
- ข้อมูลจาก capture/log อาจมีข้อมูลส่วนบุคคล — เก็บและแชร์ตามนโยบายองค์กร
