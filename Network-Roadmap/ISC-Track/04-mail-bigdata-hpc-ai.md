# Part 4 — Enterprise Mail & Collaboration · Big Data & Analytics · HPC & AI Infrastructure (Level 74–87)

> ตามขอบเขตงาน ISC:
> - **Enterprise Mail & Collaboration:** Microsoft Exchange, Office 365, Zimbra Enterprise + Spam Filter & Anti-Virus Gateway
> - **Big Data & Data Analytics:** Enterprise Data Warehouse & Lakehouse, Real-time ETL/Data Pipelines, Executive BI Dashboards, Data Governance & Quality
> - **HPC & AI Infrastructure:** Enterprise GPU Clusters, InfiniBand/RoCE Fabric, High-IOPS Parallel File Storage, LLM & Deep Learning Workload Optimization
>
> ทั้ง 14 Level ใน Part นี้เป็นเนื้อหาใหม่

---

## Level 74 — Microsoft Exchange Server (On-premises)

**สิ่งที่ต้องรู้**
- Exchange Server Subscription Edition (SE) เป็นรุ่นปัจจุบัน (Exchange 2016/2019 สิ้นสุด support ต.ค. 2025): Mailbox server role, Edge Transport (optional)
- Mail flow: Send/Receive connectors, accepted domains, MX → (gateway) → Exchange; Autodiscover, OWA, ActiveSync, MAPI/HTTP
- HA: Database Availability Group (DAG), witness server, lagged copy, load balancer หน้า client access
- Certificate (SAN: mail, autodiscover), DNS internal/external (split DNS)
- Patch (CU + Security Update) สำคัญมาก: Exchange on-prem เป็นเป้าหมายโจมตีบ่อย (เช่น ProxyLogon/ProxyShell)
- เครื่องมือ: Exchange Admin Center, Exchange Management Shell (`Get-Mailbox`, `Get-MessageTrackingLog`, `Test-ServiceHealth`), Microsoft Remote Connectivity Analyzer

**แบบทดสอบ**
1. DAG ต่างจาก Windows Failover Cluster ทั่วไปอย่างไร
2. ทำไม certificate ต้องมีชื่อ autodiscover
3. ผู้ใช้บอกว่าอีเมลไม่ถึงผู้รับภายนอก ตรวจอะไร
4. ทำไม Exchange on-prem ต้อง patch เร็ว
5. Lagged database copy ใช้ทำอะไร

<details><summary>เฉลย</summary>

1. ไม่ใช้ shared storage แต่ละ server มีสำเนาฐานข้อมูลของตัวเอง (replication) แล้วใช้ cluster แค่ส่วน quorum/failover
2. Outlook/มือถือใช้ autodiscover หาค่าการเชื่อมต่อ ถ้า cert ไม่ตรงจะขึ้นคำเตือน/ตั้งค่าไม่ได้
3. Message tracking log, queue (`Get-Queue`), send connector, DNS/MX/SPF ของผู้รับ, blacklist ของ IP ขาออก, gateway
4. เปิดสู่อินเทอร์เน็ต (OWA/ActiveSync) และมีช่องโหว่ร้ายแรงที่ถูกใช้โจมตีจริงหลายครั้ง
5. สำเนาที่ apply log ช้ากว่ากำหนด (เช่น 7 วัน) ใช้กู้จาก logical corruption/การลบผิด
</details>

**5 โปรเจค**
- ⭐⭐ P1: Lab AD + Exchange Server (eval) 1 node: mailbox, connector, OWA
- ⭐⭐⭐ P2: DAG 2 node + witness แล้วทดสอบ failover
- ⭐⭐ P3: Message tracking script (PowerShell) สรุปอีเมลที่ส่งไม่ถึงรายวัน
- ⭐⭐ P4: Exchange hardening & patch checklist
- ⭐⭐ P5: Mail flow diagram + DNS record ครบชุด (MX, SPF, DKIM, DMARC, autodiscover) สำหรับลูกค้า

---

## Level 75 — Microsoft 365 / Exchange Online & Hybrid

**สิ่งที่ต้องรู้**
- Tenant, domain verification, license (Business/E3/E5), Entra ID, MFA/Conditional Access
- Identity: cloud-only, Entra Connect Sync / Cloud Sync (password hash sync, pass-through)
- Exchange Hybrid (Hybrid Configuration Wizard), migration: cutover, staged, hybrid remote move, IMAP, PST
- Exchange Online Protection (EOP), Defender for Office 365 (Safe Links, Safe Attachments), retention, eDiscovery
- Teams/SharePoint/OneDrive พื้นฐาน, admin center, Microsoft 365 backup (ข้อมูลใน cloud ก็ต้อง backup ตามนโยบายองค์กร)

**แบบทดสอบ**
1. ทำไมองค์กรต้อง backup Microsoft 365 แม้อยู่บน cloud
2. Hybrid migration เหมาะกับองค์กรแบบไหน
3. Password hash sync ข้อดีคืออะไร
4. Safe Links ทำงานอย่างไร
5. ก่อนสลับ MX ไป Exchange Online ต้องเตรียมอะไร

<details><summary>เฉลย</summary>

1. Shared responsibility: Microsoft ดูแลความพร้อมของบริการ แต่การลบผิด/ransomware/retention ระยะยาวเป็นหน้าที่ลูกค้า
2. องค์กรใหญ่ที่ย้ายทีละกลุ่ม ต้องการ free/busy และ GAL ร่วมกันระหว่างย้าย
3. ผู้ใช้ login cloud ได้แม้ AD on-prem ล่ม และรองรับ leaked credential detection
4. เขียน URL ใหม่ให้ตรวจตอนผู้ใช้คลิก (time-of-click) แล้ว block ถ้าเป็นอันตราย
5. ย้าย mailbox ครบ, ลด TTL, อัปเดต SPF/DKIM/DMARC, ตั้ง connector กับ gateway (ถ้ามี), แจ้งผู้ใช้
</details>

**5 โปรเจค**
- ⭐⭐ P1: M365 developer/trial tenant + custom domain + MFA/Conditional Access
- ⭐⭐ P2: Entra Cloud Sync จาก AD lab
- ⭐⭐ P3: Migration plan (on-prem → Exchange Online) 500 mailbox
- ⭐⭐ P4: PowerShell (Exchange Online module) รายงาน mailbox size, license, MFA status
- ⭐⭐⭐ P5: Email security baseline สำหรับ M365 (anti-phishing, Safe Links/Attachments, DMARC reject)

---

## Level 76 — Zimbra Enterprise Mail

**สิ่งที่ต้องรู้**
- Zimbra Collaboration (Network Edition สำหรับ enterprise / open-source edition): องค์ประกอบ mailbox (Jetty/Java), MTA (Postfix + Amavis/SpamAssassin/ClamAV), proxy (Nginx), LDAP (OpenLDAP), logger
- Single server vs multi-server (แยก LDAP/MTA/proxy/mailbox), HSM (เก็บข้อมูลเก่าใน storage ราคาถูก)
- งานที่ต้องทำได้: domain/COS/account, quota, SSL cert, DKIM, backup/restore (Network Edition), อัปเกรด/patch
- CLI: `zmcontrol status`, `zmprov`, `zmmailbox`, `postqueue -p`, log ที่ `/var/log/zimbra.log`
- ภาครัฐ/มหาวิทยาลัยไทยหลายแห่งใช้ Zimbra เนื่องจากต้นทุนและเก็บข้อมูลในประเทศได้

**แบบทดสอบ**
1. Zimbra ใช้ซอฟต์แวร์อะไรเป็น MTA
2. คำสั่งดูสถานะบริการทั้งหมด
3. COS ใช้ทำอะไร
4. ทำไมต้องแยก MTA/proxy ออกจาก mailbox ในองค์กรใหญ่
5. ดูอีเมลค้างในคิวอย่างไร

<details><summary>เฉลย</summary>

1. Postfix (ร่วมกับ Amavis, SpamAssassin, ClamAV)
2. `zmcontrol status` (รันด้วย user zimbra)
3. Class of Service: กำหนด quota/ฟีเจอร์/นโยบายให้กลุ่มผู้ใช้
4. Scale และความปลอดภัย: ส่วนที่หันหน้าอินเทอร์เน็ตแยกจากที่เก็บข้อมูล, ขยายแต่ละส่วนได้อิสระ
5. `postqueue -p` (หรือ `/opt/zimbra/common/sbin/postqueue -p`) และ Admin console
</details>

**5 โปรเจค**
- ⭐⭐ P1: ติดตั้ง Zimbra (single server) บน Ubuntu VM + domain + SSL
- ⭐⭐ P2: ตั้ง DKIM + SPF + DMARC แล้วทดสอบด้วย mail-tester
- ⭐⭐ P3: สคริปต์ `zmprov` สร้างบัญชีจาก CSV + ตั้ง COS
- ⭐⭐ P4: Backup/restore plan ของ Zimbra (Network Edition หรือ script สำหรับ open-source)
- ⭐⭐⭐ P5: Multi-server design สำหรับ 10,000 mailbox (มหาวิทยาลัย) + sizing storage

---

## Level 77 — Email Security Gateway & Mail Migration

**สิ่งที่ต้องรู้**
- Gateway หน้า mail server: FortiMail, Proofpoint, Trend Micro, Cisco Secure Email, Sophos; หรือ cloud (Defender for O365, Mimecast)
- ฟีเจอร์: anti-spam (reputation, content, Bayesian), anti-virus, sandbox, URL rewrite, DLP, quarantine, TLS enforcement, outbound filtering
- SPF/DKIM/DMARC (ต่อยอด SI L52), BIMI, MTA-STS
- Mail migration: Zimbra/Exchange ↔ M365 ↔ Zimbra ผ่าน IMAP sync (imapsync), PST, เครื่องมือเชิงพาณิชย์ (BitTitan MigrationWiz, CodeTwo); coexistence; MX cutover
- Communication กับผู้ใช้: ตั้ง Outlook/มือถือใหม่, คู่มือ, helpdesk ช่วงย้าย

**แบบทดสอบ**
1. Gateway ควรวางที่ไหนใน mail flow
2. Outbound filtering มีไว้ทำไม
3. imapsync ทำอะไร และย้ายอะไรไม่ได้
4. ลำดับ MX cutover ที่ปลอดภัย
5. DMARC report ช่วยอะไรก่อนตั้ง p=reject

<details><summary>เฉลย</summary>

1. ระหว่างอินเทอร์เน็ตกับ mail server (MX ชี้ไป gateway) ทั้งขาเข้าและขาออก
2. ป้องกันเครื่อง/บัญชีที่ถูกยึดส่ง spam ออกไปจน IP/domain ติด blacklist
3. Copy อีเมลระหว่าง IMAP server แบบ incremental; ไม่ย้ายปฏิทิน/รายชื่อ/กฎได้ครบ (ต้องใช้วิธีอื่น)
4. Pre-sync ข้อมูลส่วนใหญ่ → ลด TTL → สลับ MX ช่วงเวลาที่อีเมลน้อย → delta sync → ตรวจ mail flow → ปิดระบบเดิมหลังรอบยืนยัน
5. เห็นว่าระบบใดส่งในนามโดเมนบ้าง แก้ SPF/DKIM ให้ครบก่อน ไม่ให้อีเมลจริงถูกปฏิเสธ
</details>

**5 โปรเจค**
- ⭐⭐ P1: Postfix + Rspamd/SpamAssassin + ClamAV เป็น gateway หน้า Zimbra lab
- ⭐⭐ P2: imapsync migration Zimbra → mailbox ปลายทาง (lab) + log สรุป
- ⭐⭐ P3: DMARC report parser (Python) สรุปแหล่งส่งที่ไม่ผ่าน
- ⭐⭐ P4: Mail migration runbook + เอกสารคู่มือผู้ใช้
- ⭐⭐⭐ P5: Proposal ย้ายระบบอีเมลมหาวิทยาลัย (Zimbra vs M365 vs hybrid) พร้อม TCO และแผนย้าย

---

## Level 78 — Data Platform Fundamentals: Warehouse, Lake, Lakehouse

**สิ่งที่ต้องรู้**
- OLTP (ระบบงาน: ERP, HIS) vs OLAP (วิเคราะห์)
- Data Warehouse (schema-on-write, star/snowflake schema), Data Lake (schema-on-read, ไฟล์ดิบ), Lakehouse (table format บน object storage: Delta Lake, Apache Iceberg, Hudi)
- Columnar format (Parquet, ORC), partitioning, compression
- Medallion architecture: Bronze (raw) → Silver (clean) → Gold (business)
- Batch vs streaming; data mart
- โครงสร้างพื้นฐานที่ SI ต้องจัดเตรียม: object storage (S3-compatible), compute cluster, network 25G+, backup

**แบบทดสอบ**
1. ทำไมไม่ควรรัน report หนัก ๆ บนฐานข้อมูล ERP ตรง ๆ
2. Lakehouse แก้ปัญหาอะไรของ data lake
3. ทำไม Parquet เร็วสำหรับ query วิเคราะห์
4. Star schema ประกอบด้วยอะไร
5. Medallion Bronze/Silver/Gold คืออะไร

<details><summary>เฉลย</summary>

1. แย่ง resource กับธุรกรรมจริง ทำให้ระบบงานช้า
2. เพิ่ม ACID transaction, schema enforcement, time travel บนไฟล์ใน lake (ไม่กลายเป็น data swamp)
3. เก็บแบบคอลัมน์ อ่านเฉพาะคอลัมน์ที่ใช้ บีบอัดได้ดี และข้ามข้อมูลด้วย statistics
4. Fact table (ตัวเลขธุรกรรม) + dimension table (ลูกค้า, สินค้า, เวลา)
5. Bronze = ข้อมูลดิบ, Silver = ทำความสะอาด/รวม, Gold = พร้อมใช้ทางธุรกิจ (KPI/รายงาน)
</details>

**5 โปรเจค**
- ⭐ P1: Diagram เปรียบเทียบ warehouse/lake/lakehouse + use case
- ⭐⭐ P2: แปลง CSV ขนาดใหญ่เป็น Parquet (pandas/pyarrow/DuckDB) แล้วเทียบเวลา query
- ⭐⭐ P3: ออกแบบ star schema สำหรับยอดขาย/การรักษาผู้ป่วย
- ⭐⭐ P4: MinIO + DuckDB/Trino query Parquet บน object storage
- ⭐⭐⭐ P5: Lakehouse lab: MinIO + Apache Iceberg (หรือ Delta) + Spark/Trino พร้อม medallion 3 ชั้น

---

## Level 79 — Data Pipelines: ETL/ELT & Real-time

**สิ่งที่ต้องรู้**
- ETL vs ELT; orchestration: Apache Airflow, Dagster; transformation: dbt, Spark
- Real-time: Apache Kafka (topic, partition, consumer group), CDC จากฐานข้อมูล (Debezium), stream processing (Flink, Spark Structured Streaming)
- Idempotent pipeline, incremental load, late-arriving data, retry/alert
- Data quality check ระหว่าง pipeline
- โครงสร้างพื้นฐาน: Kafka cluster 3 broker+, disk throughput, network, monitoring

**แบบทดสอบ**
1. ETL ต่างจาก ELT อย่างไร
2. CDC ช่วยอะไรเทียบกับ dump ทั้งตารางทุกคืน
3. Kafka partition มีผลต่ออะไร
4. Idempotent pipeline คืออะไร
5. ทำไม Kafka cluster ควรมีอย่างน้อย 3 broker

<details><summary>เฉลย</summary>

1. ETL แปลงก่อนโหลดเข้าปลายทาง; ELT โหลดดิบก่อนแล้วแปลงในปลายทาง (ใช้พลังของ warehouse/lakehouse)
2. ส่งเฉพาะการเปลี่ยนแปลงแบบเกือบ real-time ลดภาระฐานข้อมูลต้นทาง
3. Parallelism (จำนวน consumer ที่ทำงานพร้อมกัน) และลำดับข้อมูล (เรียงเฉพาะภายใน partition)
4. รันซ้ำแล้วผลเหมือนเดิม ไม่เกิดข้อมูลซ้ำ
5. ใช้ replication factor 3 ทนต่อ broker เสีย 1 ตัวและยังเขียนได้ (min.insync.replicas = 2)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Airflow DAG ดึงข้อมูล API → Parquet → load ทุกวัน
- ⭐⭐ P2: dbt project สร้าง model Silver/Gold + test
- ⭐⭐⭐ P3: PostgreSQL → Debezium → Kafka → sink ลง lakehouse (docker compose)
- ⭐⭐ P4: Monitoring pipeline (เวลา, จำนวนแถว, error) + alert
- ⭐⭐⭐ P5: Real-time dashboard จาก Kafka stream (เช่น ข้อมูล sensor โรงงาน)

---

## Level 80 — Data Warehouse / Lakehouse Platforms & Infrastructure Sizing

**สิ่งที่ต้องรู้**
- On-prem/open-source: ClickHouse, Apache Spark + Iceberg + Trino, PostgreSQL (+ columnar extension), Greenplum (ตรวจสถานะ license ก่อนเสนอ)
- Commercial/cloud: Snowflake, Databricks, Google BigQuery, Microsoft Fabric/Azure Synapse, Amazon Redshift
- Hybrid: เก็บข้อมูลอ่อนไหวในประเทศ (PDPA) + compute บน cloud ตามความเหมาะสม
- Sizing: ปริมาณข้อมูลดิบ × growth, compression ratio, จำนวนผู้ใช้/query concurrency, SLA เวลา query; แยก storage กับ compute
- Hardware: server CPU core สูง + RAM มาก, NVMe สำหรับ hot data, object storage สำหรับ lake, network 25/100G
- Security: encryption, RBAC/row-level security, masking ข้อมูลส่วนบุคคล

**แบบทดสอบ**
1. ข้อดีของการแยก storage กับ compute
2. ClickHouse เหมาะกับงานแบบไหน
3. ปัจจัยในการตัดสินใจ on-prem vs cloud data platform
4. Row-level security ใช้ทำอะไร
5. ข้อมูลดิบ 20 TB/ปี compression 5:1 เก็บ 3 ปี ต้องใช้ storage ประมาณเท่าไร (ก่อน replication)

<details><summary>เฉลย</summary>

1. ขยายแต่ละส่วนตามความต้องการได้อิสระ จ่ายเฉพาะที่ใช้ และ compute หลายกลุ่มใช้ข้อมูลเดียวกันได้
2. Analytics แบบ real-time ปริมาณมาก (log, event, time-series) query เร็วมาก
3. Data residency/PDPA, ค่าใช้จ่ายระยะยาว, ทักษะทีม, ความผันผวนของโหลด, integration
4. จำกัดให้ผู้ใช้เห็นเฉพาะแถวที่ได้รับสิทธิ์ (เช่น สาขาตัวเอง)
5. 20 × 3 / 5 = 12 TB (+ เผื่อ temp/โต และ × replication/RAID)
</details>

**5 โปรเจค**
- ⭐⭐ P1: ClickHouse lab + โหลดข้อมูลตัวอย่าง (เช่น NYC taxi) แล้ววัดเวลา query
- ⭐⭐ P2: ตารางเปรียบเทียบ data platform 6 ตัว (license, deployment, ราคา, ทักษะ)
- ⭐⭐ P3: Sizing calculator สำหรับ lakehouse (data, compute, storage, network)
- ⭐⭐ P4: Security design: RBAC, row-level security, masking ข้อมูลส่วนบุคคล
- ⭐⭐⭐ P5: HLD data platform สำหรับโรงพยาบาลเครือข่าย 5 แห่ง (on-prem + hybrid)

---

## Level 81 — Executive BI Dashboards & Data Visualization

**สิ่งที่ต้องรู้**
- เครื่องมือ: Power BI, Tableau, Looker Studio, Apache Superset, Metabase, Grafana (operational)
- Semantic model / data model, measure (DAX), refresh (import vs DirectQuery/live), gateway สำหรับข้อมูล on-prem
- หลักออกแบบ dashboard ผู้บริหาร: KPI ไม่เกิน 5–7 ตัว, เปรียบเทียบกับเป้า/ช่วงก่อน, drill-down, ใช้กราฟเหมาะกับข้อมูล
- Row-level security, การแชร์, performance
- Requirement workshop กับผู้บริหาร: คำถามธุรกิจ → KPI → แหล่งข้อมูล

**แบบทดสอบ**
1. Import กับ DirectQuery ต่างกันอย่างไร
2. ทำไม dashboard ผู้บริหารไม่ควรมีกราฟมากเกินไป
3. On-premises data gateway ใช้ทำอะไร
4. KPI ที่ดีต้องมีอะไร
5. กราฟแบบไหนเหมาะกับแนวโน้มตามเวลา

<details><summary>เฉลย</summary>

1. Import คัดลอกข้อมูลเข้า model (เร็ว แต่ต้อง refresh); DirectQuery query แหล่งข้อมูลจริงทุกครั้ง (สด แต่ขึ้นกับ performance ต้นทาง)
2. ผู้บริหารต้องเห็นประเด็นสำคัญเร็ว กราฟมากทำให้ไม่โฟกัส
3. ให้ BI บน cloud เข้าถึงข้อมูลในเครือข่ายองค์กรอย่างปลอดภัย
4. นิยามชัดเจน, เป้าหมาย, เจ้าของ, แหล่งข้อมูล, ความถี่การอัปเดต
5. Line chart
</details>

**5 โปรเจค**
- ⭐⭐ P1: Power BI Desktop (ฟรี) หรือ Superset: dashboard ยอดขาย/ผู้ป่วยจาก star schema (L78)
- ⭐⭐ P2: KPI definition document กับ "ผู้บริหาร" สมมติ
- ⭐⭐ P3: Row-level security ตามสาขา
- ⭐⭐ P4: Operational dashboard (Grafana) ของ data pipeline
- ⭐⭐⭐ P5: Executive dashboard ครบชุด + คู่มือการใช้งาน + นำเสนอ 10 นาที

---

## Level 82 — Data Governance, Data Quality & PDPA

**สิ่งที่ต้องรู้**
- Data governance: data owner/steward, policy, data catalog (DataHub, OpenMetadata, Microsoft Purview), lineage, glossary
- Data quality: completeness, accuracy, consistency, timeliness, uniqueness; เครื่องมือ Great Expectations, Soda, dbt tests
- PDPA: ข้อมูลส่วนบุคคล/อ่อนไหว (สุขภาพ), lawful basis, retention, สิทธิ์เจ้าของข้อมูล, การรายงานเหตุละเมิด
- Masking/pseudonymization/anonymization, access control, audit log
- Master data management (MDM) เบื้องต้น

**แบบทดสอบ**
1. Data lineage มีประโยชน์อย่างไร
2. Pseudonymization ต่างจาก anonymization อย่างไร
3. มิติ data quality 5 ข้อ
4. ข้อมูลสุขภาพตาม PDPA จัดเป็นข้อมูลประเภทใด
5. ทำไมต้องมี data owner

<details><summary>เฉลย</summary>

1. รู้ว่าข้อมูลมาจากไหน ผ่านการแปลงอะไร ประเมินผลกระทบเมื่อแก้ระบบต้นทาง และใช้ตรวจสอบ
2. Pseudonymization แทนตัวระบุด้วยรหัส (ย้อนกลับได้ด้วย key ยังเป็นข้อมูลส่วนบุคคล); anonymization ระบุตัวบุคคลไม่ได้อีก
3. Completeness, accuracy, consistency, timeliness, uniqueness (และ validity)
4. ข้อมูลส่วนบุคคลอ่อนไหว (มาตรา 26) ต้องได้รับความยินยอมโดยชัดแจ้งหรือมีฐานตามกฎหมาย
5. มีผู้รับผิดชอบตัดสินใจเรื่องนิยาม สิทธิ์ และคุณภาพข้อมูล
</details>

**5 โปรเจค**
- ⭐⭐ P1: OpenMetadata/DataHub + เชื่อม PostgreSQL/lakehouse lab + lineage
- ⭐⭐ P2: Great Expectations/dbt tests 10 rule กับ pipeline L79
- ⭐⭐ P3: Masking view สำหรับข้อมูลส่วนบุคคล (เลขบัตร, เบอร์โทร)
- ⭐⭐ P4: Data governance policy template (บทบาท, กระบวนการขอข้อมูล, retention)
- ⭐⭐⭐ P5: **Capstone Big Data:** โรงพยาบาลเครือข่าย — CDC จาก HIS → lakehouse → dashboard ผู้บริหาร พร้อม governance และ PDPA

---

## Level 83 — HPC & AI Infrastructure Fundamentals

> พื้นฐานจาก Roadmap หลัก [L98](../10-expert-career.md)

**สิ่งที่ต้องรู้**
- HPC (simulation, งานวิจัย) vs AI training vs AI inference: รูปแบบ compute, network, storage ต่างกัน
- GPU server: NVIDIA (เช่น H100/H200, B200, L40S), AMD Instinct; HGX/DGX 8 GPU ต่อ node, NVLink/NVSwitch ภายใน node
- ทรัพยากรสำคัญ: GPU memory (HBM), GPU interconnect, CPU/RAM สำหรับ data loading, NVMe local
- Facility: กินไฟ 10 kW ขึ้นไปต่อ server (rack 40–100+ kW), ต้อง liquid cooling/rear-door heat exchanger ในระบบหนาแน่น, ไฟฟ้า 3 เฟส
- Sizing เบื้องต้น: model size → VRAM (FP16 = 2 byte/parameter), dataset, ระยะเวลา train, จำนวนผู้ใช้ inference
- Software stack: GPU driver, CUDA, NCCL, container

**แบบทดสอบ**
1. AI training กับ inference ต้องการ infrastructure ต่างกันอย่างไร
2. Model 70B parameter ใน FP16 ต้องการ GPU memory สำหรับ weight อย่างน้อยเท่าไร
3. NVLink มีไว้ทำอะไร
4. ทำไมห้อง server เดิมมักรองรับ GPU server ไม่ได้
5. ทำไม GPU server ยังต้องการ CPU/RAM/NVMe ที่ดี

<details><summary>เฉลย</summary>

1. Training: GPU จำนวนมาก + fabric ความเร็วสูง + storage throughput สูง ทำงานยาว; Inference: latency/throughput ต่อ request, scale ตามผู้ใช้, GPU น้อยกว่าต่อ model
2. 70B × 2 byte ≈ 140 GB (ยังไม่รวม KV cache/activation) → ต้องใช้หลาย GPU หรือ quantize
3. เชื่อม GPU ภายใน node ด้วย bandwidth สูงกว่า PCIe มาก สำหรับแลกข้อมูลระหว่าง GPU
4. พลังงานและความร้อนต่อ rack สูงกว่าที่ออกแบบไว้มาก (ไฟ/แอร์/น้ำหนักไม่พอ)
5. ป้อนข้อมูลให้ GPU ทัน (data loading/preprocessing) ไม่เช่นนั้น GPU ว่างรอ
</details>

**5 โปรเจค**
- ⭐⭐ P1: VRAM calculator (parameter, precision, batch, context → GPU ที่ต้องใช้)
- ⭐⭐ P2: Power/cooling plan สำหรับ GPU server 4 เครื่อง (ต่อยอด L22)
- ⭐⭐ P3: ตารางเปรียบเทียบ GPU รุ่นปัจจุบัน (memory, bandwidth, TDP, use case)
- ⭐⭐ P4: Requirement questionnaire สำหรับลูกค้า AI/HPC (workload, model, ผู้ใช้, data)
- ⭐⭐⭐ P5: HLD GPU cluster ขนาดเล็ก (4 node × 8 GPU) สำหรับมหาวิทยาลัย/งานวิจัย

---

## Level 84 — GPU Cluster Software: Drivers, Containers, Slurm & Kubernetes

**สิ่งที่ต้องรู้**
- NVIDIA driver + CUDA toolkit, `nvidia-smi`, DCGM (monitoring/health), MIG (แบ่ง GPU), vGPU (virtualization)
- Container: NVIDIA Container Toolkit, NGC images, Apptainer/Singularity (HPC)
- Scheduler: Slurm (partition, QoS, fair-share, GRES gpu, `sbatch`/`srun`), Kubernetes + NVIDIA GPU Operator (time-slicing, MIG)
- Provisioning: PXE/Warewulf/xCAT/Bright (Base Command Manager), Ansible
- User management: LDAP, quota, accounting; Open OnDemand (เว็บพอร์ทัลสำหรับนักวิจัย)
- Monitoring: DCGM exporter → Prometheus/Grafana, GPU utilization ต่อ job

**แบบทดสอบ**
1. MIG ใช้ทำอะไร
2. Slurm GRES คืออะไร
3. ทำไม HPC นิยม Apptainer มากกว่า Docker บน shared cluster
4. GPU Operator บน Kubernetes จัดการอะไรให้
5. ตัวชี้วัดว่า GPU ถูกใช้คุ้มค่า

<details><summary>เฉลย</summary>

1. แบ่ง GPU ระดับ hardware เป็นหลาย instance ที่แยก memory/compute ให้หลายผู้ใช้/งาน inference เล็ก
2. Generic Resource: ระบุทรัพยากรพิเศษ (GPU) ที่ job ขอได้ เช่น `--gres=gpu:2`
3. ไม่ต้องให้สิทธิ์ root/daemon แก่ผู้ใช้ รันด้วยสิทธิ์ผู้ใช้ ปลอดภัยกว่าใน multi-user
4. ติดตั้ง driver, container toolkit, device plugin, DCGM exporter, MIG manager อัตโนมัติ
5. GPU utilization/SM activity, memory usage, job wait time, สัดส่วนเวลาที่ GPU ว่าง
</details>

**5 โปรเจค**
- ⭐⭐ P1: Slurm cluster 1 controller + 2 compute (VM/docker) + submit job ตัวอย่าง
- ⭐⭐ P2: Cloud GPU instance (ใช้ชั่วคราว แล้วลบทิ้ง) ติดตั้ง driver + container toolkit + `nvidia-smi`
- ⭐⭐ P3: DCGM exporter + Grafana dashboard (ใช้ GPU จริงหรือข้อมูลตัวอย่าง)
- ⭐⭐⭐ P4: k3s + NVIDIA GPU Operator (ถ้ามี GPU) หรือเขียน design + manifest สำหรับลูกค้า
- ⭐⭐ P5: User guide สำหรับนักวิจัย: login, ส่ง job, quota, ข้อปฏิบัติ

---

## Level 85 — Ultra Low-Latency Fabric: InfiniBand & RoCE

**สิ่งที่ต้องรู้**
- InfiniBand: HDR 200G / NDR 400G / XDR 800G, Subnet Manager (OpenSM/UFM), fat-tree non-blocking, credit-based flow control (lossless โดยธรรมชาติ)
- RoCEv2 บน Ethernet (UDP 4791): ต้องตั้ง lossless (PFC + ECN/DCQCN), DSCP/priority, buffer; switch Spectrum/Arista/Cisco Nexus
- Rail-optimized topology (GPU ลำดับเดียวกันของทุก node ต่อ leaf เดียวกัน), แยก compute fabric / storage fabric / management
- RDMA, GPUDirect RDMA, NIC (ConnectX, BlueField)
- Testing: `ibstat`, `ibdiagnet`, `ib_write_bw`/`ib_read_lat` (perftest), NCCL tests (`all_reduce_perf`)
- Cabling: DAC/AOC/optic 400G (OSFP/QSFP112), จำนวนสายมาก ต้องวางแผนละเอียด

**แบบทดสอบ**
1. Subnet Manager ใน InfiniBand ทำหน้าที่อะไร
2. ทำไม RoCE ต้องตั้ง PFC/ECN
3. Rail-optimized topology ช่วยอะไร
4. NCCL all_reduce test ใช้ตรวจอะไร
5. ทำไมต้องแยก compute fabric กับ storage fabric

<details><summary>เฉลย</summary>

1. ค้นหา topology, แจก LID, คำนวณ routing table ให้ทุก switch
2. RDMA ทนต่อ packet loss ได้แย่ (retransmit แพง) ต้องทำ Ethernet ให้ไม่ drop และลดอัตราก่อน congestion
3. Traffic collective ระหว่าง GPU ลำดับเดียวกันอยู่ใน leaf เดียว ลด hop และ congestion
4. Bandwidth จริงของ collective communication ข้าม GPU/node — ยืนยันว่า fabric ทำงานเต็มประสิทธิภาพ
5. ไม่ให้ traffic อ่าน checkpoint/dataset รบกวน traffic การ train ระหว่าง GPU
</details>

**5 โปรเจค**
- ⭐⭐ P1: Soft-RoCE (rdma_rxe) บน 2 Linux VM + perftest (ต่อยอด Roadmap L98)
- ⭐⭐ P2: Fabric design 32 GPU (4 node) แบบ rail-optimized + BOM สาย/optic
- ⭐⭐ P3: QoS config template PFC/ECN สำหรับ RoCE (SONiC/cEOS lab)
- ⭐⭐⭐ P4: Acceptance test plan GPU cluster (ibdiagnet, perftest, NCCL tests, burn-in) + เกณฑ์ผ่าน
- ⭐⭐ P5: เปรียบเทียบ InfiniBand vs RoCE (ราคา, ความซับซ้อน, ทักษะทีม, ผู้ผลิต) สำหรับลูกค้า

---

## Level 86 — High-IOPS Parallel File Storage

**สิ่งที่ต้องรู้**
- ทำไมต้อง parallel FS: GPU หลายร้อยตัวอ่านข้อมูลพร้อมกัน ต้อง throughput สูง (GB/s – TB/s) และ metadata เร็ว
- ระบบ: Lustre (MDS/MDT, OSS/OST), IBM Storage Scale (GPFS), BeeGFS, WEKA, DDN EXAScaler, VAST Data
- Tiering: NVMe hot tier + object/HDD capacity tier; checkpoint storage
- GPUDirect Storage (อ่านจาก storage เข้า GPU memory โดยตรง)
- Benchmark: IOR, mdtest, fio; client mount ผ่าน IB/RoCE
- Backup/archive ข้อมูลวิจัยขนาดใหญ่

**แบบทดสอบ**
1. Lustre แยก metadata กับ data อย่างไร
2. ทำไม NFS server เดี่ยวไม่พอสำหรับ GPU cluster ใหญ่
3. Checkpoint คืออะไร ทำไมกระทบ storage
4. IOR กับ mdtest วัดอะไร
5. GPUDirect Storage ช่วยอะไร

<details><summary>เฉลย</summary>

1. Metadata อยู่ที่ MDS/MDT, ข้อมูลไฟล์กระจาย (stripe) ไปหลาย OST บนหลาย OSS
2. Server เดียวเป็นคอขวดทั้ง bandwidth และ metadata
3. บันทึก state ของ model ระหว่าง train เป็นระยะ เขียนข้อมูลใหญ่พร้อมกันทั้ง cluster ทำให้เกิด burst
4. IOR = throughput อ่าน/เขียน; mdtest = performance ของ metadata (create/stat/delete)
5. ลดการคัดลอกผ่าน CPU memory ทำให้ latency ต่ำลงและ CPU ว่างขึ้น
</details>

**5 โปรเจค**
- ⭐⭐ P1: BeeGFS lab (VM 3–4 ตัว: mgmt, meta, storage, client)
- ⭐⭐ P2: IOR/mdtest/fio benchmark เทียบกับ NFS เดี่ยว
- ⭐⭐ P3: Storage sizing สำหรับ GPU cluster (dataset, checkpoint, throughput ต่อ GPU)
- ⭐⭐ P4: เปรียบเทียบ parallel FS 5 ตัว (open-source vs commercial)
- ⭐⭐⭐ P5: Data lifecycle design: hot NVMe → capacity → archive/backup สำหรับศูนย์วิจัย

---

## Level 87 — LLM & Deep Learning Workload Optimization

**สิ่งที่ต้องรู้**
- Distributed training: data parallel (DDP), FSDP/ZeRO, tensor/pipeline parallel; NCCL; mixed precision (BF16/FP8)
- Fine-tuning แบบประหยัด: LoRA/QLoRA
- Inference serving: vLLM (PagedAttention, continuous batching), NVIDIA Triton/TensorRT-LLM, SGLang, Ollama/llama.cpp (ขนาดเล็ก)
- Quantization (INT8/INT4, AWQ/GPTQ) ลด VRAM, KV cache sizing, context length
- Metric: tokens/s, time to first token (TTFT), GPU utilization, cost per 1M tokens
- On-prem LLM เพื่อ data privacy (PDPA) + RAG (vector DB) + access control/audit

**แบบทดสอบ**
1. Continuous batching ช่วยอะไรใน inference
2. QLoRA ต่างจาก full fine-tuning อย่างไร
3. ทำไม context ยาวกิน GPU memory มากขึ้น
4. TTFT คืออะไร สำคัญกับผู้ใช้อย่างไร
5. ทำไมองค์กรไทยบางแห่งเลือก LLM on-prem

<details><summary>เฉลย</summary>

1. รวม request ใหม่เข้า batch ระหว่างที่ request เดิมยัง generate อยู่ ทำให้ GPU ทำงานเต็มที่ขึ้น throughput สูงขึ้น
2. Fine-tune เฉพาะ adapter เล็ก ๆ บน model ที่ quantize 4-bit ใช้ VRAM น้อยกว่ามาก
3. KV cache โตตามความยาว context × จำนวน request พร้อมกัน
4. Time To First Token: เวลาจนเห็นคำแรก มีผลต่อความรู้สึกว่าระบบตอบเร็ว
5. ข้อมูลอ่อนไหวไม่ออกนอกองค์กร (PDPA/ความลับ), ควบคุมค่าใช้จ่ายระยะยาว, ปรับแต่งได้
</details>

**5 โปรเจค**
- ⭐⭐ P1: Ollama/llama.cpp รัน model เล็กบน CPU/GPU แล้ววัด tokens/s
- ⭐⭐ P2: vLLM บน cloud GPU (ชั่วคราว) + load test (TTFT, throughput) ที่ concurrency ต่าง ๆ
- ⭐⭐ P3: QLoRA fine-tune model เล็กด้วย dataset ตัวอย่าง (Colab/cloud GPU)
- ⭐⭐⭐ P4: RAG ภายในองค์กร (vector DB + LLM on-prem) พร้อม access control และ audit log
- ⭐⭐⭐ P5: **Capstone HPC & AI:** มหาวิทยาลัยวิจัย — GPU cluster 4 node + IB/RoCE + parallel FS + Slurm/K8s + LLM serving: HLD, sizing, power/cooling, BOM, acceptance test
