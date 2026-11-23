# บทเรียน Level 27 — Windows Networking & PowerShell (ฉบับละเอียด)

> อ่านจบแล้วจะ: ใช้ PowerShell ดู/ตั้งค่าเครือข่ายได้ · เข้าใจ Network Profile และ Windows Defender Firewall · จับ packet ด้วย pktmon · รู้บทบาท DNS/DHCP/AD บน Windows Server · แก้ปัญหาเครือข่ายบน Windows อย่างเป็นระบบ

---

## 1. ทำไมต้องรู้ Windows Networking

- ผู้ใช้ในองค์กรส่วนใหญ่ใช้ Windows → งาน helpdesk/support เจอทุกวัน
- **Active Directory, DNS, DHCP** ขององค์กรจำนวนมากรันบน Windows Server
- **Hyper-V** และ Windows Server Failover Cluster ใช้ในงาน data center

---

## 2. CMD (เดิม) vs PowerShell (แนะนำ)

| งาน | CMD | PowerShell |
|---|---|---|
| ดู IP | `ipconfig /all` | `Get-NetIPConfiguration` / `Get-NetIPAddress` |
| ดู route | `route print` | `Get-NetRoute` |
| ดู ARP | `arp -a` | `Get-NetNeighbor` |
| DNS lookup | `nslookup` | `Resolve-DnsName` |
| ทดสอบ port | (telnet) | **`Test-NetConnection -Port`** |
| ดู connection | `netstat -ano` | `Get-NetTCPConnection` |
| ดู NIC | — | `Get-NetAdapter` |
| ตั้ง IP | `netsh interface ip set address` | `New-NetIPAddress` |
| Firewall | `netsh advfirewall` | `Get/New-NetFirewallRule` |

**ข้อดีของ PowerShell:** ผลลัพธ์เป็น object นำไปกรอง/เรียง/ส่งออก CSV ได้ และสั่งเครื่องอื่นจากระยะไกลได้ (Remoting)

```powershell
Get-NetTCPConnection -State Established | Group-Object RemoteAddress | Sort Count -Desc | Select -First 10
Get-NetAdapter | Where Status -eq 'Up' | Select Name, LinkSpeed, MacAddress
Get-NetIPConfiguration | Export-Csv C:\temp\net.csv -NoTypeInformation
```

---

## 3. ตั้งค่า IP/DNS ด้วย PowerShell

```powershell
Get-NetAdapter                                          # ดูชื่อ interface (เช่น "Ethernet")
# Static IP
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 10.0.0.50 -PrefixLength 24 -DefaultGateway 10.0.0.1
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 10.0.0.53,10.0.0.54
# กลับไปใช้ DHCP
Set-NetIPInterface -InterfaceAlias "Ethernet" -Dhcp Enabled
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ResetServerAddresses
Remove-NetRoute -InterfaceAlias "Ethernet" -DestinationPrefix 0.0.0.0/0 -Confirm:$false   # ลบ gateway static เดิม
# DNS suffix
Set-DnsClient -InterfaceAlias "Ethernet" -ConnectionSpecificSuffix corp.local
# ล้าง/ดู DNS cache
Clear-DnsClientCache ; Get-DnsClientCache
# Route ถาวร (CMD)
route -p add 172.16.0.0 mask 255.240.0.0 10.0.0.254
```

---

## 4. Test-NetConnection — เครื่องมือหลักของ support

```powershell
Test-NetConnection fileserver01                         # ping + interface/source IP ที่ใช้
Test-NetConnection fileserver01 -Port 445               # SMB
Test-NetConnection mail.corp.com -Port 443 -InformationLevel Detailed
Test-NetConnection 8.8.8.8 -TraceRoute
Test-NetConnection -ComputerName dc01 -CommonTCPPort RDP   # HTTP, RDP, SMB, WINRM
```
```
ComputerName     : fileserver01
RemoteAddress    : 10.0.10.20
RemotePort       : 445
InterfaceAlias   : Ethernet
SourceAddress    : 10.0.20.55
PingSucceeded    : True
TcpTestSucceeded : False        ← เครื่องอยู่ แต่ port 445 ถูกบล็อก/ไม่เปิด
```

---

## 5. Network Profile และ Windows Defender Firewall

### Network Location Profile
| Profile | ใช้เมื่อ | ค่าเริ่มต้นของ firewall |
|---|---|---|
| **Domain** | เครื่องเชื่อมต่อแล้วติดต่อ Domain Controller ได้ | ตาม GPO ขององค์กร |
| **Private** | เครือข่ายที่เชื่อถือ (บ้าน) | อนุญาต discovery/file sharing ได้ |
| **Public** | เครือข่ายสาธารณะ (ร้านกาแฟ) | **เข้มที่สุด** ปิด discovery/sharing |

**ปัญหาที่พบบ่อย:** เครื่องในองค์กรถูกจัดเป็น **Public** (เช่น ติดต่อ DC ไม่ได้ตอนบูต) → file sharing/remote management ใช้ไม่ได้
```powershell
Get-NetConnectionProfile
Set-NetConnectionProfile -InterfaceAlias "Ethernet" -NetworkCategory Private   # Domain ตั้งเองไม่ได้ ระบบกำหนด
```

### Firewall Rules
```powershell
Get-NetFirewallProfile | Select Name, Enabled
Get-NetFirewallRule -DisplayGroup "File and Printer Sharing" | Select DisplayName, Enabled, Profile
New-NetFirewallRule -DisplayName "Allow App 8080" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Domain
Enable-NetFirewallRule -DisplayName "File and Printer Sharing (Echo Request - ICMPv4-In)"   # อนุญาต ping
```
- ในองค์กรควรจัดการ firewall ผ่าน **Group Policy (GPO)** หรือ **Intune** ไม่ใช่ตั้งทีละเครื่อง
- **Windows ปิดรับ ping เป็นค่าเริ่มต้นในหลายกรณี** — ping ไม่ได้ไม่ได้แปลว่าเครื่องดับ

---

## 6. Packet Capture บน Windows (ไม่ต้องติดตั้งเพิ่ม)

```powershell
pktmon filter add -i 10.0.0.5                      # (ทางเลือก) กรองตาม IP
pktmon start --capture --pkt-size 0 -f C:\temp\cap.etl
# ... ทำให้ปัญหาเกิด ...
pktmon stop
pktmon etl2pcap C:\temp\cap.etl -o C:\temp\cap.pcapng   # แปลงไปเปิดใน Wireshark
pktmon filter remove
```
ทางเลือกเดิม: `netsh trace start capture=yes tracefile=C:\temp\t.etl` / `netsh trace stop`

---

## 7. Wi-Fi บน Windows

```powershell
netsh wlan show interfaces              # SSID, BSSID, channel, signal %, rx/tx rate
netsh wlan show networks mode=bssid     # AP รอบตัว + channel + สัญญาณ
netsh wlan show profiles
netsh wlan show wlanreport              # รายงาน HTML ย้อนหลัง 3 วัน (การหลุด, สาเหตุ)
```
รายงานอยู่ที่ `C:\ProgramData\Microsoft\Windows\WlanReport\wlan-report-latest.html`

---

## 8. คำสั่งซ่อมเครือข่ายที่ใช้บ่อย (helpdesk)

```cmd
ipconfig /release
ipconfig /renew
ipconfig /flushdns
ipconfig /registerdns           :: ลงทะเบียนชื่อเครื่องใน DNS ของ AD ใหม่
netsh winsock reset             :: รีเซ็ต Winsock (ต้อง restart)
netsh int ip reset              :: รีเซ็ต TCP/IP stack (ต้อง restart)
```
Settings → Network & internet → Advanced → **Network reset** (ล้างทุกอย่าง ใช้เป็นทางสุดท้าย)

---

## 9. บริการเครือข่ายบน Windows Server

| Role | หน้าที่ | ประเด็นสำคัญ |
|---|---|---|
| **AD DS** | ยืนยันตัวตน/นโยบาย | พึ่ง DNS ทั้งหมด, เวลาต้องตรง (Kerberos ยอมคลาดได้ 5 นาที) |
| **DNS Server** | AD-integrated zone, forwarder, conditional forwarder | client ในโดเมนต้องใช้ DNS นี้ |
| **DHCP Server** | scope, reservation, option, **failover** (load balance/hot standby) | ต้อง **Authorize** ใน AD ก่อนแจก IP |
| **NPS** | RADIUS server สำหรับ 802.1X, VPN, Wi-Fi Enterprise | |
| **Hyper-V** | virtualization, virtual switch | Level 64 ใน ISC-Track |
| **RRAS** | VPN/routing บน Windows | |

### Port ที่ Active Directory ใช้ (ต้องเปิดระหว่าง client กับ DC)
DNS 53 · Kerberos 88 · RPC 135 + dynamic 49152–65535 · LDAP 389 · SMB 445 · LDAPS 636 · Global Catalog 3268/3269 · NTP 123

---

## 10. PowerShell Remoting — จัดการหลายเครื่อง

```powershell
Enter-PSSession -ComputerName pc-0123                       # remote แบบ interactive (WinRM 5985/5986)
Invoke-Command -ComputerName pc-01,pc-02,pc-03 -ScriptBlock { Get-NetIPConfiguration }
Invoke-Command -ComputerName (Get-Content pcs.txt) -ScriptBlock { Test-NetConnection fileserver01 -Port 445 } |
  Select PSComputerName, TcpTestSucceeded
```
ใช้ตรวจหลายสิบเครื่องพร้อมกันได้ในไม่กี่วินาที

---

## 11. ขั้นตอนแก้ปัญหาบน Windows

```
 1) Get-NetAdapter               → Up? speed ถูก?
 2) ipconfig /all                → IP/mask/gateway/DNS/DHCP server ถูก? 169.254?
 3) Get-NetConnectionProfile     → Domain/Private/Public?
 4) Test-NetConnection <gateway> → ออกจากเครื่องได้
 5) Resolve-DnsName <ชื่อ>        → DNS ภายใน/ภายนอก
 6) Test-NetConnection <server> -Port <port> → บริการ/firewall
 7) netsh wlan show wlanreport   → (ถ้าเป็น Wi-Fi)
 8) pktmon                       → หลักฐานระดับ packet
```

---

## 12. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ping Windows ไม่ได้ = เครื่องดับ | firewall ปิดรับ ICMP ได้ |
| `nslookup` ผลเหมือนที่โปรแกรมใช้เสมอ | nslookup ถาม DNS server ตรง ไม่ผ่าน resolver/hosts ของ Windows — `Resolve-DnsName` ใกล้เคียงการใช้งานจริงกว่า |
| ตั้ง profile เป็น Domain เองได้ | ระบบกำหนดเมื่อติดต่อ DC ได้ |
| DHCP บน Windows Server ติดตั้งแล้วแจกได้ทันที | ต้อง authorize ใน AD และ activate scope |

---

## 13. Cheat Sheet

```
Get-NetIPConfiguration · Get-NetAdapter · Get-NetRoute · Get-NetNeighbor
Resolve-DnsName name -Server X · Clear-DnsClientCache
Test-NetConnection host -Port N [-TraceRoute] [-InformationLevel Detailed]
New-NetIPAddress -InterfaceAlias X -IPAddress A -PrefixLength 24 -DefaultGateway G
Set-DnsClientServerAddress -InterfaceAlias X -ServerAddresses a,b
Get-NetConnectionProfile (Domain/Private/Public) · New-NetFirewallRule
pktmon start --capture → pktmon stop → pktmon etl2pcap
netsh wlan show interfaces / wlanreport
netsh winsock reset · netsh int ip reset
AD ต้องใช้ DNS ภายใน · DHCP ต้อง authorize · Invoke-Command หลายเครื่อง
```

---

## 14. แบบทดสอบ 10 ข้อ

1. คำสั่ง PowerShell ที่ใช้แทน telnet เพื่อทดสอบ port
2. คำสั่ง PowerShell ตั้ง DNS server 10.0.0.53 ให้ interface "Ethernet"
3. Network profile 3 แบบมีอะไรบ้าง แบบไหนเข้มที่สุด
4. เครื่องในโดเมนแชร์ไฟล์ไม่ได้ และพบว่า profile เป็น Public สาเหตุที่เป็นไปได้คืออะไร
5. จับ packet บน Windows โดยไม่ติดตั้งโปรแกรมเพิ่มใช้เครื่องมืออะไร แปลงไปเปิดใน Wireshark อย่างไร
6. คำสั่งสร้างรายงานปัญหา Wi-Fi ย้อนหลัง
7. Resolve-DnsName ต่างจาก nslookup อย่างไร
8. DHCP บน Windows Server ติดตั้งแล้วไม่แจก IP ควรตรวจอะไร 2 อย่าง
9. ทำไมเวลาของเครื่องต้องตรงกับ Domain Controller
10. ต้องการตรวจว่าเครื่อง 50 เครื่องเข้าถึง fileserver01 port 445 ได้หรือไม่ ทำอย่างไรให้เร็ว

<details><summary><b>เฉลย</b></summary>

1. `Test-NetConnection <host> -Port <port>`
2. `Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 10.0.0.53`
3. Domain, Private, Public — Public เข้มที่สุด
4. เครื่องติดต่อ DC ไม่ได้ (DNS ผิด, เครือข่าย/VLAN ผิด, DC ล่ม) จึงไม่ถูกจัดเป็น Domain profile
5. `pktmon` — `pktmon etl2pcap <file.etl> -o <file.pcapng>`
6. `netsh wlan show wlanreport`
7. Resolve-DnsName ใช้ resolver ของ Windows (cache, hosts, suffix) ใกล้เคียงแอปจริง; nslookup ถาม DNS server โดยตรง
8. Authorize DHCP server ใน AD แล้วหรือยัง และ scope ถูก activate หรือไม่ (รวมถึง relay/firewall)
9. Kerberos ยอมให้เวลาคลาดเคลื่อนได้จำกัด (ค่าเริ่มต้น 5 นาที) เกินแล้ว login/ยืนยันตัวตนล้มเหลว
10. ใช้ `Invoke-Command -ComputerName (list) -ScriptBlock { Test-NetConnection fileserver01 -Port 445 }`
</details>

---

➡️ ต่อไป: **Level 28 — ตั้ง Lab: Packet Tracer, GNS3, EVE-NG, Containerlab**
