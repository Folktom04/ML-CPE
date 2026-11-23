# Tier 7 — Network Security (Level 61–70)

> เป้าหมายของ Tier: ออกแบบและดูแลเครือข่ายให้ปลอดภัย ตรวจจับ และตอบสนองเหตุการณ์
>
> ⚠️ ทุก lab ด้านโจมตีให้ทำในเครือข่ายทดลองของตัวเองหรือที่ได้รับอนุญาตเป็นลายลักษณ์อักษรเท่านั้น

---

## Level 61 — Security Fundamentals

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L61-security-fundamentals.md](lessons/L61-security-fundamentals.md)

**สิ่งที่ต้องรู้**
- CIA Triad, AAA, Least privilege, Defense in depth
- Threat / Vulnerability / Risk / Exploit; CVE, CVSS
- การโจมตีที่พบบ่อย: phishing, ransomware, DDoS, MITM, brute force, lateral movement
- MITRE ATT&CK, Cyber Kill Chain
- Framework: NIST CSF 2.0, ISO 27001, CIS Controls; กฎหมายไทย: พ.ร.บ.คอมพิวเตอร์, PDPA, พ.ร.บ.ไซเบอร์

**แบบทดสอบ**
1. DDoS กระทบ CIA ข้อใด
2. Vulnerability กับ Risk ต่างกันอย่างไร
3. Defense in depth คืออะไร ยกตัวอย่าง 3 ชั้น
4. CVSS 9.8 หมายความว่าอะไร
5. MITRE ATT&CK ใช้ทำอะไรในงาน network

<details><summary>เฉลย</summary>

1. Availability
2. Vulnerability = จุดอ่อน; Risk = โอกาส × ผลกระทบเมื่อจุดอ่อนถูกใช้
3. ป้องกันหลายชั้น: firewall ขอบ + segmentation + EDR + MFA
4. Critical — ร้ายแรงมาก ควร patch ด่วน
5. map การตรวจจับ/ป้องกันกับเทคนิคผู้โจมตี หาช่องว่าง
</details>

**5 โปรเจค**
- ⭐ P1: สรุป CIS Controls v8 ข้อที่เกี่ยวกับ network
- ⭐⭐ P2: Risk register เครือข่าย lab (10 ความเสี่ยง + mitigations)
- ⭐⭐ P3: ติดตาม CVE ของอุปกรณ์ที่ใช้ (สคริปต์ query NVD API)
- ⭐⭐ P4: Map การป้องกันใน lab กับ MITRE ATT&CK (ATT&CK Navigator)
- ⭐⭐ P5: เขียน security policy เครือข่าย (password, remote access, change, logging)

---

## Level 62 — Firewall: Stateful, NGFW, iptables/nftables

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L62-firewall-ngfw.md](lessons/L62-firewall-ngfw.md)

**สิ่งที่ต้องรู้**
- Packet filter → Stateful → NGFW (App-ID, User-ID, IPS, URL filtering, SSL inspection)
- Zone-based policy, rule order (top-down first match), implicit deny, logging
- NAT policy vs Security policy
- HA: active/passive, active/active, session sync
- Linux: nftables (แทน iptables), conntrack; pfSense/OPNsense
- Rule hygiene: ไม่มี any-any, มี owner/ticket/expiry, review รายไตรมาส

```bash
nft add table inet fw
nft add chain inet fw input '{ type filter hook input priority 0; policy drop; }'
nft add rule inet fw input ct state established,related accept
nft add rule inet fw input iif lo accept
nft add rule inet fw input tcp dport 22 ip saddr 10.0.0.0/24 accept
```

**แบบทดสอบ**
1. Stateful firewall จำอะไร
2. ทำไม rule เฉพาะเจาะจงต้องอยู่ก่อน rule กว้าง
3. SSL inspection ทำงานอย่างไร และข้อควรระวัง
4. Shadowed rule คืออะไร
5. policy drop ใน nftables input chain โดยไม่มี `ct state established` จะเกิดอะไร

<details><summary>เฉลย</summary>

1. session table (5-tuple, state, timeout)
2. first-match — rule กว้างจะจับไปก่อน
3. Firewall เป็น MITM ออก cert ใหม่ด้วย CA ภายใน; ระวัง privacy (ธนาคาร/สุขภาพ), cert pinning, PDPA
4. Rule ที่ไม่มีวัน match เพราะ rule ก่อนหน้าครอบหมดแล้ว
5. response ของ connection ที่เครื่องเริ่มเองจะถูก drop (ออกเน็ตไม่ได้)
</details>

**5 โปรเจค**
- ⭐ P1: nftables host firewall สำหรับ web server
- ⭐⭐ P2: pfSense/OPNsense 3 zone (LAN/DMZ/WAN)
- ⭐⭐ P3: FortiGate/Palo Alto VM trial: App-ID policy block แอป
- ⭐⭐⭐ P4: Firewall HA active/passive + ทดสอบ session failover
- ⭐⭐⭐ P5: Rule audit tool: วิเคราะห์ config export → หา any-any, shadowed, unused (hit count 0)

---

## Level 63 — Layer 2 Security

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L63-layer2-security.md](lessons/L63-layer2-security.md)

**สิ่งที่ต้องรู้**
- การโจมตี: MAC flooding, ARP spoofing, DHCP starvation/rogue, VLAN hopping, STP manipulation
- ป้องกัน: Port security, DHCP snooping (trusted port), Dynamic ARP Inspection, IP Source Guard, BPDU Guard/Root Guard, ปิด DTP, native VLAN ไม่ใช้งาน
- IPv6: RA Guard, DHCPv6 Guard

```
ip dhcp snooping
ip dhcp snooping vlan 10,20
interface g0/24
 ip dhcp snooping trust
ip arp inspection vlan 10,20
```

**แบบทดสอบ**
1. DAI อาศัยข้อมูลจากไหน
2. ต้อง trust port ไหนบ้างใน DHCP snooping
3. ป้องกัน double-tagging VLAN hopping อย่างไร
4. MAC flooding ทำให้ switch ทำงานเหมือนอะไร
5. ทำไม DHCP snooping ต้องเปิดก่อน IP Source Guard

<details><summary>เฉลย</summary>

1. DHCP snooping binding table (หรือ ARP ACL)
2. uplink ไปหา DHCP server/relay
3. native VLAN = VLAN ไม่ใช้งาน, tag native VLAN, ไม่ใช้ VLAN 1
4. Hub (flood ทุก frame)
5. IPSG ใช้ binding table จาก snooping
</details>

**5 โปรเจค**
- ⭐⭐ P1: Lab DHCP starvation (Yersinia/scapy) → ป้องกันด้วย snooping + rate limit
- ⭐⭐ P2: ARP spoofing → ป้องกันด้วย DAI
- ⭐⭐ P3: MAC flooding (macof) → port security
- ⭐⭐ P4: Access switch security template ครบชุด + checklist audit
- ⭐⭐⭐ P5: วิดีโอ/บทความ "L2 attack & defense" สาธิต 5 การโจมตีพร้อมการป้องกัน

---

## Level 64 — IDS/IPS

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L64-ids-ips.md](lessons/L64-ids-ips.md)

**สิ่งที่ต้องรู้**
- IDS (passive, ตรวจจับ) vs IPS (inline, block)
- Signature-based vs Anomaly-based; False positive/negative
- Suricata, Snort 3, Zeek (network security monitoring — log metadata)
- การวาง: หลัง firewall, ระหว่าง zone, บน SPAN/TAP
- Tuning rules, threshold, suppression

```
alert tcp any any -> $HOME_NET 22 (msg:"SSH brute force"; flags:S; threshold: type both, track by_src, count 10, seconds 60; sid:1000001; rev:1;)
```

**แบบทดสอบ**
1. IDS กับ IPS วางต่างกันอย่างไร
2. False positive สูงเกินไปมีผลอย่างไร
3. Zeek ต่างจาก Suricata อย่างไร
4. IPS fail-open vs fail-closed
5. ทำไม IDS มองไม่เห็นใน traffic เข้ารหัส และแก้อย่างไร

<details><summary>เฉลย</summary>

1. IDS รับสำเนา traffic (SPAN/TAP); IPS อยู่ inline
2. Alert fatigue — คนเลิกสนใจ alert จริง
3. Zeek สร้าง log พฤติกรรม/metadata (conn, dns, http, ssl); Suricata เน้น signature alert (ทำ log ได้ด้วย)
4. Fail-open = ล่มแล้วปล่อยผ่าน (availability); fail-closed = ล่มแล้ว block (security)
5. Payload เข้ารหัส → ใช้ TLS inspection, JA3/JA4 fingerprint, metadata/flow analysis
</details>

**5 โปรเจค**
- ⭐⭐ P1: ติดตั้ง Suricata บน Linux router + ET Open rules
- ⭐⭐ P2: เขียน custom rule 5 ข้อ + ทดสอบด้วย traffic จำลอง
- ⭐⭐ P3: Zeek วิเคราะห์ pcap → หา DNS แปลก ๆ / beaconing
- ⭐⭐⭐ P4: Security Onion lab + เล่นโจทย์จาก malware-traffic-analysis.net
- ⭐⭐⭐ P5: Suricata IPS inline (NFQUEUE) + วัด throughput ที่ลดลง

---

## Level 65 — Cryptography & PKI สำหรับ Network Engineer

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L65-crypto-pki.md](lessons/L65-crypto-pki.md)

**สิ่งที่ต้องรู้**
- Symmetric (AES) vs Asymmetric (RSA, ECC), Hash (SHA-256), HMAC, Digital signature
- Certificate X.509, CA, Intermediate, Chain of trust, CSR, SAN
- Revocation: CRL, OCSP; Let's Encrypt/ACME
- Formats: PEM, DER, PFX/P12; private key ห้ามหลุด
- ใช้งาน: HTTPS, IPsec cert-auth, 802.1X EAP-TLS, SSH keys, device management certs

```bash
openssl req -new -newkey rsa:2048 -nodes -keyout srv.key -out srv.csr -subj "/CN=vpn.lab.local"
openssl x509 -in cert.pem -text -noout
openssl verify -CAfile chain.pem cert.pem
```

**แบบทดสอบ**
1. ทำไม browser ฟ้อง cert แม้ cert ถูกต้อง (บ่อยสุด)
2. SAN คืออะไร
3. CSR มี private key หรือไม่
4. PFX ต่างจาก PEM
5. ทำไม cert อายุสั้นลงเรื่อย ๆ (เช่น 47 วันในอนาคต)

<details><summary>เฉลย</summary>

1. Server ไม่ส่ง intermediate cert (chain ไม่ครบ)
2. Subject Alternative Name — รายชื่อโดเมน/IP ที่ cert ใช้ได้
3. ไม่มี (มี public key + ข้อมูล subject)
4. PFX เป็น binary รวม cert + key + chain มีรหัสผ่าน; PEM เป็น text base64
5. ลดผลกระทบ key รั่ว/revocation ใช้ไม่ได้จริง → บังคับให้ทำ automation
</details>

**5 โปรเจค**
- ⭐⭐ P1: สร้าง Private CA (root + intermediate) ด้วย openssl
- ⭐⭐ P2: step-ca + ACME ออก cert อัตโนมัติให้ server ภายใน
- ⭐⭐ P3: ใช้ cert-auth กับ IPsec (strongSwan)
- ⭐⭐ P4: สคริปต์ inventory cert ทั้งองค์กร (scan 443) + วันหมดอายุ
- ⭐⭐⭐ P5: ระบบต่ออายุ cert อัตโนมัติ + deploy ไป Nginx/HAProxy + alert ก่อนหมด

---

## Level 66 — 802.1X, NAC & Zero Trust

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L66-8021x-nac-zero-trust.md](lessons/L66-8021x-nac-zero-trust.md)

**สิ่งที่ต้องรู้**
- 802.1X: Supplicant – Authenticator (switch/AP) – Authentication server (RADIUS)
- EAP methods: EAP-TLS (cert, ดีที่สุด), PEAP-MSCHAPv2, EAP-TTLS
- MAB (MAC Authentication Bypass) สำหรับ printer/IoT
- Dynamic VLAN / dACL / SGT (TrustSec), Guest/Posture
- Monitor mode → Low-impact → Closed mode (rollout แบบค่อยเป็นค่อยไป)
- Zero Trust: "Never trust, always verify", identity-based, micro-segmentation, continuous verification (NIST SP 800-207)

**แบบทดสอบ**
1. บทบาท 3 ตัวใน 802.1X
2. ทำไม EAP-TLS ปลอดภัยกว่า PEAP
3. MAB ใช้กับอะไร และจุดอ่อนคืออะไร
4. ทำไมควร rollout แบบ monitor mode ก่อน
5. หลักการ Zero Trust 3 ข้อ

<details><summary>เฉลย</summary>

1. Supplicant, Authenticator, Authentication Server
2. ใช้ cert ทั้งสองฝั่ง ไม่มีรหัสผ่านให้ขโมย
3. อุปกรณ์ที่ไม่รองรับ 802.1X; MAC ปลอมได้ → ต้องจำกัดสิทธิ์ + profiling
4. ดูผลกระทบโดยไม่ block ผู้ใช้จริง
5. Verify explicitly, Least privilege, Assume breach
</details>

**5 โปรเจค**
- ⭐⭐ P1: 802.1X wired lab: FreeRADIUS + switch (GNS3 IOSvL2) + Linux wpa_supplicant
- ⭐⭐ P2: Dynamic VLAN ตามกลุ่มผู้ใช้ (RADIUS attribute)
- ⭐⭐⭐ P3: EAP-TLS ด้วย private CA จาก Level 65
- ⭐⭐ P4: Rollout plan 802.1X สำหรับองค์กร 500 พอร์ต (phase, risk, rollback)
- ⭐⭐⭐ P5: Zero Trust demo: Cloudflare Access/Pomerium ป้องกันเว็บภายในด้วย identity + device posture

---

## Level 67 — Segmentation, DMZ & Secure Architecture

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L67-segmentation-dmz.md](lessons/L67-segmentation-dmz.md)

**สิ่งที่ต้องรู้**
- DMZ (single/dual firewall), Management network แยก (OOB)
- Zone model: Internet, DMZ, User, Server, Database, Management, OT/IoT, Guest
- Micro-segmentation (NSX, Illumio, Cilium policy, Security Groups)
- Jump host/bastion, PAM
- OT/ICS: Purdue model, IEC 62443

**แบบทดสอบ**
1. web server สาธารณะควรอยู่ zone ไหน
2. ทำไม management interface ไม่ควรอยู่ใน user VLAN
3. Micro-segmentation ต่างจาก VLAN segmentation อย่างไร
4. Bastion host มีไว้ทำอะไร
5. Purdue model ใช้กับเครือข่ายแบบไหน

<details><summary>เฉลย</summary>

1. DMZ
2. ลดพื้นที่โจมตี — ผู้ใช้/มัลแวร์เข้าถึง interface จัดการอุปกรณ์ไม่ได้
3. ควบคุมระดับ workload/แอป ไม่ใช่ subnet ทั้งก้อน
4. จุดเข้าเดียวที่ควบคุมและ log สำหรับผู้ดูแลระบบ
5. OT/ICS (โรงงาน, ระบบควบคุม)
</details>

**5 โปรเจค**
- ⭐⭐ P1: ออกแบบ zone model + inter-zone policy matrix สำหรับบริษัท
- ⭐⭐ P2: Lab DMZ web + DB ภายใน + bastion
- ⭐⭐ P3: OOB management network ใน lab (VRF management)
- ⭐⭐⭐ P4: Micro-segmentation ด้วย Kubernetes NetworkPolicy (ต่อยอด Level 77)
- ⭐⭐⭐ P5: Security architecture review ของ lab Capstone ก่อนหน้า → findings + remediation

---

## Level 68 — Logging, SIEM & Visibility

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L68-siem-logging.md](lessons/L68-siem-logging.md)

**สิ่งที่ต้องรู้**
- แหล่ง log: firewall, DNS, DHCP, proxy, VPN, AAA, NetFlow, IDS
- SIEM: Splunk, Elastic, Wazuh, Microsoft Sentinel, Graylog
- Normalize, correlate, alert, dashboard; retention ตามกฎหมาย (พ.ร.บ.คอมฯ: เก็บ log ≥ 90 วัน)
- Use cases: brute force VPN, DNS tunneling, impossible travel, traffic ไป IP อันตราย
- Threat intel feeds (STIX/TAXII, abuse.ch)

**แบบทดสอบ**
1. log อะไรช่วยหาว่าเครื่องไหนติดมัลแวร์ที่ติดต่อ C2 ด้วยชื่อโดเมน
2. ข้อกำหนดเก็บ log ตาม พ.ร.บ.คอมฯ
3. Correlation rule ตัวอย่าง 1 ข้อ
4. DNS tunneling ตรวจจับอย่างไร
5. ทำไม NTP สำคัญกับ SIEM

<details><summary>เฉลย</summary>

1. DNS query log (+ proxy log)
2. ไม่น้อยกว่า 90 วัน (ขยายได้ตามคำสั่งเจ้าหน้าที่)
3. VPN login fail > 10 ครั้ง/5 นาที แล้ว success จาก IP เดียวกัน
4. query ยาว/entropy สูง, จำนวน subdomain มาก, TXT record ปริมาณสูง
5. เวลาตรงกันจึง correlate เหตุการณ์ข้ามระบบได้
</details>

**5 โปรเจค**
- ⭐⭐ P1: Wazuh/ELK รับ syslog จาก firewall + router
- ⭐⭐ P2: Dashboard top blocked IP, top talkers, VPN logins
- ⭐⭐ P3: Rule ตรวจ brute force SSH/VPN + แจ้งเตือน
- ⭐⭐⭐ P4: เอา threat intel feed มาเทียบกับ DNS log อัตโนมัติ
- ⭐⭐⭐ P5: ตรวจจับ DNS tunneling (ทดลองด้วย iodine/dnscat2 ใน lab) ด้วย rule/ML ง่าย ๆ

---

## Level 69 — Penetration Testing สำหรับ Network (Authorized)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L69-pentest-authorized.md](lessons/L69-pentest-authorized.md)

**สิ่งที่ต้องรู้**
- ขอบเขต/Rules of Engagement/หนังสืออนุญาต — ห้ามทำโดยไม่ได้รับอนุญาต
- Phase: Recon → Scanning → Enumeration → Exploitation → Post-exploitation → Reporting
- เครื่องมือ: nmap, Nessus/OpenVAS, Metasploit, Responder, CrackMapExec/NetExec, Burp
- ช่องโหว่ network ที่พบบ่อย: default credentials, SNMP public, Telnet, SMBv1, LLMNR/NBT-NS, unpatched VPN
- Report: executive summary + technical findings + remediation

**แบบทดสอบ**
1. เอกสารที่ต้องมีก่อนเริ่ม pentest
2. LLMNR poisoning ป้องกันอย่างไร
3. Vulnerability scan ต่างจาก pentest อย่างไร
4. SNMP community "public" เสี่ยงอย่างไร
5. Report ที่ดีต้องมีอะไร

<details><summary>เฉลย</summary>

1. หนังสืออนุญาต/สัญญา, scope, RoE, ช่องทางติดต่อฉุกเฉิน
2. ปิด LLMNR/NBT-NS ผ่าน GPO, ใช้ SMB signing
3. Scan = อัตโนมัติหาช่องโหว่; Pentest = พิสูจน์ว่าโจมตีได้จริงและผลกระทบ
4. อ่าน config/ARP/route ได้ (หรือแก้ไขได้ถ้าเป็น RW)
5. Executive summary, risk rating, หลักฐาน, ขั้นตอน reproduce, วิธีแก้
</details>

**5 โปรเจค**
- ⭐⭐ P1: OpenVAS/Greenbone scan lab ตัวเอง + จัดลำดับความเสี่ยง
- ⭐⭐ P2: เล่น TryHackMe/HackTheBox ห้อง network (Nmap, Wireshark, Network Services)
- ⭐⭐⭐ P3: Lab AD เล็ก ๆ: LLMNR poisoning → ป้องกัน → ทดสอบซ้ำ
- ⭐⭐⭐ P4: เขียน pentest report ฉบับเต็มของ lab
- ⭐⭐⭐ P5: Hardening ทุกอุปกรณ์ตาม CIS Benchmark แล้วสแกนเทียบก่อน/หลัง

---

## Level 70 — Incident Response & DDoS Mitigation

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L70-incident-response-ddos.md](lessons/L70-incident-response-ddos.md)

**สิ่งที่ต้องรู้**
- NIST IR: Preparation → Detection & Analysis → Containment, Eradication, Recovery → Post-incident
- Network containment: isolate port/VLAN, block IP/domain, sinkhole DNS, quarantine VLAN
- เก็บหลักฐาน: pcap, flow, log, config; chain of custody
- DDoS: volumetric / protocol (SYN flood) / application (L7); ป้องกัน: scrubbing center, CDN, RTBH, rate-limit, SYN cookies
- Tabletop exercise, playbook

**แบบทดสอบ**
1. ขั้นตอน IR ตาม NIST
2. RTBH คืออะไร
3. SYN cookies ช่วยอะไร
4. ทำไมไม่ควรปิดเครื่องที่ติดมัลแวร์ทันที
5. DDoS ระดับ 100 Gbps ป้องกันที่ firewall องค์กรได้ไหม

<details><summary>เฉลย</summary>

1. Preparation; Detection & Analysis; Containment, Eradication & Recovery; Post-incident activity
2. Remotely Triggered Black Hole — ส่ง BGP community ให้ ISP drop traffic ไป IP เป้าหมาย
3. ไม่ต้องจอง state จนกว่า handshake ครบ → ทน SYN flood
4. หลักฐานใน memory หาย — ควร isolate จาก network แทน
5. ไม่ได้ ลิงก์เต็มก่อนถึง firewall → ต้องใช้ ISP/scrubbing/CDN
</details>

**5 โปรเจค**
- ⭐⭐ P1: เขียน IR playbook: ransomware, DDoS, compromised VPN account
- ⭐⭐ P2: Tabletop exercise กับเพื่อน 3–5 คน + after-action report
- ⭐⭐ P3: สคริปต์ quarantine อัตโนมัติ (ย้ายพอร์ตไป VLAN quarantine ผ่าน API/SSH)
- ⭐⭐⭐ P4: Lab SYN flood (hping3, ใน lab ปิด) → วัดผล → ป้องกันด้วย SYN cookies/rate-limit
- ⭐⭐⭐ P5: Capstone Tier 7: Secure enterprise lab: firewall zones, 802.1X, IDS, SIEM, IR playbook + red/blue exercise
