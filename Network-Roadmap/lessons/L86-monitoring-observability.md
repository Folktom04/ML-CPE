# บทเรียน Level 86 — Monitoring & Observability (ฉบับละเอียด)

> อ่านจบแล้วจะ: แยก monitoring กับ observability · 3 สัญญาณ (metrics, logs, traces) · รู้ว่าต้อง monitor อะไรในเครือข่าย · SNMP polling และการคำนวณ bandwidth/95th percentile · NMS ยอดนิยม (Zabbix, LibreNMS, PRTG) · stack Prometheus + Grafana · synthetic monitoring · ออกแบบ alert ที่ดี ลด alert fatigue · SLI/SLO/error budget · MTTD/MTTR

---

## 1. Monitoring vs Observability

| | **Monitoring** | **Observability** |
|---|---|---|
| คำถาม | "ระบบปกติไหม" (สิ่งที่รู้ล่วงหน้าว่าต้องดู) | "**ทำไม**ถึงผิดปกติ" (ถามคำถามใหม่จากข้อมูลได้) |
| ข้อมูล | dashboard/threshold ที่กำหนดไว้ | metrics + logs + traces + flows ที่สัมพันธ์กัน ละเอียด |
| ตัวอย่าง | ลิงก์ WAN ใช้ >80% → alert | ผู้ใช้สาขา A ช้าเฉพาะแอป X ตั้งแต่ 10:05 เพราะ path เปลี่ยนหลัง BGP flap |

**3 สัญญาณ (+ flow สำหรับ network)**

| สัญญาณ | คืออะไร | ตัวอย่าง |
|---|---|---|
| **Metrics** | ตัวเลขตามเวลา (time series) | bps, errors, CPU, latency |
| **Logs** | เหตุการณ์ข้อความ | syslog: `%LINEPROTO-5-UPDOWN`, BGP down (Level 68) |
| **Traces** | เส้นทางของ request ข้าม service | APM/OpenTelemetry (ฝั่งแอป) |
| **Flows** | ใครคุยกับใคร เท่าไร | NetFlow/IPFIX (Level 87) |

---

## 2. ต้อง Monitor อะไรในเครือข่าย

| หมวด | ตัวชี้วัด | ทำไม |
|---|---|---|
| **Availability** | up/down ของอุปกรณ์ (ICMP), interface oper status | พื้นฐาน |
| **Utilization** | in/out bps ทุก uplink/WAN/Internet | คอขวด, capacity planning |
| **Errors/Discards** | CRC/input errors (L1/L2 เสีย), output **discards** (congestion/buffer เต็ม) | ปัญหาสาย/SFP/duplex, QoS |
| **Device health** | CPU, memory, temperature, fan, PSU, disk/flash | ฮาร์ดแวร์ใกล้เสีย |
| **Routing/Protocol** | **OSPF/BGP neighbor state**, จำนวน prefix ที่รับ, STP topology change, HSRP/VRRP state | การเปลี่ยนแปลงที่ทำให้ traffic ย้ายทาง |
| **Services** | DNS resolve time, DHCP pool utilization, NTP offset, RADIUS auth success | บริการพื้นฐานที่ผู้ใช้พึ่ง |
| **Wireless** | client count, channel utilization, retry rate, AP down | ประสบการณ์ Wi-Fi |
| **Security devices** | session count, throughput, VPN tunnel status, HA state | firewall เป็นคอขวดบ่อย |
| **Expiry** | **certificate expiry**, license, support contract | เหตุล่มที่ป้องกันได้ 100% |
| **Experience** | latency/jitter/loss ไปปลายทางสำคัญ, HTTP response time | สิ่งที่ผู้ใช้รู้สึกจริง |
| **Config** | การเปลี่ยน config (syslog/backup diff) | สาเหตุอันดับต้นของ incident |

---

## 3. SNMP Polling และการคำนวณ Bandwidth

```
 NMS ถาม ifHCInOctets (64-bit counter) ทุก 60 วินาที
 t1 = 1,000,000,000 bytes · t2 (60 วิ ถัดมา) = 1,450,000,000 bytes
 bps = (t2 - t1) × 8 / 60 = 450,000,000 × 8 / 60 = 60 Mbps
 utilization = 60 / ifHighSpeed(1000 Mbps) = 6%
```
- ใช้ **counter 64-bit (ifHC*)** สำหรับลิงก์ ≥1G — counter 32-bit วนกลับเร็ว (1G วนทุก ~34 วินาที) ทำให้กราฟเพี้ยน
- **SNMPv3 authPriv** (Level 55) · จำกัด ACL ให้เฉพาะ NMS
- Polling interval 1–5 นาที → **ค่าเฉลี่ยกลบ microburst** (ระดับ ms) — ต้องใช้ telemetry/ตรวจ output discards (Level 90)

### 95th Percentile
```
 1 เดือน × 5 นาที/sample ≈ 8,640 ค่า → เรียงจากน้อยไปมาก → ตัด 5% บนสุด (~432 ค่า หรือ ~36 ชั่วโมง) ทิ้ง
 → ค่าสูงสุดที่เหลือ = 95th percentile
```
- ใช้ **คิดเงิน burstable bandwidth** กับ ISP/DC และวางแผน capacity — ไม่ถูก spike สั้น ๆ หลอก
- รายงาน capacity: ดู 95th percentile + แนวโน้ม ไม่ใช่ค่าเฉลี่ยทั้งเดือน (ซึ่งต่ำเกินจริง) หรือค่าสูงสุด (spike)

---

## 4. เครื่องมือ (NMS และ Stack)

| เครื่องมือ | จุดเด่น | เหมาะกับ |
|---|---|---|
| **Zabbix** | ครบเครื่อง (SNMP, agent, template มาก, trigger, discovery) open source | องค์กรทั่วไป |
| **LibreNMS** | auto-discovery ด้วย SNMP/LLDP, กราฟ network สวย ติดตั้งง่าย | ทีม network |
| **PRTG** | ใช้ง่าย GUI ดี (เชิงพาณิชย์ คิดตาม sensor) | SMB |
| **SolarWinds NPM, ManageEngine OpManager** | เชิงพาณิชย์ องค์กรใหญ่ | |
| **Prometheus + Grafana** ⭐ | time-series + query (PromQL) + dashboard ยืดหยุ่น, cloud-native | ทีม DevOps/NetDevOps |
| Telegraf + InfluxDB + Grafana | รับ gNMI/SNMP ได้ดี | streaming telemetry (Level 83) |
| **Loki/ELK/Graylog** | logs | Level 68 |
| ThousandEyes, Catchpoint, Kentik | internet/SaaS path visibility, synthetic | ผู้ใช้กระจาย, SaaS |
| Vendor cloud (Meraki, Mist, Aruba Central) | ในตัว | ระบบของยี่ห้อนั้น |

### Prometheus + snmp_exporter + Grafana
```
 [Switches] ◄─SNMP─ [snmp_exporter] ◄─scrape─ [Prometheus] ─► [Grafana dashboards]
                                                  └─► [Alertmanager] ─► Teams/LINE/PagerDuty
 [blackbox_exporter] ─ ICMP/HTTP/DNS/TCP probes ─► Prometheus
```
```yaml
# prometheus.yml (ย่อ)
scrape_configs:
  - job_name: snmp
    scrape_interval: 60s
    static_configs: [ { targets: [10.0.0.1, 10.0.0.2] } ]
    metrics_path: /snmp
    params: { module: [if_mib], auth: [snmpv3_net] }
    relabel_configs:
      - { source_labels: [__address__], target_label: __param_target }
      - { source_labels: [__param_target], target_label: instance }
      - { target_label: __address__, replacement: snmp-exporter:9116 }
```
```promql
# bps ขาเข้าของทุก interface (เฉลี่ย 5 นาที)
rate(ifHCInOctets[5m]) * 8
# utilization %
rate(ifHCInOctets[5m]) * 8 / (ifHighSpeed * 1e6) * 100
# interface ที่มี errors เพิ่มขึ้น
increase(ifInErrors[15m]) > 0
```

---

## 5. Synthetic Monitoring

**จำลองการใช้งานจริงเป็นระยะ** จากหลายจุด (สาขา, DC, cloud, internet)
- ICMP (latency/loss), **DNS resolve**, **HTTP(S) ไปแอปสำคัญ** (เช่น ERP login page), TCP connect, VoIP MOS
- เครื่องมือ: blackbox_exporter, Zabbix web scenario, Cisco IP SLA/ThousandEyes, Smokeping (เห็น jitter/loss เป็นภาพ)
- ✅ รู้ปัญหา **ก่อนผู้ใช้แจ้ง** และวัด "ประสบการณ์" ไม่ใช่แค่ "อุปกรณ์ up"
```
 อุปกรณ์ทุกตัวเขียว แต่ synthetic HTTP ไป ERP จากสาขา 10 แห่งช้า 8 วินาที → ปัญหาที่ DNS/proxy/แอป/path
```

---

## 6. Alerting ที่ดี — ไม่ให้ทีม "ชินชา"

### ปัญหา Alert Fatigue
alert มาก → คนเลิกอ่าน → พลาดเหตุสำคัญจริง

### หลักการ

| หลัก | ตัวอย่าง |
|---|---|
| **Alert เฉพาะสิ่งที่ต้องลงมือทำ** | "Core uplink down" ✅ · "พอร์ตเครื่องพนักงาน down" ❌ (ทำเป็น report แทน) |
| **Severity ชัดเจน** | Critical (ปลุกกลางดึก) / Warning (เวลาทำการ) / Info (dashboard) |
| **Hysteresis / for duration** | CPU > 90% **ต่อเนื่อง 10 นาที** ไม่ใช่ spike เดียว · กลับต่ำกว่า 80% ถึง clear |
| **Dedup/grouping/dependency** | router สาขาล่ม → ไม่ต้อง alert ทุก switch/AP หลัง router (parent-child) |
| **Runbook ทุก alert** | ลิงก์ขั้นตอนตรวจสอบ/แก้ไขเบื้องต้น |
| **Maintenance window** | ปิด alert ระหว่าง change ที่วางแผนไว้ |
| **ทบทวนเป็นประจำ** | alert ที่ไม่มีใครทำอะไร → ปรับหรือลบ |
| **Alert ตามอาการผู้ใช้** | synthetic ล้มเหลว/SLO burn rate สำคัญกว่า CPU สูง |

```yaml
# Prometheus alert rule
groups:
- name: network
  rules:
  - alert: WanLinkHighUtilization
    expr: rate(ifHCOutOctets{ifAlias=~"WAN.*"}[5m]) * 8 / (ifHighSpeed * 1e6) > 0.85
    for: 15m
    labels: { severity: warning }
    annotations:
      summary: "{{ $labels.instance }} {{ $labels.ifAlias }} > 85% นาน 15 นาที"
      runbook: "https://wiki.example/runbooks/wan-congestion"
  - alert: BgpPeerDown
    expr: bgpPeerState != 6          # 6 = established
    for: 2m
    labels: { severity: critical }
```
**ช่องทาง:** Alertmanager/Zabbix → Teams/Slack/LINE/email · on-call → PagerDuty/Opsgenie (rotation, escalation)

---

## 7. SLI, SLO, Error Budget

| คำ | ความหมาย | ตัวอย่าง |
|---|---|---|
| **SLI** (Indicator) | ตัวชี้วัดที่สะท้อนประสบการณ์ | % ของ HTTP probe ไป ERP จากสาขาที่สำเร็จภายใน 2 วินาที |
| **SLO** (Objective) | เป้าหมายภายใน | 99.9% ต่อเดือน |
| **SLA** (Agreement) | สัญญากับลูกค้า/ผู้ให้บริการ (มีบทลงโทษ) | ISP รับประกัน 99.5% |
| **Error budget** | ส่วนที่ "ล้มเหลวได้" = 100% − SLO | 0.1% ของเดือน ≈ **43 นาที** |

```
 Availability   ต่อเดือน (30 วัน)   ต่อปี
 99%            7.2 ชั่วโมง          3.65 วัน
 99.9%          43.2 นาที            8.76 ชั่วโมง
 99.99%         4.3 นาที             52.6 นาที
 99.999%        26 วินาที            5.26 นาที
```
- ใช้ error budget ตัดสินใจ: budget เหลือมาก → เปลี่ยนแปลงได้, ใกล้หมด → ชะลอ change เน้นเสถียรภาพ

---

## 8. Incident Metrics

| ตัวชี้วัด | ความหมาย | ปรับปรุงด้วย |
|---|---|---|
| **MTTD** (Mean Time To Detect) | เกิดเหตุ → รู้ตัว | synthetic, alert ที่ดี |
| **MTTA** (Acknowledge) | alert → มีคนรับ | on-call ชัดเจน |
| **MTTR** (Mean Time To Recover/Repair) | เกิด → กลับมาใช้ได้ | runbook, automation, OOB, redundancy |
| **MTBF** (Mean Time Between Failures) | ความถี่ของความเสียหาย | ฮาร์ดแวร์/การออกแบบ/change ที่ดี |

---

## 9. Dashboard ที่ดี

- **ระดับผู้บริหาร/NOC:** แผนที่สาขา (สีเขียว/แดง), SLO, incident ที่เปิดอยู่
- **ระดับบริการ:** Internet/WAN ของแต่ละสาขา (utilization, latency, loss), DNS/DHCP
- **ระดับอุปกรณ์:** interface, errors, CPU/mem, neighbors
- หลักการ: **ไม่ยัดทุกอย่างในหน้าเดียว**, ตอบคำถามเฉพาะ, ใช้ห่วงเวลาเปรียบเทียบ (สัปดาห์ก่อน), drill-down ได้, ใส่ annotation เวลามี change
- ใช้ข้อมูลจาก NetBox (Level 89) เป็น label (site, role) เพื่อกรอง/จัดกลุ่มใน Grafana

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ping ได้ = ระบบปกติ | ต้องวัดประสบการณ์จริง (synthetic) และ errors/discards |
| ค่าเฉลี่ย 5 นาที 40% = ไม่มี congestion | microburst ระดับ ms ซ่อนอยู่ — ดู discards/telemetry |
| Alert ยิ่งมากยิ่งปลอดภัย | alert fatigue ทำให้พลาดเหตุจริง |
| ใช้ counter 32-bit ได้ทุกลิงก์ | ลิงก์เร็วต้องใช้ 64-bit (ifHC*) |
| 99.9% ฟังดูสูงมาก | เท่ากับล่มได้ ~43 นาที/เดือน |

---

## 11. Cheat Sheet

```
Monitoring (ปกติไหม) vs Observability (ทำไม) · metrics · logs · traces · flows
ต้องดู: up/down · bps · errors(L1)/discards(congestion) · CPU/mem/temp · OSPF/BGP state · DNS/DHCP/NTP · cert expiry · latency/loss · config change
bps = Δoctets × 8 / Δt · ใช้ ifHC* 64-bit · SNMPv3
95th percentile = ตัด 5% บนสุด (คิดเงิน/capacity)
Tools: Zabbix · LibreNMS · PRTG · Prometheus(snmp/blackbox exporter)+Grafana+Alertmanager · Telegraf/Influx
Synthetic: ICMP/DNS/HTTP จากหลายจุด
Alert: actionable · severity · for/hysteresis · dependency/dedup · runbook · maintenance · ทบทวน
SLI/SLO/SLA · error budget (99.9% ≈ 43 นาที/เดือน) · MTTD/MTTA/MTTR/MTBF
```

---

## 12. แบบทดสอบ 10 ข้อ

1. Monitoring ต่างจาก observability อย่างไร
2. Interface errors กับ discards บอกปัญหาต่างกันอย่างไร
3. Counter ifHCInOctets เพิ่มขึ้น 750,000,000 bytes ใน 60 วินาที เท่ากับกี่ Mbps
4. ทำไมลิงก์ 10G ต้องใช้ counter 64-bit
5. 95th percentile คำนวณอย่างไร และใช้ทำอะไร
6. Synthetic monitoring มีประโยชน์อย่างไร
7. ยกหลักการลด alert fatigue 4 ข้อ
8. SLO 99.9% ต่อเดือน มี error budget กี่นาที
9. MTTD กับ MTTR ต่างกันอย่างไร ลดได้อย่างไร
10. ทำไม certificate expiry ควรอยู่ใน monitoring

<details><summary><b>เฉลย</b></summary>

1. Monitoring ตรวจสิ่งที่รู้ล่วงหน้าว่าปกติไหม; observability ช่วยหาว่า "ทำไม" ผิดปกติจากข้อมูลที่ละเอียดและสัมพันธ์กัน (metrics/logs/traces/flows)
2. Errors = frame เสีย (ปัญหา L1/L2 เช่น สาย/SFP/duplex); discards = ทิ้งเพราะ buffer เต็ม/policy (congestion)
3. 750,000,000 × 8 / 60 = 100 Mbps
4. Counter 32-bit วนกลับเร็วมาก (ภายในไม่กี่วินาทีที่ 10G) ทำให้คำนวณผิด
5. เรียงค่าตัวอย่างทั้งเดือน ตัด 5% สูงสุดออก ค่าสูงสุดที่เหลือคือ 95th percentile — ใช้คิดเงิน bandwidth และวางแผน capacity โดยไม่ถูก spike หลอก
6. วัดประสบการณ์จริงของผู้ใช้จากหลายจุด รู้ปัญหาก่อนผู้ใช้แจ้ง แม้อุปกรณ์ทุกตัวยัง up
7. Alert เฉพาะสิ่งที่ต้อง action, ระดับ severity, ระยะเวลาต่อเนื่อง/hysteresis, dependency/dedup, runbook, maintenance window, ทบทวนเป็นประจำ
8. ≈ 43.2 นาที
9. MTTD = เวลาจนตรวจพบ (ลดด้วย synthetic/alert ที่ดี); MTTR = เวลาจนกลับมาใช้ได้ (ลดด้วย runbook, automation, redundancy, OOB)
10. Certificate หมดอายุทำให้บริการล่มทันที (HTTPS, VPN, RADIUS/EAP) และป้องกันได้ 100% ด้วยการแจ้งเตือนล่วงหน้า
</details>

---

➡️ ต่อไป: **Level 87 — Flow Analysis: NetFlow, sFlow, IPFIX**
