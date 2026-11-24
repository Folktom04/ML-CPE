# 🧰 รวมคำสั่งตรวจเช็คเครือข่าย (Command Cheat Sheets)

คำสั่งที่ใช้ตรวจเช็คและแก้ปัญหาในงานจริง พร้อมวิธีอ่านผล แยกตามอุปกรณ์

| ไฟล์ | เนื้อหา |
|---|---|
| [01-ping-traceroute-route.md](01-ping-traceroute-route.md) | Ping, Traceroute, mtr, Route, DNS, ทดสอบ Port, iperf3, tcpdump บน Windows / Linux / macOS + วิธีอ่านผล |
| [02-cisco.md](02-cisco.md) | Cisco IOS / IOS-XE / NX-OS: ระบบ, interface, VLAN/STP/MAC, routing (OSPF/BGP/HSRP), ACL/NAT/VPN, packet capture |
| [03-fortigate.md](03-fortigate.md) | FortiGate: ระบบ, interface, routing, ping จาก source, policy/session, **debug flow**, sniffer, IPsec VPN, SD-WAN, HA, log |
| [04-paloalto-checkpoint.md](04-paloalto-checkpoint.md) | Palo Alto, Check Point, Linux firewall + ตารางเทียบคำสั่งระหว่างยี่ห้อ |
| [05-troubleshooting-flow.md](05-troubleshooting-flow.md) | ลำดับการไล่ปัญหา และชุดคำสั่งสำหรับสถานการณ์ที่พบบ่อย (เน็ตไม่ได้, VLAN ล่ม, ออกเน็ตไม่ได้, เข้า server ไม่ได้, VPN, ช้า, หาเครื่องจาก IP) |

📘 **อ่านคำอธิบายละเอียด (หลักการ, ตัวอย่างผลลัพธ์พร้อมอธิบายทีละบรรทัด, กรณีศึกษา):** [explained/README.md](explained/README.md)

## ลำดับสั้นที่สุดเมื่อมีปัญหา

```
ipconfig /all  →  ping gateway  →  ping 8.8.8.8  →  nslookup  →  tracert -d / mtr  →  ทดสอบ port
→ ดูอุปกรณ์ใน path: interface (errors) → route → firewall policy/session/debug flow
```

> ⚠️ คำสั่ง show/get/ping ปลอดภัย · คำสั่ง debug/clear/reboot และการแก้ config บนระบบจริงต้องทำตาม change process และปิด debug ทุกครั้งเมื่อเสร็จ
> คำสั่งอาจต่างกันเล็กน้อยตาม version ของ OS — ตรวจด้วย `?` หรือเอกสารของผู้ผลิตเมื่อไม่แน่ใจ

⬅️ กลับไป [README หลัก](../README.md) · [สารบัญบทเรียน](../lessons/README.md)
