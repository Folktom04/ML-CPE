# บทเรียน Level 82 — Ansible for Network (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า Ansible ทำงานกับอุปกรณ์ network อย่างไร (agentless, network_cli) · เขียน inventory, group_vars/host_vars · playbook, task, module, handler · resource modules และ state · Jinja2 template · idempotency, `--check --diff` · ansible-vault · role และโครงสร้างโปรเจค · AWX/AAP · pattern งานจริง (baseline, backup, compliance)

---

## 1. Ansible คืออะไร

**Ansible** = เครื่องมือ automation แบบ **declarative-ish** ที่อธิบาย "สถานะที่ต้องการ" ด้วยไฟล์ YAML (playbook)

| คุณสมบัติ | อธิบาย |
|---|---|
| **Agentless** | ไม่ต้องติดตั้งอะไรบนอุปกรณ์ — ใช้ SSH/API |
| **YAML** | อ่านง่ายกว่าโค้ด เหมาะกับทีม network |
| **Idempotent** (ถ้าใช้ module ที่ถูกต้อง) | รันซ้ำได้ผลเหมือนเดิม |
| **Multi-vendor** | collections ของ Cisco, Arista, Juniper, Fortinet, Palo Alto, F5, ฯลฯ |

### การทำงานกับอุปกรณ์ network ต่างจาก server
- Server: Ansible copy โค้ด Python ไปรันบนเครื่องปลายทาง
- **Network: module รันบน control node** แล้วคุยกับอุปกรณ์ผ่าน connection plugin:

| connection | ใช้กับ |
|---|---|
| `ansible.netcommon.network_cli` ⭐ | SSH CLI (IOS, NX-OS, EOS, Junos CLI) |
| `ansible.netcommon.netconf` | NETCONF (Junos, IOS-XE, IOS-XR) |
| `ansible.netcommon.httpapi` | REST API (EOS eAPI, NX-API, FortiOS, PAN-OS) |
| `local` | module ที่เรียก API เอง (บางรุ่นเก่า) |

---

## 2. ติดตั้งและโครงสร้างโปรเจค

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install ansible-core ansible-pylibssh paramiko
ansible-galaxy collection install cisco.ios arista.eos junipernetworks.junos ansible.netcommon ansible.utils
```
```
network-automation/
├── ansible.cfg
├── inventory/
│   ├── hosts.yml
│   ├── group_vars/
│   │   ├── all.yml          # ค่าร่วม (NTP, syslog, DNS)
│   │   ├── ios.yml          # connection ของ Cisco IOS
│   │   └── vault.yml        # รหัสผ่าน (เข้ารหัสด้วย ansible-vault)
│   └── host_vars/
│       └── sw-acc-01.yml    # ค่าเฉพาะเครื่อง (VLAN, interface)
├── playbooks/
│   ├── baseline.yml
│   └── backup.yml
├── roles/
│   └── vlans/ (tasks/, templates/, defaults/)
└── templates/
```
```ini
# ansible.cfg
[defaults]
inventory = inventory/hosts.yml
host_key_checking = True          ; อย่าปิดใน production (ใช้ known_hosts)
forks = 20                        ; ทำพร้อมกันกี่เครื่อง
retry_files_enabled = False
[persistent_connection]
command_timeout = 60
```

---

## 3. Inventory และ Variables

```yaml
# inventory/hosts.yml
all:
  children:
    ios:
      children:
        core:
          hosts:
            core-01: { ansible_host: 10.0.0.1 }
            core-02: { ansible_host: 10.0.0.2 }
        access:
          hosts:
            sw-acc-01: { ansible_host: 10.0.10.11 }
            sw-acc-02: { ansible_host: 10.0.10.12 }
    eos:
      hosts:
        leaf-01: { ansible_host: 10.0.20.11 }
```
```yaml
# inventory/group_vars/ios.yml
ansible_network_os: cisco.ios.ios
ansible_connection: ansible.netcommon.network_cli
ansible_user: "{{ vault_net_user }}"
ansible_password: "{{ vault_net_pass }}"
ansible_become: true
ansible_become_method: enable
```
```yaml
# inventory/group_vars/all.yml
ntp_servers: [10.0.0.123, 10.0.0.124]
syslog_host: 10.0.0.50
dns_servers: [10.0.0.53, 10.0.0.54]
```
```yaml
# inventory/host_vars/sw-acc-01.yml
vlans:
  - {id: 10, name: USERS}
  - {id: 20, name: VOICE}
  - {id: 99, name: MGMT}
access_ports:
  - {name: GigabitEthernet1/0/1, vlan: 10, voice: 20, desc: "Desk-2F-01"}
```
**ลำดับความสำคัญ (ย่อ):** host_vars > group_vars ของกลุ่มลูก > group_vars ของกลุ่มแม่ > all (และ extra vars `-e` สูงสุด)
```bash
ansible-inventory --graph                  # ดูโครงสร้าง
ansible-inventory --host sw-acc-01         # ดูตัวแปรที่เครื่องนี้ได้รับ
```

---

## 4. Playbook แรก

```yaml
# playbooks/facts.yml
- name: Gather facts from IOS devices
  hosts: ios
  gather_facts: false
  tasks:
    - name: Get facts
      cisco.ios.ios_facts:
        gather_subset: [min]
    - name: Show version
      ansible.builtin.debug:
        msg: "{{ inventory_hostname }} → {{ ansible_net_version }} ({{ ansible_net_model }})"
    - name: Run show command
      cisco.ios.ios_command:
        commands: ["show ip interface brief"]
      register: out
    - ansible.builtin.debug: var=out.stdout_lines
```
```bash
ansible-playbook playbooks/facts.yml --ask-vault-pass
ansible-playbook playbooks/facts.yml --limit access          # เฉพาะกลุ่ม/เครื่อง
ansible ios -m cisco.ios.ios_command -a "commands='show clock'"   # ad-hoc
```

---

## 5. Resource Modules และ State ⭐

module ใหม่ที่จัดการ "ทรัพยากร" ของอุปกรณ์แบบมีโครงสร้าง (`ios_vlans`, `ios_interfaces`, `ios_l2_interfaces`, `ios_l3_interfaces`, `ios_ospfv2`, `ios_bgp_global`, `ios_acls`, `ios_logging_global`, `ios_ntp_global`...)

| state | ความหมาย | ความเสี่ยง |
|---|---|---|
| **merged** | เพิ่ม/แก้ตามที่ระบุ ไม่ลบอย่างอื่น | ต่ำ |
| **replaced** | แทนที่ config **ของทรัพยากรที่ระบุ** ให้ตรงตามนี้ | กลาง |
| **overridden** | ทำให้ **ทั้งหมด** ตรงตามนี้ — **ลบตัวที่ไม่ได้ระบุ** | **สูง** (เช่น ลบ VLAN อื่นทั้งหมด) |
| **deleted** | ลบที่ระบุ | สูง |
| **gathered** | อ่านค่าปัจจุบันเป็นข้อมูลโครงสร้าง | ไม่มี (อ่านอย่างเดียว) |
| **rendered** | แสดง CLI ที่จะถูกส่ง โดยไม่ต่ออุปกรณ์ | ไม่มี |
| **parsed** | แปลงไฟล์ config เป็นข้อมูลโครงสร้าง | ไม่มี |

วิธีที่ง่ายที่สุด: เก็บข้อมูลใน host_vars ให้มีรูปแบบเดียวกับที่ module ต้องการ แล้วส่งให้ module ตรง ๆ
```yaml
# host_vars/sw-acc-01.yml:  vlans_cfg: [{vlan_id: 10, name: USERS}, {vlan_id: 20, name: VOICE}]
- name: Configure VLANs and access ports
  hosts: access
  gather_facts: false
  tasks:
    - name: VLANs
      cisco.ios.ios_vlans:
        config: "{{ vlans_cfg }}"
        state: merged
    - name: Access ports
      cisco.ios.ios_l2_interfaces:
        config:
          - name: GigabitEthernet1/0/1
            mode: access
            access: { vlan: 10 }
            voice: { vlan: 20 }
        state: merged
```

---

## 6. Idempotency, Check Mode และ Diff

```bash
ansible-playbook playbooks/baseline.yml --check --diff     # dry-run + แสดงสิ่งที่จะเปลี่ยน
ansible-playbook playbooks/baseline.yml --diff --limit sw-acc-01    # ทดสอบ 1 เครื่องก่อน (canary)
ansible-playbook playbooks/baseline.yml                    # ทั้งหมด
```
ผลลัพธ์: `ok` (ตรงอยู่แล้ว ไม่แก้) · `changed` (แก้) · `failed` · `skipped`
- **รันครั้งที่สองต้องได้ changed=0** — ถ้าไม่ใช่ แสดงว่า playbook ไม่ idempotent (มักเกิดจากใช้ `ios_command` ส่งคำสั่ง config หรือรูปแบบ config ที่อุปกรณ์แปลงต่างไป)
- **ใช้ `ios_config` / `ios_command` เท่าที่จำเป็น** — resource modules ดีกว่า

### ios_config + Jinja2 (เมื่อไม่มี resource module)
```yaml
- name: Baseline config
  cisco.ios.ios_config:
    src: templates/baseline.j2
    save_when: modified               # write memory เมื่อมีการเปลี่ยน
    backup: true                      # เก็บ backup ก่อนแก้
```
```jinja
{# templates/baseline.j2 #}
hostname {{ inventory_hostname | upper }}
{% for s in ntp_servers %}
ntp server {{ s }}
{% endfor %}
logging host {{ syslog_host }}
ip name-server {{ dns_servers | join(' ') }}
banner motd ^Authorized access only. Activity is logged.^
```

---

## 7. Secrets: ansible-vault

```bash
ansible-vault create inventory/group_vars/vault.yml      # สร้างไฟล์เข้ารหัส
#   vault_net_user: netauto
#   vault_net_pass: S3cure!
ansible-vault edit inventory/group_vars/vault.yml
ansible-playbook site.yml --ask-vault-pass               # หรือ --vault-password-file (เก็บนอก repo)
```
- commit ได้เฉพาะไฟล์ที่ **เข้ารหัสแล้ว** · ใน production ใช้ credential ของ AWX/AAP หรือ lookup จาก HashiCorp Vault
- `no_log: true` บน task ที่แสดงข้อมูลลับ

---

## 8. Roles, Handlers, Tags, Conditionals

```yaml
# roles/vlans/tasks/main.yml
- name: Configure VLANs
  cisco.ios.ios_vlans: { config: "{{ vlans_cfg }}", state: merged }
  notify: save config
  tags: [vlans]
# roles/vlans/handlers/main.yml
- name: save config
  cisco.ios.ios_command: { commands: ["write memory"] }
```
```yaml
# site.yml
- hosts: access
  gather_facts: false
  roles: [baseline, vlans]
- hosts: core
  gather_facts: false
  roles: [baseline, ospf]
```
```bash
ansible-playbook site.yml --tags vlans        # เฉพาะบางส่วน
```
- `when:` (เงื่อนไข) · `loop:` · `assert:` (ตรวจผล) · `block/rescue` (จัดการ error/rollback)

### Verify หลัง change ด้วย assert
```yaml
- name: Check OSPF neighbors
  cisco.ios.ios_command: { commands: ["show ip ospf neighbor"] }
  register: ospf
- ansible.builtin.assert:
    that: "'FULL' in ospf.stdout[0]"
    fail_msg: "OSPF neighbor ไม่ FULL บน {{ inventory_hostname }}"
```

---

## 9. Pattern งานจริง

### Backup config → Git
```yaml
- hosts: ios
  gather_facts: false
  tasks:
    - cisco.ios.ios_config:
        backup: true
        backup_options:
          dir_path: "./backups/{{ lookup('pipe','date +%F') }}"
          filename: "{{ inventory_hostname }}.cfg"
- hosts: localhost
  gather_facts: false
  tasks:
    - ansible.builtin.shell: |
        cd backups && git add -A && git commit -m "backup {{ lookup('pipe','date +%F') }}" || true
```
### Compliance check (ไม่แก้ แค่รายงาน)
```yaml
- cisco.ios.ios_command: { commands: ["show running-config | include ntp server|logging host|aaa new-model"] }
  register: run
- ansible.builtin.set_fact:
    compliant: "{{ ('aaa new-model' in run.stdout[0]) and (syslog_host in run.stdout[0]) }}"
```

---

## 10. AWX / Ansible Automation Platform

- **Web UI + REST API** สำหรับ Ansible: จัดเก็บ inventory (sync จาก NetBox — Level 89), **credential ที่เข้ารหัส** (ผู้ใช้ไม่เห็นรหัสผ่าน), **RBAC** (helpdesk รันได้เฉพาะ job ที่อนุญาต), **schedule**, log ทุกการรัน (audit)
- **Job template + Survey:** ฟอร์มให้ helpdesk กรอก "switch / port / VLAN" แล้วรัน playbook ที่ผ่าน review แล้ว → **self-service ที่ควบคุมได้**
- **Workflow:** backup → change → verify → แจ้ง Teams/Slack
- รุ่นเชิงพาณิชย์: Red Hat AAP (+ Event-Driven Ansible ทำงานตาม event เช่น alert)

---

## 11. Ansible vs Python vs Terraform

| | Ansible | Python (Nornir) | Terraform |
|---|---|---|---|
| รูปแบบ | YAML playbook | โค้ด | HCL declarative + state |
| เหมาะกับ | config อุปกรณ์/OS, งานเป็นขั้นตอน, ทีมที่ไม่ถนัดโค้ด | logic ซับซ้อน, data processing, เครื่องมือเฉพาะ | provisioning ทรัพยากร (cloud, firewall object) — Level 85 |
| ข้อจำกัด | logic ซับซ้อนเขียนยาก, ช้ากว่า | ต้องเขียนโค้ด | ไม่เหมาะกับ config CLI รายเครื่อง |

→ ในงานจริงใช้ **ร่วมกัน**

---

## 12. Troubleshooting

| ปัญหา | แก้ |
|---|---|
| `unable to open shell` / connection timeout | ตรวจ ansible_host, SSH, `ansible_network_os` ถูกไหม, `-vvvv` ดูรายละเอียด, log: `ANSIBLE_LOG_PATH`, `ansible_persistent_log_messages` |
| Authentication failed | vault ตัวแปร, enable password (`ansible_become`) |
| command timeout | เพิ่ม `ansible_command_timeout` (คำสั่งที่ช้าเช่น show tech) |
| changed ทุกครั้ง | ไม่ idempotent — ใช้ resource module, ตรวจรูปแบบ config ที่อุปกรณ์แสดง |
| ตัวแปรไม่ได้ค่าที่คาด | `ansible-inventory --host`, ลำดับความสำคัญของตัวแปร |

---

## 13. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Ansible ต้องติดตั้ง agent บน switch | agentless — module รันบน control node |
| ใช้ `ios_command` ส่ง config ก็พอ | ไม่ idempotent ไม่มี diff — ใช้ resource modules/ios_config |
| `overridden` ปลอดภัยเหมือน `merged` | overridden ลบสิ่งที่ไม่ได้ระบุ |
| --check รับประกันว่าใช้จริงจะสำเร็จ | network module บางตัวรองรับ check mode จำกัด — ทดสอบ lab/canary ด้วย |
| เก็บรหัสผ่านใน group_vars แบบ plain text ได้ | ใช้ ansible-vault/credential ของ AWX |

---

## 14. Cheat Sheet

```
Agentless · network_cli / netconf / httpapi · ansible_network_os
inventory (groups) + group_vars + host_vars · ansible-inventory --graph/--host
playbook → tasks → module · register · debug · assert · when · loop · block/rescue
Resource modules: merged · replaced · overridden (ลบอื่น!) · deleted · gathered · rendered · parsed
ios_config src=template.j2 backup=true save_when=modified
--check --diff · --limit · --tags · -vvvv · รันซ้ำต้อง changed=0
ansible-vault create/edit · no_log
roles + handlers · AWX/AAP: RBAC, credentials, survey, schedule, workflow
```

---

## 15. แบบทดสอบ 10 ข้อ

1. Ansible ทำงานกับอุปกรณ์ network ต่างจาก server อย่างไร
2. ตั้งตัวแปรอะไรเพื่อให้ Ansible คุยกับ Cisco IOS ผ่าน SSH
3. group_vars กับ host_vars ใช้ต่างกันอย่างไร
4. state merged, replaced, overridden ต่างกันอย่างไร
5. Idempotent คืออะไร ตรวจอย่างไร
6. ทำไมไม่ควรใช้ `ios_command` สำหรับ config
7. `--check --diff` และ `--limit` ใช้ทำอะไร
8. เก็บรหัสผ่านอุปกรณ์อย่างไรในโปรเจค Ansible
9. ใช้ assert ทำอะไรหลัง change
10. AWX ช่วยให้ helpdesk เปลี่ยน VLAN ได้อย่างปลอดภัยอย่างไร

<details><summary><b>เฉลย</b></summary>

1. Module รันบน control node แล้วคุยกับอุปกรณ์ผ่าน connection plugin (network_cli/netconf/httpapi) ไม่ได้ copy โค้ดไปรันบนอุปกรณ์
2. `ansible_connection: ansible.netcommon.network_cli`, `ansible_network_os: cisco.ios.ios`, user/password (และ become: enable)
3. group_vars เป็นค่าร่วมของกลุ่ม (เช่น NTP ของทุกเครื่อง); host_vars เป็นค่าเฉพาะเครื่อง (VLAN/พอร์ตของเครื่องนั้น)
4. merged เพิ่ม/แก้โดยไม่ลบ; replaced แทนที่ config ของทรัพยากรที่ระบุ; overridden ทำให้ทั้งหมดตรงตามที่ระบุและลบส่วนที่ไม่ได้ระบุ
5. รันซ้ำแล้วผลเหมือนเดิม ไม่เปลี่ยนสิ่งที่ตรงอยู่แล้ว — รันครั้งที่สองต้องได้ changed=0
6. ไม่ idempotent ไม่มี diff/check mode ที่มีความหมาย และไม่รู้สถานะปัจจุบัน
7. --check --diff = dry-run แสดงการเปลี่ยนแปลง; --limit = จำกัดเครื่อง/กลุ่ม (เช่นทดสอบ canary)
8. ansible-vault เข้ารหัสไฟล์ตัวแปร หรือ credential ของ AWX/secret manager — ไม่เก็บแบบ plain text
9. ตรวจสถานะหลัง change (เช่น OSPF neighbor FULL, interface up) และทำให้ job ล้มเหลวพร้อมข้อความหากไม่ผ่าน
10. Job template ที่ผ่าน review + survey form จำกัดสิ่งที่กรอก, RBAC ให้รันเฉพาะ job ที่อนุญาต, ผู้ใช้ไม่เห็น credential และมี log การรันทุกครั้ง
</details>

---

➡️ ต่อไป: **Level 83 — APIs: REST, NETCONF, RESTCONF, YANG, gNMI**
