/*
 * Lab Aruba: ตัวจำลอง CLI ของ switch AOS-CX (ทำงานในเบราว์เซอร์ทั้งหมด)
 * - parser รองรับคำย่อ, ? (help), Tab (เติมคำ), ↑/↓ (history), Ctrl+Z (end), paste หลายบรรทัด
 * - เก็บสถานะ config: hostname, VLAN, port, LAG, SVI, STP, static route, OSPF, user/SSH/NTP/SNMP/logging
 * - จำลองอุปกรณ์ปลายทางตาม peers / hosts ในบทเรียน: LACP, STP root, OSPF neighbor, ping / traceroute
 * - ข้อมูลเครื่อง (firmware, uptime, CPU, fan, PSU, อุณหภูมิ, event, VSF, checkpoint) มาจาก device ในไฟล์บทเรียน
 * - ตรวจโจทย์ตาม checks ในไฟล์บทเรียน JSON (config / คำสั่งที่รัน / คำตอบที่อ่านจากผล show)
 * ข้อความผลลัพธ์เป็นการเลียนรูปแบบเพื่อการฝึก ไม่ใช่ผลจากเครื่องจริง
 */
(function () {
    'use strict';
    var L = window.LAB_LESSON;
    if (!L) return;
    var KEY = 'arubaLab:' + L.slug;
    var DEV = L.device || {};
    var PEER = L.peers || {};
    var VER = DEV.firmware || 'FL.10.13.1000';
    var NPORT = DEV.ports || 28;
    var SFP = DEV.sfpFrom || 25;
    var SPLIT = SFP > 1 ? SFP : NPORT - 3;          // จุดแบ่งกลุ่ม port บนหน้าเครื่อง
    var CONN = L.connected || {};
    var LLDP = L.lldp || {};
    var MACS = L.macs || {};
    var HOSTS = (L.hosts || []).slice();
    if (PEER.ospf) HOSTS.push({ ip: PEER.ospf.ip, port: PEER.ospf.port, mac: PEER.ospf.mac || '38:21:c7:11:22:00' });
    var MYMAC = DEV.mac || '38:21:c7:5d:a0:00';

    // ---------- helpers ----------
    function pad(s, n) { s = String(s); return s.length >= n ? s + ' ' : s + new Array(n - s.length + 1).join(' '); }
    function rpad(s, n) { s = String(s); return s.length >= n ? s : new Array(n - s.length + 1).join(' ') + s; }
    function dash(n) { return new Array(n + 1).join('-'); }
    function range(a, b) { var r = []; for (var i = a; i <= b; i++) r.push(i); return r; }
    function uniqSort(a) { return a.filter(function (x, i) { return a.indexOf(x) === i; }).sort(function (x, y) { return x - y; }); }
    function hex2(n) { return ('0' + (n & 255).toString(16)).slice(-2); }
    function pn(n) { return '1/1/' + n; }
    function arr(x, d) { return x === undefined ? [d] : [].concat(x); }
    function compress(nums, fmt) {
        nums = uniqSort(nums); var out = [], i = 0;
        while (i < nums.length) {
            var j = i; while (j + 1 < nums.length && nums[j + 1] === nums[j] + 1) j++;
            out.push(j > i ? fmt(nums[i]) + '-' + fmt(nums[j]) : fmt(nums[i]));
            i = j + 1;
        }
        return out.join(',');
    }
    function cPorts(a) { return compress(a, pn); }
    function cVlans(a) { return compress(a, String); }

    function parseIf(tok) {
        var m, out = [];
        if (tok.indexOf(',') >= 0) {
            var parts = tok.split(',');
            for (var k = 0; k < parts.length; k++) { var r = parseIf(parts[k]); if (!r) return null; out = out.concat(r); }
            return uniqSort(out);
        }
        if ((m = /^1\/1\/(\d+)$/.exec(tok))) { var n = +m[1]; return n >= 1 && n <= NPORT ? [n] : null; }
        if ((m = /^1\/1\/(\d+)-(?:1\/1\/)?(\d+)$/.exec(tok))) {
            var a = +m[1], b = +m[2];
            return a >= 1 && b <= NPORT && a <= b ? range(a, b) : null;
        }
        return null;
    }
    function parseVlans(tok) {
        if (!/^[\d,\-]+$/.test(tok)) return null;
        var out = [], parts = tok.split(',');
        for (var k = 0; k < parts.length; k++) {
            var m = /^(\d+)(?:-(\d+))?$/.exec(parts[k]); if (!m) return null;
            var a = +m[1], b = m[2] ? +m[2] : a;
            if (a < 1 || b > 4094 || a > b) return null;
            out = out.concat(range(a, b));
        }
        return uniqSort(out);
    }
    function ipInt(ip) { var p = ip.split('.').map(Number); return ((p[0] << 24) >>> 0) + (p[1] << 16) + (p[2] << 8) + p[3]; }
    function validIp(t) {
        var m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(t);
        if (!m) return false;
        for (var i = 1; i <= 4; i++) if (+m[i] > 255) return false;
        return true;
    }
    function validIpMask(t) { var m = /^([\d.]+)\/(\d{1,2})$/.exec(t); return !!m && validIp(m[1]) && +m[2] <= 32; }
    function maskOf(len) { return len === 0 ? 0 : (0xFFFFFFFF << (32 - len)) >>> 0; }
    function inNet(ip, cidr) { var m = cidr.split('/'), len = +m[1], mk = maskOf(len); return ((ipInt(ip) & mk) >>> 0) === ((ipInt(m[0]) & mk) >>> 0); }
    function netOf(cidr) {
        var m = cidr.split('/'), len = +m[1], v = (ipInt(m[0]) & maskOf(len)) >>> 0;
        return [v >>> 24, (v >> 16) & 255, (v >> 8) & 255, v & 255].join('.') + '/' + len;
    }
    function normArea(a) { return /^\d+$/.test(a) ? [(a >>> 24) & 255, (a >>> 16) & 255, (a >>> 8) & 255, a & 255].join('.') : a; }

    var PARAM = {
        '<VLAN-ID>': function (t) { return /^\d+$/.test(t) && +t >= 1 && +t <= 4094; },
        '<VLAN-LIST>': function (t) { return !!parseVlans(t); },
        '<IFNAME>': function (t) { return !!parseIf(t); },
        '<LAG-ID>': function (t) { return /^\d+$/.test(t) && +t >= 1 && +t <= 256; },
        '<PID>': function (t) { return /^\d+$/.test(t) && +t >= 1 && +t <= 63; },
        '<PRIO>': function (t) { return /^\d+$/.test(t) && +t >= 0 && +t <= 15; },
        '<AREA>': function (t) { return (/^\d+$/.test(t) && +t <= 4294967295) || validIp(t); },
        '<WORD>': function (t) { return t.length > 0; },
        '<IP>': validIp,
        '<IP/MASK>': validIpMask,
        '<LINE>': function () { return true; }
    };
    function isParam(w) { return w.charAt(0) === '<'; }

    var HELP = {
        configure: 'Enter the configuration context', terminal: 'Configure from the terminal',
        show: 'Show running system information', 'running-config': 'Current running configuration',
        'startup-config': 'Startup configuration', vlan: 'VLAN configuration', interface: 'Interface configuration / information',
        brief: 'Show brief information in tabular format', ip: 'IP configuration / information', version: 'Show version information',
        write: 'Write running configuration to memory', memory: 'Write running configuration to startup configuration',
        copy: 'Copy configuration', history: 'Show command history', exit: 'Exit current context',
        end: 'Return to the manager context', hostname: 'Configure the device hostname', no: 'Negate a command or set its defaults',
        name: 'Configure the VLAN name', description: 'Set a description', shutdown: 'Disable the interface / VLAN',
        access: 'Access VLAN configuration', trunk: 'Trunk VLAN configuration', native: 'Native VLAN of the trunk',
        allowed: 'Allowed VLANs on the trunk', all: 'All VLANs', routing: 'Enable L3 routing on the interface',
        address: 'Configure an IPv4 address', page: 'Disable output paging',
        system: 'System information (hostname, firmware, uptime, CPU, memory)', 'resource-utilization': 'CPU / memory utilization',
        environment: 'Environmental information', fan: 'Fan information', 'power-supply': 'Power supply information',
        temperature: 'Temperature sensor information', 'spanning-tree': 'Spanning tree configuration / information',
        vsf: 'VSF (stack) information', events: 'Event logs', logging: 'Event logs / remote syslog server', '-r': 'Show newest entries first',
        checkpoint: 'Configuration checkpoints', lldp: 'LLDP information', 'neighbor-info': 'LLDP neighbor information',
        'mac-address-table': 'MAC address table', uptime: 'System uptime', clock: 'System date and time / time zone',
        lag: 'Link aggregation group', lacp: 'LACP configuration / information', mode: 'Mode', active: 'LACP active mode',
        passive: 'LACP passive mode', interfaces: 'Per-interface information', aggregates: 'Per-aggregate information',
        priority: 'Bridge priority (multiplier of 4096)', mstp: 'Multiple Spanning Tree', rpvst: 'Rapid per-VLAN Spanning Tree',
        'port-type': 'Port type', 'admin-edge': 'Edge port (connects to an end device)', 'bpdu-guard': 'Disable the port when a BPDU is received',
        route: 'Routing table / static route', router: 'Routing protocol configuration', ospf: 'OSPF configuration / information',
        'router-id': 'OSPF router ID', area: 'OSPF area', neighbors: 'OSPF neighbors', arp: 'ARP table',
        ping: 'Send ICMP echo requests', traceroute: 'Trace the route to a host',
        user: 'Local user account', group: 'User group', administrators: 'Full read-write access', operators: 'Read-only access',
        auditors: 'Audit (log) access only', password: 'User password', plaintext: 'Password in plain text',
        ssh: 'SSH server', server: 'Server configuration', vrf: 'VRF', default: 'Default VRF (data ports)', mgmt: 'Management VRF (OOBM port)',
        ntp: 'Network Time Protocol', enable: 'Enable', iburst: 'Send a burst of packets on startup', status: 'Status information',
        associations: 'NTP server associations', 'snmp-server': 'SNMP agent configuration', snmp: 'SNMP information',
        community: 'SNMPv1/v2c community', timezone: 'System time zone', 'user-list': 'Local users',
        '<VLAN-ID>': '<1-4094>|VLAN identifier', '<VLAN-LIST>': '<VLAN-LIST>|VLAN list, e.g. 10 or 10,20 or 30-40',
        '<IFNAME>': '<IFNAME>|Interface name, e.g. 1/1/1 or 1/1/1-1/1/4', '<WORD>': '<WORD>|Text string',
        '<LAG-ID>': '<1-256>|LAG number', '<PID>': '<1-63>|OSPF process ID', '<PRIO>': '<0-15>|Priority multiplier (x 4096)',
        '<AREA>': '<A.B.C.D|0-4294967295>|OSPF area ID', '<IP>': 'A.B.C.D|IPv4 address',
        '<LINE>': '<LINE>|Text up to the end of the line', '<IP/MASK>': 'A.B.C.D/M|IPv4 address with prefix length'
    };
    // ความหมายภาษาไทยของแต่ละคำสั่ง (ให้ Kafra อธิบาย) · key = "โหมด|คำสั่ง" หรือ "คำสั่ง" · {n} = คำที่ n ที่ผู้ใช้พิมพ์
    var MEAN = {
        'show running-config': 'แสดง config ที่ใช้งานอยู่ตอนนี้ (running-config) ทั้งหมด ใช้ตรวจว่าตั้งค่าครบไหม และเก็บเป็นไฟล์แนบรายงาน',
        'show running-config interface <IFNAME>': 'แสดง config เฉพาะ interface {3}',
        'show startup-config': 'แสดง config ที่บันทึกไว้ ซึ่งเครื่องจะโหลดตอนเปิดเครื่องครั้งถัดไป',
        'show vlan': 'แสดงรายการ VLAN ทั้งหมด สถานะ และ port ที่อยู่ในแต่ละ VLAN',
        'show vlan <VLAN-ID>': 'แสดงข้อมูลเฉพาะ VLAN {2}',
        'show interface brief': 'ตารางสรุปทุก port: VLAN, โหมด, เปิด/ปิด, up/down, ความเร็ว และ description เป็นคำสั่งแรกที่ควรดูเวลาไล่ปัญหา',
        'show interface <IFNAME>': 'รายละเอียดของ port {2}: สถานะ, ความเร็ว, VLAN และ Utilization',
        'show ip interface brief': 'สรุป interface ที่มี IP Address พร้อมสถานะ link/admin',
        'show ip route': 'ตาราง routing ว่าเครือข่ายปลายทางไปทางไหน (C = ต่อตรง, L = IP ของเครื่องเอง, S = static, O = OSPF)',
        'show ip ospf neighbors': 'ดูเพื่อนบ้าน OSPF ต้องขึ้น FULL ถึงจะแลก route กันได้',
        'show arp': 'ตาราง ARP จับคู่ IP Address กับ MAC ของเครื่องในวงที่ต่อตรง',
        'show lacp interfaces': 'สถานะ LACP ของแต่ละ port ใน LAG ทั้งฝั่งเรา (Actor) และอีกฝั่ง (Partner)',
        'show lacp aggregates': 'สรุปแต่ละ LAG ว่ามี port อะไรบ้างและใช้โหมด LACP แบบไหน',
        'show version': 'ดูเวอร์ชัน firmware และรุ่นเครื่อง',
        'show system': 'ข้อมูลระบบ: ชื่อเครื่อง, firmware, serial, Up Time, CPU และ Memory ใช้เก็บค่า PM ได้ในคำสั่งเดียว',
        'show system resource-utilization': 'ดูการใช้ CPU และ Memory ของแต่ละ member',
        'show uptime': 'ดูว่าเครื่องเปิดมานานเท่าไหร่แล้ว',
        'show clock': 'ดูวันและเวลาของเครื่อง',
        'show environment fan': 'สถานะพัดลมทุกตัว (ok = ปกติ)',
        'show environment power-supply': 'สถานะ Power Supply ทุกตัว (OK = ปกติ)',
        'show environment temperature': 'อุณหภูมิของ sensor แต่ละจุดในเครื่อง',
        'show spanning-tree': 'สถานะ Spanning Tree: ใครเป็น root bridge และ port ไหนเป็น Root/Designated',
        'show vsf': 'สถานะ stack (VSF): สมาชิกครบไหม ใครเป็น Master และ stack แยกกัน (split) หรือเปล่า',
        'show events': 'Event log ของเครื่อง เรียงจากเก่าไปใหม่',
        'show events -r': 'Event log เรียงล่าสุดก่อน ใช้หาว่าเกิดอะไรขึ้นเมื่อไหร่และใครทำ',
        'show logging': 'Event log ของเครื่อง เรียงจากเก่าไปใหม่',
        'show logging -r': 'Event log เรียงล่าสุดก่อน',
        'show checkpoint': 'รายการ checkpoint (snapshot ของ config) ที่เครื่องเก็บไว้ ใช้ดูวันที่ backup ล่าสุด',
        'show lldp neighbor-info': 'ดูว่าแต่ละ port ต่อกับอุปกรณ์ชื่ออะไร ที่ port ไหน (อุปกรณ์บอกกันเองผ่าน LLDP)',
        'show mac-address-table': 'ตาราง MAC ว่าเครื่องไหน (MAC) อยู่ VLAN ไหน และต่อ port ไหน',
        'show ntp status': 'ดูว่า NTP เปิดอยู่ไหม และ sync เวลากับ server ได้หรือยัง',
        'show ntp associations': 'รายการ NTP server และสถานะการติดต่อ',
        'show ssh server': 'ดูว่าเปิด SSH ไว้บน VRF ไหนบ้าง',
        'show snmp community': 'ดู SNMP community ที่ตั้งไว้',
        'show user-list': 'รายชื่อผู้ใช้ในเครื่องพร้อมกลุ่มสิทธิ์',
        'show history': 'ดูคำสั่งที่พิมพ์ไปล่าสุด',
        'ping <IP>': 'ส่ง ICMP ไปทดสอบว่าติดต่อ {1} ได้ไหม ถ้ามีตอบกลับแปลว่าเส้นทางไปและกลับใช้ได้',
        'traceroute <IP>': 'ดูเส้นทางไป {1} ทีละ hop ว่าผ่าน router ตัวไหนและไปหยุดที่ไหน',
        'end': 'ออกจากทุกโหมดกลับไปที่ prompt หลัก (switch#)',
        'exit': 'ออกจากโหมดปัจจุบันขึ้นไปหนึ่งชั้น',
        'configure terminal': 'เข้าโหมดตั้งค่า (config) ทุกคำสั่งที่แก้ config ต้องพิมพ์ในโหมดนี้',
        'configure': 'เข้าโหมดตั้งค่า (config) ทุกคำสั่งที่แก้ config ต้องพิมพ์ในโหมดนี้',
        'write memory': 'บันทึก running-config ลง startup-config ถ้าไม่บันทึก พอ reboot แล้ว config ที่แก้จะหายหมด',
        'copy running-config startup-config': 'บันทึก running-config ลง startup-config (ผลเหมือน write memory)',
        'no page': 'ปิดการแบ่งหน้า ผลยาวๆ จะแสดงต่อกันจนจบ สะดวกตอนเก็บผลลงรายงาน',
        'page': 'เปิดการแบ่งหน้าผลลัพธ์',
        'hostname <WORD>': 'ตั้งชื่อเครื่องเป็น {1} ชื่อจะขึ้นที่ prompt ทำให้รู้ว่ากำลังทำงานกับเครื่องไหน',
        'no hostname': 'คืนชื่อเครื่องเป็นค่าเริ่มต้น',
        'vlan <VLAN-LIST>': 'สร้าง VLAN {1} (หรือเข้าไปแก้ถ้ามีแล้ว) แล้วเข้าโหมด config-vlan',
        'no vlan <VLAN-LIST>': 'ลบ VLAN {2}',
        'interface vlan <VLAN-ID>': 'สร้างหรือเข้า interface vlan {2} (SVI) ซึ่งเป็น interface Layer 3 ของ VLAN ใช้เป็น gateway',
        'no interface vlan <VLAN-ID>': 'ลบ interface vlan {3}',
        'interface lag <LAG-ID>': 'สร้างหรือเข้า interface lag {2} คือ port เสมือนที่รวมหลายสายเป็นเส้นเดียว',
        'no interface lag <LAG-ID>': 'ลบ lag {3}',
        'interface <IFNAME>': 'เข้าไปตั้งค่า port {1} (ใส่ช่วงอย่าง 1/1/1-1/1/4 เพื่อทำหลาย port พร้อมกันได้)',
        'spanning-tree': 'เปิด Spanning Tree เพื่อกัน loop',
        'spanning-tree mode mstp': 'ใช้ STP แบบ MSTP (ค่าตั้งต้นของ AOS-CX)',
        'spanning-tree mode rpvst': 'ใช้ STP แบบ Rapid PVST (แยกต้นไม้ต่อ VLAN)',
        'spanning-tree priority <PRIO>': 'ตั้ง bridge priority = {2} × 4096 ยิ่งต่ำยิ่งมีโอกาสได้เป็น root bridge',
        'no spanning-tree priority': 'คืน bridge priority เป็นค่าตั้งต้น 32768',
        'user <WORD> group administrators password plaintext <WORD>': 'สร้างผู้ใช้ {1} กลุ่ม administrators ซึ่งแก้ config ได้ทุกอย่าง',
        'user <WORD> group operators password plaintext <WORD>': 'สร้างผู้ใช้ {1} กลุ่ม operators ซึ่งรัน show ได้แต่แก้ config ไม่ได้',
        'user <WORD> group auditors password plaintext <WORD>': 'สร้างผู้ใช้ {1} กลุ่ม auditors ซึ่งดู log ได้อย่างเดียว',
        'no user <WORD>': 'ลบผู้ใช้ {2}',
        'ssh server vrf default': 'เปิด SSH ให้เข้าผ่าน port ข้อมูล (VRF default) เช่น IP บน VLAN',
        'ssh server vrf mgmt': 'เปิด SSH ที่ port OOBM (VRF mgmt)',
        'no ssh server vrf default': 'ปิด SSH บน VRF default',
        'no ssh server vrf mgmt': 'ปิด SSH บน VRF mgmt',
        'ntp server <IP>': 'กำหนด NTP server {2} สำหรับเทียบเวลา',
        'ntp server <IP> iburst': 'กำหนด NTP server {2} (iburst = ส่งถี่ๆ ตอนเริ่ม ทำให้ sync ได้เร็ว)',
        'no ntp server <IP>': 'ลบ NTP server {3}',
        'ntp enable': 'เปิดการทำงานของ NTP ถ้าไม่สั่ง เครื่องจะไม่ sync เวลาแม้ตั้ง server แล้ว',
        'no ntp enable': 'ปิด NTP',
        'clock timezone <WORD>': 'ตั้งเขตเวลาของเครื่องเป็น {2}',
        'no clock timezone': 'คืนเขตเวลาเป็น UTC',
        'snmp-server community <WORD>': 'ตั้ง SNMP community "{2}" (เหมือนรหัสผ่านที่ระบบ monitor ใช้ดึงค่าแบบ SNMPv2c)',
        'no snmp-server community <WORD>': 'ลบ SNMP community {3}',
        'snmp-server vrf default': 'เปิด SNMP agent บน VRF default ให้ระบบ monitor ดึงค่าผ่าน port ข้อมูลได้',
        'snmp-server vrf mgmt': 'เปิด SNMP agent บน VRF mgmt (port OOBM)',
        'logging <IP>': 'ส่ง log ไปเก็บที่ syslog server {1}',
        'no logging <IP>': 'เลิกส่ง log ไป {2}',
        'ip route <IP/MASK> <IP>': 'สร้าง static route: ข้อมูลที่จะไปเครือข่าย {2} ให้ส่งต่อไปที่ next-hop {3}',
        'no ip route <IP/MASK> <IP>': 'ลบ static route ไป {3}',
        'router ospf <PID>': 'เปิด OSPF process {2} แล้วเข้าโหมดตั้งค่า OSPF',
        'no router ospf <PID>': 'ลบ OSPF process {3}',
        'vlan|name <WORD>': 'ตั้งชื่อ VLAN เป็น {1} ให้อ่าน config แล้วรู้ว่า VLAN นี้ใช้ทำอะไร',
        'vlan|no name': 'คืนชื่อ VLAN เป็นค่าตั้งต้น',
        'vlan|description <LINE>': 'ใส่คำอธิบายให้ VLAN',
        'vlan|no description': 'ลบคำอธิบายของ VLAN',
        'vlan|shutdown': 'ปิด VLAN นี้',
        'vlan|no shutdown': 'เปิด VLAN นี้',
        'if|shutdown': 'ปิด port (admin down) เช่น port ที่ไม่ใช้ เพื่อกันคนแอบเสียบสาย',
        'if|no shutdown': 'เปิด port ให้ทำงาน',
        'if|description <LINE>': 'ใส่คำอธิบายว่า port นี้ต่ออะไร ช่วยมากตอนทำ MA และไล่ปัญหา',
        'if|no description': 'ลบคำอธิบายของ port',
        'if|vlan access <VLAN-ID>': 'ให้ port เป็น access ของ VLAN {2} เครื่องที่ต่อจะอยู่ VLAN นี้ (ส่งแบบไม่มี tag)',
        'if|no vlan access': 'คืน access VLAN เป็น 1',
        'if|vlan trunk native <VLAN-ID>': 'ให้ port เป็น trunk และกำหนด native VLAN {3} ซึ่งเป็น VLAN ที่ส่งแบบไม่มี tag',
        'if|no vlan trunk native': 'คืน native VLAN เป็น 1',
        'if|vlan trunk allowed all': 'ให้ trunk ส่งได้ทุก VLAN',
        'if|vlan trunk allowed <VLAN-LIST>': 'อนุญาตให้ VLAN {3} วิ่งผ่าน trunk นี้ (เพิ่มต่อจากที่มีอยู่)',
        'if|no vlan trunk allowed <VLAN-LIST>': 'เอา VLAN {4} ออกจาก trunk',
        'if|no vlan trunk allowed': 'เอาทุก VLAN ออกจาก trunk',
        'if|routing': 'เปลี่ยน port เป็น Layer 3 (routed port) จึงจะใส่ IP Address ได้',
        'if|no routing': 'เปลี่ยนกลับเป็น port Layer 2',
        'if|ip address <IP/MASK>': 'ตั้ง IP Address {2} ให้ interface นี้',
        'if|no ip address': 'ลบ IP Address',
        'if|ip ospf <PID> area <AREA>': 'เปิด OSPF process {2} บน interface นี้ใน area {4} (area ต้องตรงกับอีกฝั่ง)',
        'if|no ip ospf <PID> area <AREA>': 'ปิด OSPF บน interface นี้',
        'if|lag <LAG-ID>': 'ใส่ port นี้เป็นสมาชิกของ lag {1} (port จะใช้ config ของ lag แทน)',
        'if|no lag <LAG-ID>': 'เอา port ออกจาก lag',
        'if|spanning-tree port-type admin-edge': 'บอกว่า port นี้ต่อเครื่องปลายทาง ให้ส่งข้อมูลได้ทันทีโดยไม่ต้องรอ STP',
        'if|no spanning-tree port-type': 'ยกเลิก admin-edge',
        'if|spanning-tree bpdu-guard': 'ถ้ามี BPDU เข้ามา (มีคนเอา switch มาต่อ) ให้ปิด port ทันทีเพื่อกัน loop',
        'if|no spanning-tree bpdu-guard': 'ปิด BPDU guard',
        'lag|lacp mode active': 'ให้ lag ส่ง LACP ไปเจรจากับอีกฝั่งเอง',
        'lag|lacp mode passive': 'ให้ lag รออีกฝั่งส่ง LACP มาก่อน (passive ทั้งสองฝั่งจะไม่เกิด LAG)',
        'lag|no lacp mode': 'เป็น LAG แบบ static ที่ไม่ใช้ LACP',
        'svi|ip address <IP/MASK>': 'ตั้ง IP {2} ให้ SVI เพื่อเป็น gateway ของเครื่องใน VLAN นี้',
        'svi|no ip address': 'ลบ IP ของ SVI',
        'svi|description <LINE>': 'ใส่คำอธิบายให้ interface vlan',
        'svi|no description': 'ลบคำอธิบาย',
        'svi|shutdown': 'ปิด interface vlan ทำให้ gateway ของ VLAN นี้ใช้ไม่ได้',
        'svi|no shutdown': 'เปิด interface vlan ให้ทำงาน',
        'svi|ip ospf <PID> area <AREA>': 'ประกาศวงของ VLAN นี้เข้า OSPF process {2} area {4}',
        'svi|no ip ospf <PID> area <AREA>': 'เอา VLAN นี้ออกจาก OSPF',
        'ospf|router-id <IP>': 'ตั้ง router-id {1} เป็นชื่อประจำตัวของเครื่องใน OSPF (ห้ามซ้ำกับเครื่องอื่น)',
        'ospf|no router-id': 'ลบ router-id ที่ตั้งไว้',
        'ospf|area <AREA>': 'ประกาศ area {1} ใน OSPF process (area 0 คือ backbone)',
        'ospf|no area <AREA>': 'ลบ area {2}'
    };
    var MODE_LABEL = { exec: 'switch#', config: '(config)#', vlan: '(config-vlan)#', 'if': '(config-if)#', lag: '(config-lag-if)#', svi: '(config-if-vlan)#', ospf: '(config-ospf)#' };
    function meaningOf(def, m, args) {
        var k = def.w.join(' ');
        var t = MEAN[m + '|' + k] || (m === 'lag' && MEAN['if|' + k]) || MEAN[k] || '';
        return t.replace(/\{(\d+)\}/g, function (_, i) { return args[+i] || ''; });
    }
    function helpLabel(w) { var h = HELP[w] || ''; return isParam(w) ? h.split('|')[0] : w; }
    function helpText(w) { var h = HELP[w] || ''; return isParam(w) ? (h.split('|')[1] || '') : h; }

    // ---------- state ----------
    function newIf() { return { admin: true, desc: '', routing: false, mode: 'access', access: 1, native: 1, allowed: 'all', ip: '', lag: 0, edge: false, bpdu: false, ospf: null }; }
    function newLag() { var o = newIf(); o.admin = false; o.lacp = ''; return o; }
    function fix(s) {
        s.events = s.events || []; s.ran = s.ran || []; s.lags = s.lags || {}; s.routes = s.routes || [];
        s.ospf = s.ospf || null;
        s.stp = s.stp || { mode: 'mstp', prio: DEV.stp && DEV.stp.priority !== undefined ? DEV.stp.priority / 4096 : 8 };
        s.sys = s.sys || { users: {}, ssh: ['mgmt'], ntp: [], ntpOn: false, snmp: [], snmpVrf: [], logging: [], tz: '' };
        for (var n = 1; n <= NPORT; n++) { var d = newIf(); for (var k in d) if (s.ports[n][k] === undefined) s.ports[n][k] = d[k]; }
        return s;
    }
    function freshState() {
        var ports = {};
        for (var n = 1; n <= NPORT; n++) ports[n] = newIf();
        var s = fix({ hostname: DEV.hostname || 'switch', vlans: { 1: { name: 'DEFAULT_VLAN_1', desc: '', admin: true } }, ports: ports, svis: {} });
        var I = L.initial;
        if (!I) return s;
        if (I.hostname) s.hostname = I.hostname;
        Object.keys(I.vlans || {}).forEach(function (v) {
            var x = I.vlans[v] || {};
            s.vlans[v] = { name: x.name || (+v === 1 ? 'DEFAULT_VLAN_1' : 'VLAN' + v), desc: x.desc || '', admin: x.admin !== false };
        });
        function apply(o, x) {
            if (x.desc !== undefined) o.desc = x.desc;
            if (x.admin !== undefined) o.admin = x.admin;
            if (x.access !== undefined) { o.mode = 'access'; o.access = x.access; }
            if (x.mode === 'trunk') { o.mode = 'trunk'; o.native = x.native || 1; o.allowed = x.allowed || 'all'; }
            if (x.routing) { o.routing = true; o.ip = x.ip || ''; }
            if (x.ospf) o.ospf = x.ospf;
            if (x.edge) o.edge = true;
            if (x.bpdu) o.bpdu = true;
            if (x.lacp) o.lacp = x.lacp;
        }
        Object.keys(I.lags || {}).forEach(function (id) {
            var x = I.lags[id]; s.lags[id] = newLag(); apply(s.lags[id], x);
            (parseIf(x.members || '') || []).forEach(function (n) { s.ports[n].lag = +id; });
        });
        Object.keys(I.ports || {}).forEach(function (k) { (parseIf(k) || []).forEach(function (n) { apply(s.ports[n], I.ports[k]); }); });
        Object.keys(I.svis || {}).forEach(function (v) {
            var x = I.svis[v]; if (typeof x === 'string') x = { ip: x };
            s.svis[v] = { ip: x.ip || '', admin: x.admin !== false, desc: x.desc || '', ospf: x.ospf || null };
        });
        if (I.ospf) s.ospf = { pid: I.ospf.pid || 1, rid: I.ospf.rid || '', areas: (I.ospf.areas || []).map(normArea) };
        if (I.routes) s.routes = I.routes.slice();
        if (I.stpPriority !== undefined) s.stp.prio = I.stpPriority;
        if (I.sys) Object.keys(I.sys).forEach(function (k) { s.sys[k] = I.sys[k]; });
        return s;
    }
    var S, startup, hist = [], done = [], answers = {};
    var studyMode = 'learn';   // learn = Kafra สอนทีละข้อ + ดูเฉลยได้ · exam = ทำเองไม่มีสอน ไม่มีเฉลย
    var mode = { name: 'exec' };

    function save() {
        try { localStorage.setItem(KEY, JSON.stringify({ S: S, startup: startup, hist: hist.slice(-200), done: done, answers: answers, study: studyMode })); } catch (e) {}
    }
    function reset() {
        S = freshState(); hist = []; done = []; answers = {};
        startup = L.initial && L.initial.saved ? runCfg() : null;
    }
    function load() {
        try {
            var d = JSON.parse(localStorage.getItem(KEY) || 'null');
            if (d && d.S && d.S.ports) {
                S = fix(d.S); startup = d.startup || null; hist = d.hist || []; done = d.done || []; answers = d.answers || {};
                studyMode = d.study === 'exam' ? 'exam' : 'learn';
                return true;
            }
        } catch (e) {}
        reset();
        return false;
    }

    // ---------- link / L2 model ----------
    function vlanIds() { return Object.keys(S.vlans).map(Number).sort(function (a, b) { return a - b; }); }
    function lagIds() { return Object.keys(S.lags).map(Number).sort(function (a, b) { return a - b; }); }
    function linkUp(n) { var p = S.ports[n]; return p.admin && !!CONN[pn(n)]; }      // ชั้นกายภาพ
    function bundled(n) {
        var p = S.ports[n], g = S.lags[p.lag];
        if (!g || !g.admin || !linkUp(n) || !g.lacp) return false;
        return !PEER.lacp || PEER.lacp.ports.indexOf(pn(n)) >= 0;
    }
    function fwd(n) { var p = S.ports[n]; return linkUp(n) && (!p.lag || bundled(n)); }  // ส่งข้อมูลได้จริง
    function lagUp(id) { var g = S.lags[id]; if (!g || !g.admin) return false; for (var n = 1; n <= NPORT; n++) if (S.ports[n].lag === +id && bundled(n)) return true; return false; }
    function lagMembers(id) { var r = []; for (var n = 1; n <= NPORT; n++) if (S.ports[n].lag === +id) r.push(n); return r; }
    function eff(n) { var p = S.ports[n]; return p.lag ? (S.lags[p.lag] || null) : p; }
    function inVlan(o, v) {
        if (!o || o.routing) return false;
        if (o.mode === 'access') return o.access === v;
        return o.native === v || o.allowed === 'all' || o.allowed.indexOf(v) >= 0;
    }
    function portInVlan(n, v) { return inVlan(eff(n), v); }
    function portSpeed(n) { return n < SFP ? 1000 : (SFP === 1 && n > NPORT - 4 ? 25000 : 10000); }
    function portType(n) { return n < SFP ? '1GbT' : (CONN[pn(n)] ? (n > NPORT - 4 && SFP === 1 ? 'SFP56DAC3' : 'SFP+DAC3') : '--'); }
    function sviUp(v) {
        var s = S.svis[v]; if (!s || !s.admin || !S.vlans[v] || !S.vlans[v].admin) return false;
        for (var n = 1; n <= NPORT; n++) if (portInVlan(n, v) && fwd(n)) return true;
        return false;
    }

    // ---------- L3 model ----------
    function l3ifs() {    // interface ที่มี IP ของเครื่องนี้
        var r = [];
        for (var n = 1; n <= NPORT; n++) {
            var p = S.ports[n];
            if (p.routing && p.ip) r.push({ name: pn(n), cidr: p.ip, up: fwd(n) && p.admin, ospf: p.ospf, port: n });
        }
        Object.keys(S.svis).map(Number).sort(function (a, b) { return a - b; }).forEach(function (v) {
            var s = S.svis[v]; if (s.ip) r.push({ name: 'vlan' + v, cidr: s.ip, up: sviUp(v), ospf: s.ospf, vlan: v });
        });
        return r;
    }
    function hostOn(ifc, ip) {    // ปลายทางใน subnet ที่ต่อตรง ต่ออยู่และส่งข้อมูลถึงไหม
        for (var i = 0; i < HOSTS.length; i++) {
            var h = HOSTS[i]; if (h.ip !== ip) continue;
            var n = (parseIf(h.port) || [0])[0]; if (!n || !fwd(n)) return false;
            if (ifc.port) return ifc.port === n;
            return portInVlan(n, ifc.vlan);
        }
        return false;
    }
    function ospfIfFor(ip) { var f = l3ifs(); for (var i = 0; i < f.length; i++) if (inNet(ip, f[i].cidr)) return f[i]; return null; }
    function ospfState() {
        var p = PEER.ospf; if (!p || !S.ospf) return null;
        var f = ospfIfFor(p.ip); if (!f || !f.up || !f.ospf) return null;
        var parts = String(f.ospf).split('|');
        if (+parts[0] !== S.ospf.pid) return null;
        var area = normArea(parts[1]);
        if (area !== normArea(p.area || '0') || S.ospf.areas.indexOf(area) < 0) return null;
        if (!hostOn(f, p.ip)) return null;
        return { ifc: f, area: area };
    }
    function routeTable() {
        var r = [];
        l3ifs().forEach(function (f) {
            if (!f.up) return;
            r.push({ prefix: netOf(f.cidr), nh: '-', ifn: f.name, o: 'C', d: '[0/0]' });
            r.push({ prefix: f.cidr.split('/')[0] + '/32', nh: '-', ifn: f.name, o: 'L', d: '[0/0]' });
        });
        S.routes.forEach(function (x) {
            var f = ospfIfFor(x.nh);
            if (f && f.up) r.push({ prefix: netOf(x.prefix), nh: x.nh, ifn: f.name, o: 'S', d: '[1/0]' });
        });
        var st = ospfState();
        // OSPF (AD 110) ไม่ถูกเลือกถ้ามี connected/static (AD 0/1) prefix เดียวกัน — แสดงเฉพาะ route ที่ใช้ forward
        if (st) (PEER.ospf.routes || []).forEach(function (pfx) {
            if (r.some(function (x) { return x.prefix === pfx; })) return;
            r.push({ prefix: pfx, nh: PEER.ospf.ip, ifn: st.ifc.name, o: 'O', d: '[110/' + (pfx === '0.0.0.0/0' ? 1 : 20) + ']' });
        });
        return r;
    }
    function lookup(ip) {
        var best = null;
        routeTable().forEach(function (x) {
            if (x.o === 'L' || !inNet(ip, x.prefix)) return;
            var len = +x.prefix.split('/')[1];
            if (!best || len > best.len || (len === best.len && x.o === 'S' && best.o === 'O')) best = { len: len, r: x };
        });
        return best && best.r;
    }
    function reach(ip) {
        var f = l3ifs(), i;
        for (i = 0; i < f.length; i++) if (f[i].cidr.split('/')[0] === ip) return f[i].up ? { ok: true, hops: [ip] } : { ok: false, why: 'unreach' };
        var r = lookup(ip);
        if (!r) return { ok: false, why: 'noroute' };
        var ifc = null; for (i = 0; i < f.length; i++) if (f[i].name === r.ifn) ifc = f[i];
        if (r.o === 'C') return hostOn(ifc, ip) ? { ok: true, hops: [ip] } : { ok: false, why: 'host' };
        if (!hostOn(ifc, r.nh)) return { ok: false, why: 'host' };
        var remote = PEER.remote || (PEER.ospf && PEER.ospf.routes) || [];
        var ok = remote.some(function (pfx) { return pfx !== '0.0.0.0/0' && inNet(ip, pfx); }) || ip === r.nh;
        return ok ? { ok: true, hops: [r.nh, ip] } : { ok: false, why: 'timeout', hops: [r.nh] };
    }
    function srcIp(ip) { var r = lookup(ip), f = l3ifs(); for (var i = 0; i < f.length; i++) if (r && f[i].name === r.ifn) return f[i].cidr.split('/')[0]; return f.length ? f[0].cidr.split('/')[0] : '0.0.0.0'; }

    // ---------- events ----------
    function stamp(d) {
        function z(x) { return ('0' + x).slice(-2); }
        return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()) + 'T' + z(d.getHours()) + ':' + z(d.getMinutes()) + ':' + z(d.getSeconds());
    }
    function ev(sev, daemon, id, msg) { S.events.push({ t: stamp(new Date()), d: daemon, id: id, sev: sev, msg: msg }); }
    var PID = { intfd: 2361, pmd: 1803, fand: 1755, tempd: 1771, hpe_config: 3120, lldpd: 2210, vsfd: 1932, 'hpe-restd': 4410, ntpd: 2650, mstpd: 2290, ops_ledd: 1702, lacpd: 2244, ospfv2d: 2701 };

    // ---------- output ----------
    var outEl = document.getElementById('termOut'), inEl = document.getElementById('termIn'),
        promptEl = document.getElementById('termPrompt'), termEl = document.getElementById('term');
    var cmdFailed = false;
    function print(lines, cls) {
        if (!Array.isArray(lines)) lines = String(lines).split('\n');
        var frag = document.createDocumentFragment();
        lines.forEach(function (l) { var d = document.createElement('div'); if (cls) d.className = cls; d.textContent = l; frag.appendChild(d); });
        outEl.appendChild(frag);
        while (outEl.childNodes.length > 3000) outEl.removeChild(outEl.firstChild);
        termEl.scrollTop = termEl.scrollHeight;
    }
    var lastExec = null;   // คำสั่งล่าสุดที่รัน (ให้ Kafra อธิบาย)
    function err(m) { cmdFailed = true; if (lastExec) lastExec.err = m; print(m, 'err'); }

    function prompt() {
        var h = S.hostname;
        switch (mode.name) {
            case 'config': return h + '(config)# ';
            case 'vlan': return h + (mode.vlans.length === 1 ? '(config-vlan-' + mode.vlans[0] + ')# ' : '(config-vlan-<' + cVlans(mode.vlans) + '>)# ');
            case 'if': return h + (mode.ports.length === 1 ? '(config-if)# ' : '(config-if-<' + cPorts(mode.ports) + '>)# ');
            case 'lag': return h + '(config-lag-if)# ';
            case 'svi': return h + '(config-if-vlan)# ';
            case 'ospf': return h + '(config-ospf-' + mode.pid + ')# ';
            default: return h + '# ';
        }
    }

    // ---------- show: config ----------
    function l2lines(o, out) {
        if (o.routing) {
            out.push('    routing');
            if (o.ip) out.push('    ip address ' + o.ip);
        } else if (o.mode === 'access') {
            out.push('    vlan access ' + o.access);
        } else {
            out.push('    vlan trunk native ' + o.native);
            out.push('    vlan trunk allowed ' + (o.allowed === 'all' ? 'all' : (o.allowed.length ? cVlans(o.allowed) : 'none')));
        }
    }
    function runCfg(only) {
        var o = [], sy = S.sys;
        function portBlock(n) {
            var p = S.ports[n];
            o.push('interface ' + pn(n));
            if (p.desc) o.push('    description ' + p.desc);
            o.push(p.admin ? '    no shutdown' : '    shutdown');
            if (p.lag) o.push('    lag ' + p.lag);
            else l2lines(p, o);
            if (p.ospf) { var q = p.ospf.split('|'); o.push('    ip ospf ' + q[0] + ' area ' + normArea(q[1])); }
            if (p.bpdu) o.push('    spanning-tree bpdu-guard');
            if (p.edge) o.push('    spanning-tree port-type admin-edge');
            o.push('    exit');
        }
        if (only) { only.forEach(portBlock); return o; }
        o.push('Current configuration:', '!', '!Version ArubaOS-CX ' + VER, '!export-password: default', 'hostname ' + S.hostname,
            'user admin group administrators password ciphertext AQBapLAB...');
        Object.keys(sy.users).forEach(function (u) { o.push('user ' + u + ' group ' + sy.users[u] + ' password ciphertext AQBapLAB' + u.length + '...'); });
        if (sy.tz) o.push('clock timezone ' + sy.tz);
        sy.logging.forEach(function (ip) { o.push('logging ' + ip); });
        sy.ntp.forEach(function (ip) { o.push('ntp server ' + ip + ' iburst'); });
        if (sy.ntpOn) o.push('ntp enable');
        o.push('!', '!');
        sy.ssh.forEach(function (v) { o.push('ssh server vrf ' + v); });
        sy.snmpVrf.forEach(function (v) { o.push('snmp-server vrf ' + v); });
        sy.snmp.forEach(function (c) { o.push('snmp-server community ' + c); });
        if (DEV.vsf) o.push('vsf member 1', '    type ' + (DEV.vsf.members[0].type || 'jl658a').toLowerCase(), '    link 1 1/1/' + NPORT, 'vsf member 2', '    type ' + (DEV.vsf.members[1].type || 'jl658a').toLowerCase(), '    link 1 2/1/' + NPORT);
        vlanIds().forEach(function (v) {
            var x = S.vlans[v]; o.push('vlan ' + v);
            if (v !== 1 && x.name !== 'VLAN' + v) o.push('    name ' + x.name);
            if (x.desc) o.push('    description ' + x.desc);
            if (!x.admin) o.push('    shutdown');
            if (v !== 1 && (x.name !== 'VLAN' + v || x.desc || !x.admin)) o.push('    exit');
        });
        o.push('spanning-tree');
        if (S.stp.mode !== 'mstp') o.push('spanning-tree mode ' + S.stp.mode);
        if (S.stp.prio !== 8) o.push('spanning-tree priority ' + S.stp.prio);
        o.push('interface mgmt', '    no shutdown', DEV.mgmtIp ? '    ip static ' + DEV.mgmtIp : '    ip dhcp');
        lagIds().forEach(function (id) {
            var g = S.lags[id];
            o.push('interface lag ' + id);
            if (g.desc) o.push('    description ' + g.desc);
            o.push(g.admin ? '    no shutdown' : '    shutdown');
            l2lines(g, o);
            if (g.lacp) o.push('    lacp mode ' + g.lacp);
            o.push('    exit');
        });
        for (var n = 1; n <= NPORT; n++) portBlock(n);
        Object.keys(S.svis).map(Number).sort(function (a, b) { return a - b; }).forEach(function (v) {
            var s = S.svis[v]; o.push('interface vlan ' + v);
            if (s.desc) o.push('    description ' + s.desc);
            if (!s.admin) o.push('    shutdown');
            if (s.ip) o.push('    ip address ' + s.ip);
            if (s.ospf) { var q = s.ospf.split('|'); o.push('    ip ospf ' + q[0] + ' area ' + normArea(q[1])); }
            o.push('    exit');
        });
        S.routes.forEach(function (r) { o.push('ip route ' + r.prefix + ' ' + r.nh); });
        if (S.ospf) {
            o.push('router ospf ' + S.ospf.pid);
            if (S.ospf.rid) o.push('    router-id ' + S.ospf.rid);
            S.ospf.areas.forEach(function (a) { o.push('    area ' + a); });
            o.push('    exit');
        }
        o.push('!', 'https-server vrf mgmt');
        return o;
    }
    function showVlan(only) {
        var line = dash(100);
        var o = [line, pad('VLAN', 6) + pad('Name', 34) + pad('Status', 8) + pad('Reason', 20) + pad('Type', 10) + 'Interfaces', line];
        if (only && !S.vlans[only]) return err('VLAN ' + only + ' does not exist.');
        (only ? [only] : vlanIds()).forEach(function (v) {
            var x = S.vlans[v], mem = [], lg = [];
            for (var n = 1; n <= NPORT; n++) if (!S.ports[n].lag && portInVlan(n, v)) mem.push(n);
            lagIds().forEach(function (id) { if (inVlan(S.lags[id], v)) lg.push('lag' + id); });
            var list = (mem.length ? [cPorts(mem)] : []).concat(lg).join(',');
            o.push(pad(v, 6) + pad(x.name, 34) + pad(x.admin ? 'up' : 'down', 8) + pad(x.admin ? 'ok' : 'admin_down', 20) +
                pad(v === 1 ? 'default' : 'static', 10) + list);
        });
        print(o);
    }
    function ifRow(n) {
        var p = S.ports[n], up = linkUp(n), o = eff(n) || p;
        var reason = !p.admin ? 'Administratively down' : (up ? (p.lag && !bundled(n) ? 'LACP not in sync' : '') : 'Waiting for link');
        var md = p.lag ? 'lag' + p.lag : (o.routing ? 'routed' : o.mode);
        return pad(pn(n), 11) + pad(o.routing ? '--' : (o.mode === 'access' ? o.access : o.native), 8) +
            pad(md, 8) + pad(portType(n), 11) + pad(p.admin ? 'yes' : 'no', 8) + pad(up ? 'up' : 'down', 7) +
            pad(reason || '--', 23) + pad(up ? portSpeed(n) : '--', 8) + (p.desc || '--');
    }
    function showIfBrief() {
        var line = dash(107);
        var o = [line, pad('Port', 11) + pad('Native', 8) + pad('Mode', 8) + pad('Type', 11) + pad('Enabled', 8) + pad('Status', 7) + pad('Reason', 23) + pad('Speed', 8) + 'Description',
            pad('', 11) + pad('VLAN', 8) + pad('', 8) + pad('', 11) + pad('', 8) + pad('', 7) + pad('', 23) + '(Mb/s)', line];
        for (var n = 1; n <= NPORT; n++) o.push(ifRow(n));
        lagIds().forEach(function (id) {
            var g = S.lags[id], up = lagUp(id);
            o.push(pad('lag' + id, 11) + pad(g.routing ? '--' : (g.mode === 'access' ? g.access : g.native), 8) + pad(g.routing ? 'routed' : g.mode, 8) +
                pad('--', 11) + pad(g.admin ? 'yes' : 'no', 8) + pad(up ? 'up' : 'down', 7) + pad(!g.admin ? 'Administratively down' : (up ? '--' : 'No member in sync'), 23) +
                pad(up ? lagMembers(id).filter(bundled).length * portSpeed(lagMembers(id)[0]) : '--', 8) + (g.desc || '--'));
        });
        print(o);
    }
    function showIf(ports) {
        var o = [];
        ports.forEach(function (n) {
            var p = S.ports[n], up = linkUp(n), x = eff(n) || p;
            o.push('', 'Interface ' + pn(n) + ' is ' + (up ? 'up' : 'down'),
                ' Admin state is ' + (p.admin ? 'up' : 'down'),
                ' State information: ' + (!p.admin ? 'Administratively down' : (up ? '' : 'Waiting for link')),
                ' Description: ' + (p.desc || ''),
                ' Hardware: Ethernet, MAC Address: ' + MYMAC.slice(0, 15) + hex2(n),
                ' MTU 1500', ' Type ' + portType(n),
                ' Speed ' + (up ? portSpeed(n) : 0) + ' Mb/s');
            if (p.lag) o.push(' Member of lag' + p.lag + (bundled(n) ? ' (in sync)' : ' (not in sync)'));
            else if (x.routing) o.push(' L3 (routed) interface', ' IPv4 address ' + (x.ip || 'not configured'));
            else if (x.mode === 'access') o.push(' L2 VLAN mode: access', ' Access VLAN: ' + x.access);
            else o.push(' L2 VLAN mode: native-untagged', ' Native VLAN: ' + x.native, ' Allowed VLAN List: ' + (x.allowed === 'all' ? 'all' : cVlans(x.allowed)));
            if (up) {
                var util = (L.utilization || {})[pn(n)] || [1, 1];
                o.push(' Rate collection interval: 300 seconds', '', ' Rate                               RX                   TX', ' ' + dash(66),
                    ' Utilization (%)       ' + rpad(Number(util[0]).toFixed(2), 20) + rpad(Number(util[1]).toFixed(2), 21));
            }
        });
        print(o);
    }
    function showIpBrief() {
        var o = [pad('Interface', 16) + pad('IP Address', 20) + 'Interface Status', pad('', 36) + 'link/admin'];
        for (var n = 1; n <= NPORT; n++) {
            var p = S.ports[n];
            if (p.routing) o.push(pad(pn(n), 16) + pad(p.ip || 'No Address', 20) + (fwd(n) ? 'up' : 'down') + '/' + (p.admin ? 'up' : 'down'));
        }
        Object.keys(S.svis).map(Number).sort(function (a, b) { return a - b; }).forEach(function (v) {
            var s = S.svis[v];
            o.push(pad('vlan' + v, 16) + pad(s.ip || 'No Address', 20) + (sviUp(v) ? 'up' : 'down') + '/' + (s.admin ? 'up' : 'down'));
        });
        print(o);
    }

    // ---------- show: ระบบ / สภาพแวดล้อม (ค่าจาก device ในบทเรียน) ----------
    function showVersion() {
        print([dash(77), 'ArubaOS-CX (Lab simulator — not a real device)', dash(77),
            'Version      : ' + VER, 'Build Date   : (lab)', 'Image Name   : ' + VER.replace(/\./g, '_'),
            'Platform     : ' + (DEV.product || DEV.model || '6300'), 'Active Image : primary', 'Service OS Version : FL.01.13.0001']);
    }
    function showSystem() {
        var cpu = arr(DEV.cpu, 5), mem = arr(DEV.mem, 25);
        print(['Hostname           : ' + S.hostname, 'System Description : ' + VER, 'System Contact     : ',
            'System Location    : ' + (DEV.location || ''), 'Vendor             : Aruba',
            'Product Name       : ' + (DEV.product || DEV.model || ''), 'Chassis Serial Nbr : ' + (DEV.serial || 'SG00LAB000'),
            'Base MAC Address   : ' + MYMAC, 'ArubaOS-CX Version : ' + VER, '',
            'Time Zone          : ' + (S.sys.tz || 'UTC'), '',
            'Up Time            : ' + (DEV.uptime || '3 days, 2 hours, 10 minutes'),
            'CPU Util (%)       : ' + cpu[0], 'CPU Util (%) [1m]  : ' + cpu[0], 'CPU Util (%) [5m]  : ' + cpu[0],
            'Memory Usage (%)   : ' + mem[0]]);
    }
    function showResource() {
        var cpu = arr(DEV.cpu, 5), mem = arr(DEV.mem, 25), o = ['System Resource Utilization Data poll interval: 10 seconds', ''];
        cpu.forEach(function (c, i) {
            if (cpu.length > 1) o.push('Member ' + (i + 1));
            o.push('  CPU usage(%)      : ' + c, '  Memory usage(%)   : ' + (mem[i] !== undefined ? mem[i] : mem[0]),
                '  Processes         : ' + (96 + i * 3), "  Open FD's         : " + (2380 + i * 41), '');
        });
        print(o);
    }
    function showUptime() { print('System has been up ' + (DEV.uptime || '3 days, 2 hours, 10 minutes')); }
    function showClock() { print(new Date().toString().replace(/ GMT.*$/, '') + ' ' + (S.sys.tz || 'UTC')); }
    function showFan() {
        var fans = DEV.fans || [['1/1', 'normal', 'ok', 7200], ['1/2', 'normal', 'ok', 7250]];
        var o = ['Fan information', dash(79), pad('Mbr/Fan', 14) + pad('Product', 9) + pad('Serial Number', 15) + pad('Speed', 8) + pad('Direction', 15) + pad('Status', 8) + 'RPM',
            pad('', 14) + 'Name', dash(79)];
        fans.forEach(function (f) { o.push(pad(f[0], 14) + pad('N/A', 9) + pad('N/A', 15) + pad(f[1], 8) + pad('front-to-back', 15) + pad(f[2], 8) + f[3]); });
        print(o);
    }
    function showPsu() {
        var psus = DEV.psus || [['1/1', 'JL085A', 'CN0LAB0001', 'OK', 250]];
        var o = [pad('', 9) + pad('Product', 9) + pad('Serial', 18) + pad('PSU', 15) + pad('Input', 8) + pad('Voltage', 11) + 'Wattage',
            pad('Mbr/PSU', 9) + pad('Number', 9) + pad('Number', 18) + pad('Status', 15) + pad('Type', 8) + pad('Range', 11) + 'Maximum', dash(80)];
        psus.forEach(function (p) {
            var ok = /^ok$/i.test(p[3]);
            o.push(pad(p[0], 9) + pad(p[1], 9) + pad(p[2], 18) + pad(p[3], 15) + pad(ok ? 'AC' : '--', 8) + pad(ok ? '100-240V' : '--', 11) + (ok ? p[4] : 0));
        });
        print(o);
    }
    function showTemp() {
        var t = DEV.temps || [['1/1-CPU', 'management-module', 45.0, 'normal']];
        var o = ['Temperature information', dash(78), pad('', 52) + 'Current',
            pad('Mbr/Slot-Sensor', 32) + pad('Module Type', 20) + pad('temperature', 13) + 'Status', dash(78)];
        t.forEach(function (x) { o.push(pad(x[0], 32) + pad(x[1], 20) + pad(Number(x[2]).toFixed(2) + ' C', 13) + x[3]); });
        print(o);
    }
    function stpView() {
        var ps = PEER.stp;
        if (!ps) return DEV.stp || { protocol: 'MSTP', priority: 32768, root: false };
        var me = S.stp.prio * 4096, rp = (parseIf(ps.port) || [0])[0];
        var rpUp = /^lag/.test(ps.port) ? lagUp(+ps.port.slice(3)) : (rp && fwd(rp));
        var root = me < ps.priority || !rpUp;
        return { protocol: S.stp.mode === 'mstp' ? 'MSTP' : 'RPVST', priority: me, root: root, rootPort: ps.port, rootPriority: ps.priority, rootMac: ps.mac || '38:21:c7:11:22:00' };
    }
    function showStp() {
        var st = stpView();
        var o = ['Spanning tree status        : Enabled Protocol: ' + (st.protocol || 'MSTP'), '', 'MST0',
            '  Root ID    Priority    : ' + (st.root ? st.priority : (st.rootPriority || 4096)),
            '             MAC-Address : ' + (st.root ? MYMAC : (st.rootMac || '38:21:c7:11:22:00')),
            st.root ? '             This bridge is the root' : '             Root Port   : ' + (st.rootPort || ''),
            '             Hello time(in seconds):2  Max Age(in seconds):20', '             Forward Delay(in seconds):15', '',
            '  Bridge ID  Priority    : ' + st.priority, '             MAC-Address : ' + MYMAC,
            '             Hello time(in seconds):2  Max Age(in seconds):20', '             Forward Delay(in seconds):15', '',
            pad('Port', 15) + pad('Role', 15) + pad('State', 11) + pad('Cost', 11) + pad('Priority', 11) + 'Type',
            pad(dash(14), 15) + pad(dash(14), 15) + pad(dash(10), 11) + pad(dash(10), 11) + pad(dash(10), 11) + dash(10)];
        for (var n = 1; n <= NPORT; n++) {
            var p = S.ports[n]; if (p.routing || p.lag || !fwd(n)) continue;
            var isRoot = !st.root && st.rootPort === pn(n);
            o.push(pad(pn(n), 15) + pad(isRoot ? 'Root' : 'Designated', 15) + pad('Forwarding', 11) + pad(portSpeed(n) >= 10000 ? 2000 : 20000, 11) +
                pad(128, 11) + (p.edge ? 'P2P Edge' : 'P2P'));
        }
        lagIds().forEach(function (id) {
            if (!lagUp(id)) return;
            var isRoot = !st.root && st.rootPort === 'lag' + id;
            o.push(pad('lag' + id, 15) + pad(isRoot ? 'Root' : 'Designated', 15) + pad('Forwarding', 11) + pad(1000, 11) + pad(64, 11) + 'P2P');
        });
        print(o);
    }
    function showVsf() {
        var v = DEV.vsf; if (!v) return err('VSF is not configured on this switch.');
        var o = ['MAC Address           : ' + v.members[0].mac, 'Secondary             : 2', 'Topology              : ' + (v.topology || 'Chain'),
            'Status                : ' + (v.status || 'No Split'), 'Split Detection Method: ' + (v.split || 'None'), '',
            pad('Mbr', 5) + pad('MAC Address', 20) + pad('Type', 15) + 'Status', 'ID', pad('---', 5) + pad(dash(18), 20) + pad(dash(13), 15) + dash(15)];
        v.members.forEach(function (m, i) { o.push(pad(' ' + (i + 1), 5) + pad(m.mac, 20) + pad(m.type, 15) + m.status); });
        print(o);
    }
    function allEvents() {
        return (DEV.events || []).concat(S.events).slice().sort(function (a, b) { return a.t < b.t ? -1 : a.t > b.t ? 1 : 0; });
    }
    function showEvents(rev) {
        var e = allEvents(); if (rev) e.reverse();
        var o = [dash(51), 'Event logs from current boot', dash(51)];
        e.forEach(function (x) {
            o.push(x.t + '.' + String(100000 + (x.id * 37) % 899999).slice(0, 6) + '+07:00 ' + S.hostname + ' ' + x.d + '[' + (PID[x.d] || 2000) + ']: Event|' + x.id + '|' + x.sev + '|' + (x.mod || 'AMM') + '|' + (x.slot || '1/1') + '|' + x.msg);
        });
        print(o);
    }
    function showCheckpoint() {
        var rows = (DEV.checkpoints || []).slice();
        if (startup && S.savedAt) rows.push(['startup-config', 'startup', 'User', S.savedAt]);
        var o = [pad('NAME', 30) + pad('TYPE', 12) + pad('WRITER', 11) + pad('DATE(YYYY/MM/DD)', 21) + 'IMAGE VERSION'];
        rows.forEach(function (r) { o.push(pad(r[0], 30) + pad(r[1], 12) + pad(r[2], 11) + pad(r[3], 21) + VER); });
        print(o);
    }
    function showLldp() {
        var rows = [];
        for (var n = 1; n <= NPORT; n++) { var x = LLDP[pn(n)]; if (x && linkUp(n)) rows.push([n, x]); }
        var o = ['LLDP Neighbor Information', '=========================', '', 'Total Neighbor Entries          : ' + rows.length,
            'Total Neighbor Entries Deleted  : 0', 'Total Neighbor Entries Dropped  : 0', 'Total Neighbor Entries Aged-Out : 0', '',
            pad('LOCAL-PORT', 12) + pad('CHASSIS-ID', 19) + pad('PORT-ID', 13) + pad('PORT-DESC', 13) + pad('TTL', 6) + 'SYS-NAME', dash(80)];
        rows.forEach(function (r) { o.push(pad(pn(r[0]), 12) + pad(r[1].mac || '38:21:c7:11:22:' + hex2(r[0]), 19) + pad(r[1].port, 13) + pad(r[1].port, 13) + pad(120, 6) + r[1].sys); });
        print(o);
    }
    function showMac() {
        var rows = [];
        for (var n = 1; n <= NPORT; n++) {
            var p = S.ports[n], x = eff(n); if (!x || x.routing || !fwd(n)) continue;
            var where = p.lag ? 'lag' + p.lag : pn(n);
            if (x.mode === 'access') rows.push([MACS[pn(n)] || '00:50:56:a1:' + hex2(n >> 8) + ':' + hex2(n), x.access, where]);
            else {
                var vl = x.allowed === 'all' ? vlanIds() : uniqSort(x.allowed.concat([x.native]));
                vl.forEach(function (v) { if (S.vlans[v]) rows.push(['38:21:c7:11:' + hex2(v >> 8) + ':' + hex2(v), v, where]); });
            }
        }
        rows = rows.filter(function (r, i) { return !rows.slice(0, i).some(function (q) { return q[0] === r[0] && q[1] === r[1]; }); });
        var o = ['MAC age-time            : 300 seconds', 'Number of MAC addresses : ' + rows.length, '',
            pad('MAC Address', 21) + pad('VLAN', 9) + pad('Type', 26) + 'Port', dash(62)];
        rows.forEach(function (r) { o.push(pad(r[0], 21) + pad(r[1], 9) + pad('dynamic', 26) + r[2]); });
        print(o);
    }
    function showArp() {
        var o = [pad('IPv4 Address', 17) + pad('MAC', 19) + pad('Port', 13) + pad('Physical Port', 15) + 'State', dash(75)], c = 0;
        l3ifs().forEach(function (f) {
            if (!f.up) return;
            HOSTS.forEach(function (h) {
                if (!inNet(h.ip, f.cidr) || !hostOn(f, h.ip)) return;
                c++; o.push(pad(h.ip, 17) + pad(h.mac || MACS[h.port] || '00:50:56:a1:00:' + hex2(ipInt(h.ip)), 19) + pad(f.name, 13) + pad(h.port, 15) + 'reachable');
            });
        });
        o.push('', 'Total Number Of ARP Entries Listed: ' + c + '.');
        print(o);
    }
    function showLacpIf() {
        var o = ['State abbreviations :', 'A - Active        P - Passive      F - Aggregable I - Individual',
            'S - Short-timeout L - Long-timeout N - InSync     O - OutofSync', 'C - Collecting    D - Distributing',
            'X - State m/c expired              E - Default neighbor state', '', 'Actor details of all interfaces:', dash(82),
            pad('Intf', 8) + pad('Aggr', 9) + pad('Port', 6) + pad('Port', 6) + pad('State', 8) + pad('System-ID', 18) + pad('System', 7) + pad('Aggr', 5) + 'Forwarding',
            pad('', 8) + pad('Name', 9) + pad('Id', 6) + pad('Pri', 6) + pad('', 8) + pad('', 18) + pad('Pri', 7) + pad('Key', 5) + 'State', dash(82)];
        var rows = [];
        for (var n = 1; n <= NPORT; n++) if (S.ports[n].lag) rows.push(n);
        rows.forEach(function (n) {
            var p = S.ports[n], g = S.lags[p.lag] || {}, b = bundled(n);
            var st = (g.lacp === 'passive' ? 'P' : 'A') + 'LF' + (b ? 'NCD' : 'O');
            o.push(pad(pn(n), 8) + pad('lag' + p.lag, 9) + pad(n + 1, 6) + pad(1, 6) + pad(g.lacp ? st : '--', 8) + pad(MYMAC, 18) + pad(65534, 7) + pad(p.lag, 5) + (b ? 'up' : 'down'));
        });
        o.push('', 'Partner details of all interfaces:', dash(82),
            pad('Intf', 8) + pad('Aggr', 9) + pad('Port', 6) + pad('Port', 6) + pad('State', 8) + pad('System-ID', 18) + pad('System', 7) + 'Aggr',
            pad('', 8) + pad('Name', 9) + pad('Id', 6) + pad('Pri', 6) + pad('', 8) + pad('', 18) + pad('Pri', 7) + 'Key', dash(82));
        rows.forEach(function (n) {
            var p = S.ports[n], b = bundled(n), peer = PEER.lacp && PEER.lacp.ports.indexOf(pn(n)) >= 0 && linkUp(n);
            o.push(pad(pn(n), 8) + pad('lag' + p.lag, 9) + pad(peer ? 47 + n : 0, 6) + pad(peer ? 1 : 0, 6) + pad(peer ? (b ? 'ALFNCD' : 'ALFOE') : 'PLFOEX', 8) +
                pad(peer ? (PEER.lacp.mac || '38:21:c7:11:22:00') : '00:00:00:00:00:00', 18) + pad(peer ? 65534 : 0, 7) + (peer ? 1 : 0));
        });
        print(o);
    }
    function showLacpAgg() {
        var o = [];
        lagIds().forEach(function (id) {
            var g = S.lags[id];
            o.push('Aggregate name   : lag' + id, 'Interfaces       : ' + lagMembers(id).map(pn).join(' '), 'Heartbeat rate   : Slow',
                'Hash             : l3-src-dst', 'Aggregate mode   : ' + (g.lacp ? g.lacp.charAt(0).toUpperCase() + g.lacp.slice(1) : 'Off (static)'), '');
        });
        print(o.length ? o : 'No LAG configured.');
    }
    function showRoute() {
        var o = ['Displaying ipv4 routes selected for forwarding', '', 'Origin Codes: C - connected, S - static, L - local',
            '              R - RIP, B - BGP, O - OSPF, D - DHCP', 'Type Codes:   E - External BGP, I - Internal BGP, V - VPN, EV - EVPN',
            '              IA - OSPF internal area, E1 - OSPF external type 1', '              E2 - OSPF external type 2', '', 'VRF: default', '',
            pad('Prefix', 20) + pad('Nexthop', 17) + pad('Interface', 14) + pad('VRF(egress)', 18) + pad('Origin/', 8) + pad('Distance/', 13) + 'Age',
            pad('', 69) + pad('Type', 8) + 'Metric', dash(104)];
        routeTable().sort(function (a, b) { return ipInt(a.prefix.split('/')[0]) - ipInt(b.prefix.split('/')[0]) || (+a.prefix.split('/')[1]) - (+b.prefix.split('/')[1]); })
            .forEach(function (r) { o.push(pad(r.prefix, 20) + pad(r.nh, 17) + pad(r.ifn, 14) + pad('-', 18) + pad(r.o === 'O' ? 'O/IA' : r.o, 8) + pad(r.d, 13) + (r.o === 'C' || r.o === 'L' ? '-' : '00h:03m:12s')); });
        o.push('', 'Total Route Count : ' + routeTable().length);
        print(o);
    }
    function showOspfNb() {
        if (!S.ospf) return err('OSPF is not configured.');
        var st = ospfState();
        var o = ['VRF : default                          Process : ' + S.ospf.pid, '===================================================', '',
            'Total Number of Neighbors : ' + (st ? 1 : 0), '', pad('Neighbor ID', 17) + pad('Priority', 10) + pad('State', 18) + pad('Nbr Address', 18) + 'Interface', dash(73)];
        if (st) o.push(pad(PEER.ospf.rid, 17) + pad(1, 10) + pad('FULL/DR', 18) + pad(PEER.ospf.ip, 18) + st.ifc.name);
        print(o);
    }
    function showNtp() {
        var sy = S.sys, srv = sy.ntp.filter(function (ip) { return (PEER.ntp || []).indexOf(ip) >= 0 && reach(ip).ok; });
        print(['NTP Status Information', '', 'NTP                         : ' + (sy.ntpOn ? 'Enabled' : 'Disabled'),
            'NTP Authentication          : Disabled', 'NTP Server Connections      : Using the default VRF', '',
            'System time                 : ' + new Date().toString().replace(/ GMT.*$/, ''), 'NTP uptime                  : 0 minutes',
            sy.ntpOn && srv.length ? 'Synchronized to NTP Server  : ' + srv[0] + ' at stratum 3' : 'Not synchronized with an NTP server.']);
    }
    function showNtpAssoc() {
        var o = [pad(' ID', 6) + pad('NAME', 18) + pad('REMOTE', 18) + pad('REF-ID', 14) + pad('ST', 4) + pad('LAST', 6) + pad('POLL', 6) + 'REACH', dash(80)];
        S.sys.ntp.forEach(function (ip, i) {
            var ok = S.sys.ntpOn && (PEER.ntp || []).indexOf(ip) >= 0 && reach(ip).ok;
            o.push(pad((ok ? '*' : ' ') + (i + 1), 6) + pad(ip, 18) + pad(ok ? ip : '0.0.0.0', 18) + pad(ok ? '.GPS.' : '.INIT.', 14) + pad(ok ? 3 : 16, 4) + pad(ok ? 12 : '-', 6) + pad(64, 6) + (ok ? 377 : 0));
        });
        print(o);
    }
    function showSsh() {
        if (!S.sys.ssh.length) return print('SSH server is not enabled on any VRF.');
        var o = [];
        S.sys.ssh.forEach(function (v) { o.push('SSH server configuration on VRF ' + v + ' :', '', '  IP Version           : IPv4 and IPv6', '  SSH Version          : 2.0', '  TCP Port             : 22', '  Max SSH Sessions     : 5', ''); });
        print(o);
    }
    function showSnmp() {
        var o = [pad('Community', 28) + pad('Access', 12) + 'View', dash(52)];
        S.sys.snmp.forEach(function (c) { o.push(pad(c, 28) + pad('ro', 12) + 'none'); });
        o.push('', 'SNMP agent VRF: ' + (S.sys.snmpVrf.join(', ') || '(not enabled)'));
        print(o);
    }
    function showUsers() {
        var o = [pad('USER', 24) + 'GROUP', dash(40), pad('admin', 24) + 'administrators'];
        Object.keys(S.sys.users).forEach(function (u) { o.push(pad(u, 24) + S.sys.users[u]); });
        print(o);
    }
    function doPing(ip) {
        var r = reach(ip), src = srcIp(ip), o = ['PING ' + ip + ' (' + ip + ') 100(128) bytes of data.'];
        for (var i = 1; i <= 5; i++) {
            if (r.ok) o.push('108 bytes from ' + ip + ': icmp_seq=' + i + ' ttl=' + (r.hops.length > 1 ? 63 : 64) + ' time=' + (0.3 + i * 0.05 + r.hops.length * 0.4).toFixed(3) + ' ms');
            else if (r.why === 'host') o.push('From ' + src + ' icmp_seq=' + i + ' Destination Host Unreachable');
        }
        if (r.why === 'noroute') return print(['ping: connect: Network is unreachable']);
        o.push('', '--- ' + ip + ' ping statistics ---', '5 packets transmitted, ' + (r.ok ? 5 : 0) + ' received, ' + (r.ok ? '0' : '100') + '% packet loss, time 4005ms');
        if (r.ok) o.push('rtt min/avg/max/mdev = 0.351/0.512/0.802/0.150 ms');
        print(o);
    }
    function doTrace(ip) {
        var r = reach(ip), o = ['traceroute to ' + ip + ' (' + ip + '), 1 hops min, 30 hops max, 3 sec. timeout, 3 probes'];
        if (r.why === 'noroute') return print('traceroute: connect: Network is unreachable');
        var hops = r.hops || [];
        hops.forEach(function (h, i) { o.push(rpad(i + 1, 2) + '   ' + h + '  ' + (0.4 + i * 0.3).toFixed(3) + 'ms  ' + (0.42 + i * 0.3).toFixed(3) + 'ms  ' + (0.39 + i * 0.3).toFixed(3) + 'ms'); });
        if (!r.ok) for (var i = hops.length + 1; i <= hops.length + 3; i++) o.push(rpad(i, 2) + '   * * *');
        print(o);
    }
    function savedNow() { return !!startup && startup.join('\n') === runCfg().join('\n'); }
    function writeMem() {
        startup = runCfg(); S.savedAt = stamp(new Date()).replace(/-/g, '/').replace('T', ' ');
        print('Copying configuration: [Success]');
        ev('LOG_INFO', 'hpe_config', 6801, 'Running configuration copied to startup configuration');
    }

    // ---------- command tables ----------
    function D(w, run, parent) { return { w: w.split(' '), run: run, parent: !!parent }; }
    function targets() {
        if (mode.name === 'lag') return [{ o: S.lags[mode.lag], name: 'lag' + mode.lag, n: 0 }];
        return mode.ports.map(function (n) { return { o: S.ports[n], name: pn(n), n: n }; });
    }
    function forT(fn) { var t = targets(), bad = null; t.forEach(function (x) { if (bad) return; bad = fn(x.o, x.name, x.n); }); if (bad) err(bad); }
    function needVlan(v) { return S.vlans[v] ? null : 'VLAN ' + v + ' does not exist. Create it first using "vlan ' + v + '".'; }
    function trunkCleanup(p) { if (p.mode === 'trunk' && p.native === 1 && Array.isArray(p.allowed) && !p.allowed.length) { p.mode = 'access'; p.access = 1; p.allowed = 'all'; } }
    function l2guard(o, name) {
        if (o.lag) return 'Interface ' + name + ' is a member of lag' + o.lag + '. Configure the LAG interface instead.';
        if (o.routing) return 'Interface ' + name + ' is a routed (L3) interface. Use "no routing" first.';
        return null;
    }

    var SHOW = [
        D('show running-config', function () { print(runCfg()); }),
        D('show running-config interface <IFNAME>', function (a) { print(runCfg(parseIf(a[3]))); }),
        D('show startup-config', function () { startup ? print(startup) : err('No saved configuration. Use "write memory".'); }),
        D('show vlan', function () { showVlan(); }),
        D('show vlan <VLAN-ID>', function (a) { showVlan(+a[2]); }),
        D('show interface brief', showIfBrief),
        D('show interface <IFNAME>', function (a) { showIf(parseIf(a[2])); }),
        D('show ip interface brief', showIpBrief),
        D('show ip route', showRoute),
        D('show ip ospf neighbors', showOspfNb),
        D('show arp', showArp),
        D('show lacp interfaces', showLacpIf),
        D('show lacp aggregates', showLacpAgg),
        D('show version', showVersion),
        D('show system', showSystem),
        D('show system resource-utilization', showResource),
        D('show uptime', showUptime),
        D('show clock', showClock),
        D('show environment fan', showFan),
        D('show environment power-supply', showPsu),
        D('show environment temperature', showTemp),
        D('show spanning-tree', showStp),
        D('show vsf', showVsf),
        D('show events', function () { showEvents(false); }),
        D('show events -r', function () { showEvents(true); }),
        D('show logging', function () { showEvents(false); }),
        D('show logging -r', function () { showEvents(true); }),
        D('show checkpoint', showCheckpoint),
        D('show lldp neighbor-info', showLldp),
        D('show mac-address-table', showMac),
        D('show ntp status', showNtp),
        D('show ntp associations', showNtpAssoc),
        D('show ssh server', showSsh),
        D('show snmp community', showSnmp),
        D('show user-list', showUsers),
        D('show history', function () { print(hist.slice(-30).map(function (h, i) { return pad(i + 1, 5) + h; })); }),
        D('ping <IP>', function (a) { doPing(a[1]); }),
        D('traceroute <IP>', function (a) { doTrace(a[1]); })
    ];
    var COMMON = [
        D('end', function () { mode = { name: 'exec' }; }),
        D('exit', function () {
            if (mode.name === 'config') mode = { name: 'exec' };
            else if (mode.name !== 'exec') mode = { name: 'config' };
        })
    ];
    var EXEC = [
        D('configure terminal', function () { mode = { name: 'config' }; }),
        D('configure', function () { mode = { name: 'config' }; }),
        D('write memory', writeMem),
        D('copy running-config startup-config', writeMem),
        D('no page', function () {}),
        D('page', function () {})
    ];
    function addUser(a, grp) {
        if (!/^[A-Za-z][\w.\-]{0,31}$/.test(a[1])) return err('Invalid user name.');
        if (a[1] === 'admin') return err('User admin already exists.');
        if (a[6].length < 1) return err('Invalid password.');
        S.sys.users[a[1]] = grp;
    }
    function uniqAdd(list, v) { if (list.indexOf(v) < 0) list.push(v); }
    function del(list, v) { var i = list.indexOf(v); if (i >= 0) list.splice(i, 1); }
    var CONFIG = [
        D('hostname <WORD>', function (a) {
            if (!/^[A-Za-z][A-Za-z0-9_.\-]{0,31}$/.test(a[1])) return err('Invalid hostname. Must start with a letter, max 32 characters (letters, digits, - _ .).');
            S.hostname = a[1];
        }),
        D('no hostname', function () { S.hostname = 'switch'; }),
        D('vlan <VLAN-LIST>', function (a) {
            var ids = parseVlans(a[1]);
            ids.forEach(function (v) { if (!S.vlans[v]) S.vlans[v] = { name: 'VLAN' + v, desc: '', admin: true }; });
            mode = { name: 'vlan', vlans: ids };
        }),
        D('no vlan <VLAN-LIST>', function (a) {
            var ids = parseVlans(a[2]);
            for (var k = 0; k < ids.length; k++) {
                var v = ids[k];
                if (v === 1) return err('VLAN 1 is the default VLAN and cannot be deleted.');
                if (!S.vlans[v]) continue;
                var used = [];
                for (var n = 1; n <= NPORT; n++) { var p = S.ports[n]; if (!p.lag && !p.routing && ((p.mode === 'access' && p.access === v) || (p.mode === 'trunk' && p.native === v))) used.push(n); }
                if (used.length) return err('VLAN ' + v + ' is in use on interface ' + cPorts(used) + '. Remove it from the interface first.');
            }
            ids.forEach(function (v) {
                delete S.vlans[v];
                for (var n = 1; n <= NPORT; n++) { var p = S.ports[n]; if (Array.isArray(p.allowed)) p.allowed = p.allowed.filter(function (x) { return x !== v; }); }
            });
        }),
        D('interface vlan <VLAN-ID>', function (a) {
            var v = +a[2];
            if (!S.svis[v]) S.svis[v] = { ip: '', admin: true, desc: '', ospf: null };
            mode = { name: 'svi', svi: v };
        }),
        D('no interface vlan <VLAN-ID>', function (a) { delete S.svis[+a[3]]; }),
        D('interface lag <LAG-ID>', function (a) { var id = +a[2]; if (!S.lags[id]) S.lags[id] = newLag(); mode = { name: 'lag', lag: id }; }),
        D('no interface lag <LAG-ID>', function (a) {
            var id = +a[3]; delete S.lags[id];
            for (var n = 1; n <= NPORT; n++) if (S.ports[n].lag === id) S.ports[n].lag = 0;
        }),
        D('interface <IFNAME>', function (a) { mode = { name: 'if', ports: parseIf(a[1]) }; }),
        D('spanning-tree', function () {}),
        D('spanning-tree mode mstp', function () { S.stp.mode = 'mstp'; }),
        D('spanning-tree mode rpvst', function () { S.stp.mode = 'rpvst'; }),
        D('spanning-tree priority <PRIO>', function (a) { S.stp.prio = +a[2]; ev('LOG_INFO', 'mstpd', 2002, 'Bridge priority changed to ' + (+a[2] * 4096)); }),
        D('no spanning-tree priority', function () { S.stp.prio = 8; }),
        D('user <WORD> group administrators password plaintext <WORD>', function (a) { addUser(a, 'administrators'); }),
        D('user <WORD> group operators password plaintext <WORD>', function (a) { addUser(a, 'operators'); }),
        D('user <WORD> group auditors password plaintext <WORD>', function (a) { addUser(a, 'auditors'); }),
        D('no user <WORD>', function (a) { if (!S.sys.users[a[2]]) return err('User ' + a[2] + ' does not exist.'); delete S.sys.users[a[2]]; }),
        D('ssh server vrf default', function () { uniqAdd(S.sys.ssh, 'default'); }),
        D('ssh server vrf mgmt', function () { uniqAdd(S.sys.ssh, 'mgmt'); }),
        D('no ssh server vrf default', function () { del(S.sys.ssh, 'default'); }),
        D('no ssh server vrf mgmt', function () { del(S.sys.ssh, 'mgmt'); }),
        D('ntp server <IP>', function (a) { uniqAdd(S.sys.ntp, a[2]); }),
        D('ntp server <IP> iburst', function (a) { uniqAdd(S.sys.ntp, a[2]); }),
        D('no ntp server <IP>', function (a) { del(S.sys.ntp, a[3]); }),
        D('ntp enable', function () { S.sys.ntpOn = true; }),
        D('no ntp enable', function () { S.sys.ntpOn = false; }),
        D('clock timezone <WORD>', function (a) { S.sys.tz = a[2].toLowerCase(); }),
        D('no clock timezone', function () { S.sys.tz = ''; }),
        D('snmp-server community <WORD>', function (a) { uniqAdd(S.sys.snmp, a[2]); }),
        D('no snmp-server community <WORD>', function (a) { del(S.sys.snmp, a[3]); }),
        D('snmp-server vrf default', function () { uniqAdd(S.sys.snmpVrf, 'default'); }),
        D('snmp-server vrf mgmt', function () { uniqAdd(S.sys.snmpVrf, 'mgmt'); }),
        D('logging <IP>', function (a) { uniqAdd(S.sys.logging, a[1]); }),
        D('no logging <IP>', function (a) { del(S.sys.logging, a[2]); }),
        D('ip route <IP/MASK> <IP>', function (a) {
            if (!S.routes.some(function (r) { return r.prefix === a[2] && r.nh === a[3]; })) S.routes.push({ prefix: a[2], nh: a[3] });
        }),
        D('no ip route <IP/MASK> <IP>', function (a) { S.routes = S.routes.filter(function (r) { return !(r.prefix === a[3] && r.nh === a[4]); }); }),
        D('router ospf <PID>', function (a) { var p = +a[2]; if (!S.ospf) S.ospf = { pid: p, rid: '', areas: [] }; else if (S.ospf.pid !== p) return err('Only one OSPF process is supported in this lab (process ' + S.ospf.pid + ').'); mode = { name: 'ospf', pid: p }; }),
        D('no router ospf <PID>', function (a) { if (S.ospf && S.ospf.pid === +a[3]) S.ospf = null; })
    ];
    var VLANM = [
        D('name <WORD>', function (a) {
            if (a[1].length > 32) return err('VLAN name must be at most 32 characters.');
            mode.vlans.forEach(function (v) { S.vlans[v].name = a[1]; });
        }),
        D('no name', function () { mode.vlans.forEach(function (v) { S.vlans[v].name = v === 1 ? 'DEFAULT_VLAN_1' : 'VLAN' + v; }); }),
        D('description <LINE>', function (a) { mode.vlans.forEach(function (v) { S.vlans[v].desc = a.slice(1).join(' '); }); }),
        D('no description', function () { mode.vlans.forEach(function (v) { S.vlans[v].desc = ''; }); }),
        D('shutdown', function () { mode.vlans.forEach(function (v) { S.vlans[v].admin = false; }); }),
        D('no shutdown', function () { mode.vlans.forEach(function (v) { S.vlans[v].admin = true; }); })
    ];
    function setAdmin(on) {
        forT(function (o, name, n) {
            if (o.admin === on) return;
            o.admin = on;
            ev('LOG_INFO', 'intfd', on ? 403 : 404, 'Interface ' + name + ' admin state changed to ' + (on ? 'up' : 'down') + ' by user admin');
            if (n && CONN[pn(n)]) ev(on ? 'LOG_INFO' : 'LOG_WARN', 'intfd', on ? 401 : 402, 'Link status for interface ' + name + ' is ' + (on ? 'up' : 'down'));
        });
    }
    // คำสั่งที่ใช้ได้ทั้ง interface ธรรมดาและ interface lag
    var L2CMDS = [
        D('shutdown', function () { setAdmin(false); }),
        D('no shutdown', function () { setAdmin(true); }),
        D('description <LINE>', function (a) { var t = a.slice(1).join(' '); forT(function (o) { o.desc = t; }); }),
        D('no description', function () { forT(function (o) { o.desc = ''; }); }),
        D('vlan access <VLAN-ID>', function (a) {
            var v = +a[2], e = needVlan(v); if (e) return err(e);
            forT(function (o, name) { var g = l2guard(o, name); if (g) return g; o.mode = 'access'; o.access = v; o.native = 1; o.allowed = 'all'; });
        }),
        D('no vlan access', function () { forT(function (o) { if (o.mode === 'access') o.access = 1; }); }),
        D('vlan trunk native <VLAN-ID>', function (a) {
            var v = +a[3], e = needVlan(v); if (e) return err(e);
            forT(function (o, name) { var g = l2guard(o, name); if (g) return g; if (o.mode !== 'trunk') { o.mode = 'trunk'; o.allowed = 'all'; } o.native = v; });
        }),
        D('no vlan trunk native', function () { forT(function (o) { o.native = 1; trunkCleanup(o); }); }),
        D('vlan trunk allowed all', function () {
            forT(function (o, name) { var g = l2guard(o, name); if (g) return g; if (o.mode !== 'trunk') { o.mode = 'trunk'; o.native = 1; } o.allowed = 'all'; });
        }),
        D('vlan trunk allowed <VLAN-LIST>', function (a) {
            var ids = parseVlans(a[3]);
            for (var k = 0; k < ids.length; k++) { var e = needVlan(ids[k]); if (e) return err(e); }
            forT(function (o, name) {
                var g = l2guard(o, name); if (g) return g;
                if (o.mode !== 'trunk') { o.mode = 'trunk'; o.native = 1; o.allowed = []; }
                if (o.allowed === 'all') o.allowed = [];
                o.allowed = uniqSort(o.allowed.concat(ids));
            });
        }),
        D('no vlan trunk allowed <VLAN-LIST>', function (a) {
            var ids = parseVlans(a[4]);
            forT(function (o) {
                if (o.mode !== 'trunk') return;
                if (o.allowed === 'all') o.allowed = vlanIds();
                o.allowed = o.allowed.filter(function (x) { return ids.indexOf(x) < 0; });
                trunkCleanup(o);
            });
        }),
        D('no vlan trunk allowed', function () { forT(function (o) { if (o.mode === 'trunk') { o.allowed = []; trunkCleanup(o); } }); }),
        D('routing', function () { forT(function (o, name) { if (o.lag) return 'Interface ' + name + ' is a member of lag' + o.lag + '.'; o.routing = true; o.mode = 'access'; o.access = 1; o.native = 1; o.allowed = 'all'; }); }),
        D('no routing', function () { forT(function (o) { o.routing = false; o.ip = ''; o.ospf = null; }); }),
        D('ip address <IP/MASK>', function (a) {
            var t = targets(); if (t.length > 1) return err('IP address can be configured on a single interface only.');
            forT(function (o, name) { if (!o.routing) return 'Interface ' + name + ' is not an L3 interface. Configure "routing" first.'; o.ip = a[2]; });
        }),
        D('no ip address', function () { forT(function (o) { o.ip = ''; }); }),
        D('ip ospf <PID> area <AREA>', function (a) {
            forT(function (o, name) { if (!o.routing) return 'Interface ' + name + ' is not an L3 interface. Configure "routing" first.'; o.ospf = a[2] + '|' + normArea(a[4]); });
        }),
        D('no ip ospf <PID> area <AREA>', function () { forT(function (o) { o.ospf = null; }); })
    ];
    var IFM = L2CMDS.concat([
        D('lag <LAG-ID>', function (a) {
            var id = +a[1]; if (!S.lags[id]) return err('lag' + id + ' does not exist. Create it first using "interface lag ' + id + '".');
            forT(function (o, name) { if (o.routing) return 'Interface ' + name + ' is a routed (L3) interface. Use "no routing" first.'; o.lag = id; o.mode = 'access'; o.access = 1; o.allowed = 'all'; });
        }),
        D('no lag <LAG-ID>', function () { forT(function (o) { o.lag = 0; }); }),
        D('spanning-tree port-type admin-edge', function () { forT(function (o) { o.edge = true; }); }),
        D('no spanning-tree port-type', function () { forT(function (o) { o.edge = false; }); }),
        D('spanning-tree bpdu-guard', function () { forT(function (o) { o.bpdu = true; }); }),
        D('no spanning-tree bpdu-guard', function () { forT(function (o) { o.bpdu = false; }); })
    ]);
    var LAGM = L2CMDS.concat([
        D('lacp mode active', function () { S.lags[mode.lag].lacp = 'active'; }),
        D('lacp mode passive', function () { S.lags[mode.lag].lacp = 'passive'; }),
        D('no lacp mode', function () { S.lags[mode.lag].lacp = ''; })
    ]);
    var SVIM = [
        D('ip address <IP/MASK>', function (a) { S.svis[mode.svi].ip = a[2]; }),
        D('no ip address', function () { S.svis[mode.svi].ip = ''; }),
        D('description <LINE>', function (a) { S.svis[mode.svi].desc = a.slice(1).join(' '); }),
        D('no description', function () { S.svis[mode.svi].desc = ''; }),
        D('shutdown', function () { S.svis[mode.svi].admin = false; }),
        D('no shutdown', function () { S.svis[mode.svi].admin = true; }),
        D('ip ospf <PID> area <AREA>', function (a) { S.svis[mode.svi].ospf = a[2] + '|' + normArea(a[4]); }),
        D('no ip ospf <PID> area <AREA>', function () { S.svis[mode.svi].ospf = null; })
    ];
    var OSPFM = [
        D('router-id <IP>', function (a) { S.ospf.rid = a[1]; }),
        D('no router-id', function () { S.ospf.rid = ''; }),
        D('area <AREA>', function (a) { uniqAdd(S.ospf.areas, normArea(a[1])); }),
        D('no area <AREA>', function (a) { del(S.ospf.areas, normArea(a[2])); })
    ];
    var CONFIG_P = CONFIG.map(function (d) { return { w: d.w, run: d.run, parent: true }; });

    function defsFor(m) {
        switch (m) {
            case 'exec': return EXEC.concat(SHOW, COMMON);
            case 'config': return CONFIG.concat(SHOW, COMMON);
            case 'vlan': return VLANM.concat(SHOW, COMMON, CONFIG_P);
            case 'if': return IFM.concat(SHOW, COMMON, CONFIG_P);
            case 'lag': return LAGM.concat(SHOW, COMMON, CONFIG_P);
            case 'svi': return SVIM.concat(SHOW, COMMON, CONFIG_P);
            case 'ospf': return OSPFM.concat(SHOW, COMMON, CONFIG_P);
        }
        return [];
    }

    // ---------- parser ----------
    // ไล่จับคำทีละตำแหน่ง: คำสั่ง (keyword) ใช้คำย่อได้ · ตรงเป๊ะมาก่อน · ย่อแล้วตรงหลายคำ = ambiguous
    function walk(defs, toks) {
        var alive = defs.slice(), args = toks.slice();
        for (var i = 0; i < toks.length; i++) {
            var t = toks[i], tl = t.toLowerCase(), kw = [], next = [];
            for (var k = 0; k < alive.length; k++) {
                var w = alive[k].w[i];
                if (w === undefined) continue;
                if (isParam(w)) { if (PARAM[w](t)) next.push(alive[k]); }
                else if (w.indexOf(tl) === 0) { next.push(alive[k]); if (kw.indexOf(w) < 0) kw.push(w); }
            }
            if (kw.length) {
                var pick = kw.indexOf(tl) >= 0 ? tl : (kw.length === 1 ? kw[0] : null);
                if (!pick) return { error: 'ambiguous', pos: i };
                next = next.filter(function (d) { return d.w[i] === pick; });
                args[i] = pick;
            }
            if (!next.length) return { error: 'invalid', pos: i };
            var line = next.filter(function (d) { return d.w[i] === '<LINE>'; });
            if (line.length) return { line: line[0], args: args, alive: [] };
            alive = next;
        }
        return { alive: alive, args: args };
    }
    function resolve(defs, toks) {
        var r = walk(defs, toks);
        if (r.error) return r;
        if (r.line) return { def: r.line, args: r.args };
        var full = r.alive.filter(function (d) { return d.w.length === toks.length; });
        if (full.length) return { def: full[0], args: r.args };
        return { error: 'incomplete', pos: toks.length };
    }
    function tokens(s) { s = s.trim(); return s ? s.split(/\s+/) : []; }

    function execLine(raw) {
        var toks = tokens(raw);
        lastExec = { raw: raw.trim(), err: '' };
        if (!toks.length) return;
        if (toks[0].charAt(0) === '!') return;
        var m = mode.name, defs = defsFor(m);
        if (m !== 'exec' && toks[0].toLowerCase() === 'do') { toks = toks.slice(1); defs = EXEC.concat(SHOW); if (!toks.length) return err('Incomplete command.'); }
        var r = resolve(defs, toks);
        lastExec.code = r.error || '';
        if (r.error === 'invalid') return err('Invalid input: ' + toks[r.pos]);
        if (r.error === 'ambiguous') return err('Ambiguous command: ' + toks[r.pos]);
        if (r.error === 'incomplete') return err('Incomplete command.');
        if (r.def.parent) m = 'config';
        if (r.def.parent) mode = { name: 'config' };
        cmdFailed = false;
        r.def.run(r.args);
        var full = r.args.slice(0, r.def.w.length).join(' ');
        lastExec.full = full; lastExec.meaning = meaningOf(r.def, m, r.args); lastExec.ok = !cmdFailed;
        if (!cmdFailed && S.ran.indexOf(full) < 0) S.ran.push(full);
    }
    // แปลคำสั่ง (เช่นในเฉลย) โดยไม่รัน: หาโหมดที่คำสั่งนี้อยู่ แล้วคืนรูปเต็ม + ความหมาย
    var OWN = { exec: function () { return EXEC.concat(SHOW, COMMON); }, config: function () { return CONFIG; }, 'if': function () { return IFM; },
        lag: function () { return LAGM; }, vlan: function () { return VLANM; }, svi: function () { return SVIM; }, ospf: function () { return OSPFM; } };
    function explainCmd(line, prefer) {
        var toks = tokens(line); if (!toks.length) return null;
        var order = [prefer || mode.name, 'exec', 'config', 'if', 'lag', 'vlan', 'svi', 'ospf'];
        for (var i = 0; i < order.length; i++) {
            var mm = order[i], r = resolve(OWN[mm](), toks);
            if (r.error) continue;
            var anyMode = SHOW.indexOf(r.def) >= 0 || COMMON.indexOf(r.def) >= 0;
            return { full: r.args.slice(0, r.def.w.length).join(' '), mode: anyMode ? '' : mm, meaning: meaningOf(r.def, mm, r.args) };
        }
        return null;
    }

    function helpFor(text) {
        var trailing = /\s$/.test(text) || text === '';
        var toks = tokens(text), defs = defsFor(mode.name);
        if (mode.name !== 'exec' && toks[0] && toks[0].toLowerCase() === 'do') { toks = toks.slice(1); defs = EXEC.concat(SHOW); }
        var partial = trailing ? '' : toks.pop() || '';
        var r = walk(defs, toks), pos = toks.length, seen = {}, items = [], cr = false;
        if (r.line) return { items: [], cr: true, partial: '', toks: toks };
        var alive = r.error ? [] : r.alive;
        // help แสดงเฉพาะคำสั่งของโหมดปัจจุบัน (คำสั่งโหมด config ยังพิมพ์ได้ แต่ไม่ขึ้นใน ?)
        var own = alive.filter(function (d) { return !d.parent; });
        if (own.length) alive = own;
        alive.forEach(function (d) {
            var w = d.w[pos];
            if (w === undefined) { cr = true; return; }
            if (!isParam(w) && w.indexOf(partial.toLowerCase()) !== 0) return;
            if (isParam(w) && partial && !PARAM[w](partial)) return;
            if (!seen[w]) { seen[w] = 1; items.push(w); }
        });
        return { items: items, cr: cr && !partial, partial: partial, toks: toks };
    }

    // ---------- terminal UI ----------
    var hIdx = -1;
    function refreshPrompt() { promptEl.textContent = prompt(); }
    function submit(line) {
        print(prompt() + line);
        if (line.trim()) { hist.push(line); if (hist.length > 500) hist.shift(); }
        var pm = mode.name;   // โหมดก่อนรันคำสั่ง (ให้ Kafra รู้ว่าออกจากโหมดไหนมา)
        execLine(line);
        hIdx = -1;
        refreshPrompt();
        if (line.trim()) Kafra.exec(pm);
        afterChange();
    }
    inEl.addEventListener('keydown', function (e) {
        var v = inEl.value;
        if (e.key === 'Enter') { e.preventDefault(); inEl.value = ''; submit(v); }
        else if (e.key === '?') {
            e.preventDefault();
            print(prompt() + v + '?');
            var h = helpFor(v), o = [];
            if (!h.items.length && !h.cr) o.push('Invalid input: ' + (h.partial || v.trim().split(/\s+/).pop()));
            h.items.forEach(function (w) { o.push('  ' + pad(helpLabel(w), 26) + helpText(w)); });
            if (h.cr) o.push('  <cr>');
            print(o);
        }
        else if (e.key === 'Tab') {
            e.preventDefault();
            var h2 = helpFor(v);
            var kws = h2.items.filter(function (w) { return !isParam(w); });
            if (h2.partial && kws.length === 1) inEl.value = h2.toks.concat(kws[0]).join(' ') + ' ';
            else if (h2.partial && kws.length > 1) {
                var c = kws.reduce(function (a, b) { var i = 0; while (i < a.length && a[i] === b[i]) i++; return a.slice(0, i); });
                if (c.length > h2.partial.length) inEl.value = h2.toks.concat(c).join(' ');
                else { print(prompt() + v); print(kws.join('  ')); }
            }
        }
        else if (e.key === 'ArrowUp') {
            e.preventDefault(); if (!hist.length) return;
            hIdx = hIdx < 0 ? hist.length - 1 : Math.max(0, hIdx - 1); inEl.value = hist[hIdx];
        }
        else if (e.key === 'ArrowDown') {
            e.preventDefault(); if (hIdx < 0) return;
            hIdx++; if (hIdx >= hist.length) { hIdx = -1; inEl.value = ''; } else inEl.value = hist[hIdx];
        }
        else if (e.ctrlKey && (e.key === 'z' || e.key === 'Z')) { e.preventDefault(); print(prompt() + v + '^Z'); inEl.value = ''; mode = { name: 'exec' }; refreshPrompt(); }
        else if (e.ctrlKey && (e.key === 'c' || e.key === 'C') && !window.getSelection().toString()) { e.preventDefault(); print(prompt() + v + '^C'); inEl.value = ''; }
        else if (e.ctrlKey && (e.key === 'l' || e.key === 'L')) { e.preventDefault(); outEl.innerHTML = ''; }
    });
    inEl.addEventListener('paste', function (e) {
        var t = (e.clipboardData || window.clipboardData).getData('text');
        if (t.indexOf('\n') < 0) return;
        e.preventDefault();
        var lines = (inEl.value + t).replace(/\r/g, '').split('\n');
        var last = lines.pop();
        lines.forEach(function (l) { submit(l); });
        inEl.value = last;
    });
    termEl.addEventListener('mouseup', function () { if (!window.getSelection().toString()) inEl.focus(); });

    // ---------- front panel ----------
    var PALETTE = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#a855f7', '#ec4899', '#14b8a6', '#eab308'];
    function vlanColor(v) {
        if (v === 1) return '#64748b';
        var ids = vlanIds().filter(function (x) { return x !== 1; });
        var i = ids.indexOf(v);
        return i < 0 ? '#64748b' : PALETTE[i % PALETTE.length];
    }
    function renderPanel() {
        var panel = document.getElementById('swPanel');
        document.getElementById('swHost').textContent = S.hostname;
        function portHtml(n, bottom) {
            var p = S.ports[n], up = fwd(n), x = eff(n) || p;
            var cls = 'port' + (bottom ? ' bot' : '') + (n >= SFP ? ' sfp' : '') + (!p.admin ? ' off' : (up ? ' up' : ' down'));
            var color = p.lag ? '#fb923c' : x.routing ? '#e2e8f0' : (x.mode === 'access' ? vlanColor(x.access) : '#c084fc');
            var mark = p.lag ? 'L' : x.routing ? 'R' : (x.mode === 'trunk' ? 'T' : '');
            var tip = pn(n) + (CONN[pn(n)] ? ' → ' + CONN[pn(n)] : ' (ว่าง)') + '\n' +
                (p.lag ? 'member of lag' + p.lag + (bundled(n) ? ' (in sync)' : ' (not in sync)') :
                    x.routing ? 'routed ' + (x.ip || '') : x.mode === 'access' ? 'access VLAN ' + x.access :
                    'trunk native ' + x.native + ' allowed ' + (x.allowed === 'all' ? 'all' : cVlans(x.allowed) || 'none')) +
                '\n' + (!p.admin ? 'shutdown' : up ? 'up' : linkUp(n) ? 'up (ยังไม่ส่งข้อมูล)' : 'down (ไม่มีสายเชื่อมต่อ)') + (p.desc ? '\n"' + p.desc + '"' : '');
            return '<div class="' + cls + '" data-n="' + n + '" title="' + tip.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;') + '">' +
                '<div class="num">' + n + '</div><div class="jack" style="--vc:' + color + '">' + mark + '</div><div class="led"></div></div>';
        }
        var a = '', b = '', n;
        for (n = 1; n < SPLIT; n += 2) a += portHtml(n, false) + (n + 1 < SPLIT ? portHtml(n + 1, true) : '');
        for (n = SPLIT; n <= NPORT; n += 2) b += portHtml(n, false) + (n + 1 <= NPORT ? portHtml(n + 1, true) : '');
        panel.innerHTML = '<div class="sw-grp">' + a + '</div><div class="sw-sep"></div><div class="sw-grp">' + b + '</div>';
        var lg = vlanIds().map(function (v) { return '<span><i style="border-color:' + vlanColor(v) + '"></i>VLAN ' + v + ' ' + S.vlans[v].name.replace(/</g, '&lt;') + '</span>'; });
        lg.push('<span><i style="border-color:#c084fc"></i>Trunk (T)</span>');
        if (lagIds().length) lg.push('<span><i style="border-color:#fb923c"></i>LAG member (L)</span>');
        lg.push('<span><i class="dot" style="background:#22c55e"></i>link up</span>');
        lg.push('<span><i class="dot" style="background:#f59e0b"></i>shutdown</span>');
        document.getElementById('swLegend').innerHTML = lg.join('');
    }
    document.getElementById('swPanel').addEventListener('click', function (e) {
        var p = e.target.closest('.port'); if (!p) return;
        inEl.value = 'interface ' + pn(+p.dataset.n); inEl.focus();
    });

    // ---------- checker ----------
    function portsOf(s) { return parseIf(s) || []; }
    function objOf(name) { return /^lag/.test(name) ? S.lags[+name.slice(3)] : S.ports[portsOf(name)[0]]; }
    function nums(s) { return (String(s).match(/\d+(?:\.\d+)?/g) || []).map(Number); }
    function norm(s) { return String(s).trim().toLowerCase().replace(/\s+/g, ' ').replace(/\s*%$/, ''); }
    function answerOk(c, ans) {
        if (ans === undefined || ans === '') return false;
        var ex = [].concat(c.expect);
        if (c.mode === 'nums' || c.mode === 'set') {
            var a = nums(ans);
            return ex.some(function (e) {
                var b = nums(e); if (a.length !== b.length) return false;
                var x = a, y = b;
                if (c.mode === 'set') { x = a.slice().sort(); y = b.slice().sort(); }
                return x.every(function (v, i) { return v === y[i]; });
            });
        }
        return ex.some(function (e) { return norm(e) === norm(ans); });
    }
    function cfgHas(c) {
        var lines = runCfg(), heads = [null];
        if (c.under) {
            var m = /^interface (\S+)$/.exec(c.under), ps = m && parseIf(m[1]);
            heads = ps ? ps.map(function (n) { return 'interface ' + pn(n); }) : [c.under];
        }
        var want = c.line.toLowerCase();
        function has(l) { l = l.trim().toLowerCase(); return c.prefix ? l.indexOf(want) === 0 : l === want; }
        var miss = heads.filter(function (h) {
            if (h === null) return !lines.some(function (l) { return !/^\s/.test(l) && has(l); });
            var i = lines.indexOf(h); if (i < 0) return true;
            for (var k = i + 1; k < lines.length && /^\s/.test(lines[k]); k++) if (has(lines[k])) return false;
            return true;
        });
        if (!miss.length) return '';
        return 'ยังไม่มี "' + c.line + (c.prefix ? '…' : '') + '"' + (c.under ? ' ใต้ ' + (miss.length > 1 ? miss.length + ' interface (เช่น ' + miss[0] + ')' : miss[0]) : ' ใน config');
    }
    function check(c, ti) {
        var p, bad;
        switch (c.type) {
            case 'hostname':
                return S.hostname === c.value ? '' : 'ชื่อเครื่องตอนนี้คือ "' + S.hostname + '" (ต้องเป็น ' + c.value + ')';
            case 'vlan':
                if (!S.vlans[c.id]) return 'ยังไม่มี VLAN ' + c.id;
                if (c.name && S.vlans[c.id].name !== c.name) return 'VLAN ' + c.id + ' ชื่อ "' + S.vlans[c.id].name + '" (ต้องเป็น ' + c.name + ')';
                return '';
            case 'access':
                bad = portsOf(c.ports).filter(function (n) { var x = eff(n); return !x || S.ports[n].lag || x.routing || x.mode !== 'access' || x.access !== c.vlan; });
                return bad.length ? 'port ' + cPorts(bad) + ' ยังไม่เป็น access VLAN ' + c.vlan : '';
            case 'trunk':
                p = objOf(c.port);
                if (!p || p.routing || p.mode !== 'trunk' || (p.lag && !/^lag/.test(c.port))) return c.port + ' ยังไม่เป็น trunk';
                if (c.native && p.native !== c.native) return 'native VLAN ตอนนี้คือ ' + p.native + ' (ต้องเป็น ' + c.native + ')';
                if (p.allowed === 'all') return 'ยังอนุญาตทุก VLAN (all) ต้องระบุเฉพาะ ' + c.allowed.join(',');
                bad = c.allowed.filter(function (v) { return p.allowed.indexOf(v) < 0; });
                return bad.length ? 'ยังไม่ได้อนุญาต VLAN ' + bad.join(',') + ' บน ' + c.port : '';
            case 'shutdown':
                return S.ports[portsOf(c.port)[0]].admin ? 'port ' + c.port + ' ยังเปิดอยู่' : '';
            case 'linkup':
                return fwd(portsOf(c.port)[0]) ? '' : 'port ' + c.port + ' ยัง down อยู่';
            case 'description':
                p = S.ports[portsOf(c.port)[0]];
                return (p.desc || '').trim().toLowerCase() === c.text.toLowerCase() ? '' : 'description ของ ' + c.port + ' ยังไม่ใช่ "' + c.text + '"';
            case 'svi':
                if (!S.svis[c.vlan]) return 'ยังไม่ได้สร้าง interface vlan ' + c.vlan;
                if (S.svis[c.vlan].ip !== c.ip) return 'IP ของ vlan ' + c.vlan + ' ยังไม่ใช่ ' + c.ip;
                return c.up && !sviUp(c.vlan) ? 'interface vlan ' + c.vlan + ' ยัง down อยู่' : '';
            case 'routed':
                p = S.ports[portsOf(c.port)[0]];
                return p.routing && p.ip === c.ip ? '' : c.port + ' ยังไม่เป็น routed port ที่มี IP ' + c.ip;
            case 'saved':
                return savedNow() ? '' : (startup ? 'มีการแก้ config หลังบันทึกครั้งล่าสุด ให้ write memory อีกครั้ง' : 'ยังไม่ได้บันทึก config (write memory)');
            case 'ran':
                return S.ran.some(function (x) { return x.indexOf(c.cmd) === 0; }) ? '' : 'ยังไม่ได้รันคำสั่ง ' + c.cmd;
            case 'cfg':
                return cfgHas(c);
            case 'lag':
                if (!S.lags[c.id]) return 'ยังไม่ได้สร้าง interface lag ' + c.id;
                if (!S.lags[c.id].admin) return 'lag' + c.id + ' ยัง shutdown อยู่';
                if (c.lacp && S.lags[c.id].lacp !== c.lacp) return 'lag' + c.id + ' ยังไม่ได้ตั้ง lacp mode ' + c.lacp;
                bad = portsOf(c.members).filter(function (n) { return S.ports[n].lag !== c.id; });
                if (bad.length) return 'port ' + cPorts(bad) + ' ยังไม่ได้เป็นสมาชิก lag' + c.id;
                bad = portsOf(c.members).filter(function (n) { return !bundled(n); });
                return bad.length ? 'port ' + cPorts(bad) + ' ยังไม่ in sync กับอีกฝั่ง (ดู show lacp interfaces)' : '';
            case 'stproot':
                return stpView().root ? '' : 'เครื่องนี้ยังไม่ใช่ root bridge (root คือ priority ' + stpView().rootPriority + ')';
            case 'ospf':
                return ospfState() ? '' : 'OSPF neighbor ยังไม่ขึ้น FULL (ดู show ip ospf neighbors)';
            case 'route':
                return routeTable().some(function (r) { return r.prefix === c.prefix && (!c.origin || r.o === c.origin); }) ? '' :
                    'ยังไม่มี route ' + c.prefix + (c.origin ? ' (origin ' + c.origin + ')' : '') + ' ในตาราง';
            case 'ping':
                return reach(c.ip).ok ? '' : 'ยัง ping ' + c.ip + ' ไม่ผ่าน';
            case 'ntpsync':
                return S.sys.ntpOn && S.sys.ntp.some(function (ip) { return (PEER.ntp || []).indexOf(ip) >= 0 && reach(ip).ok; }) ? '' : 'NTP ยังไม่ sync (ดู show ntp status)';
            case 'answer':
                if (answers[ti] === undefined || answers[ti] === '') return 'ยังไม่ได้ตอบ';
                return answerOk(c, answers[ti]) ? '' : 'คำตอบ "' + answers[ti] + '" ยังไม่ถูก ลองอ่านผลคำสั่งอีกครั้ง';
        }
        return '';
    }
    function taskWhy(t, ti) { for (var k = 0; k < t.checks.length; k++) { var m = check(t.checks[k], ti); if (m) return m; } return ''; }
    var taskEls = Array.prototype.slice.call(document.querySelectorAll('.lab-task'));
    function updateTasks(showWhy) {
        done = [];
        var cur = -1;
        L.tasks.forEach(function (t, i) {
            var why = taskWhy(t, i), el = taskEls[i];
            el.classList.toggle('ok', !why);
            if (!why) done.push(i); else if (cur < 0) cur = i;
            if (showWhy === true || showWhy === i) el.querySelector('.why').textContent = why;
            else if (!why) el.querySelector('.why').textContent = '';
        });
        taskEls.forEach(function (el, i) { el.classList.toggle('cur', i === cur); });
        var curEl = document.getElementById('labCur');
        if (curEl) curEl.textContent = cur < 0 ? '✓ ทำครบทุกข้อแล้ว' : '▶ ข้อ ' + (cur + 1) + ' ' + L.tasks[cur].title + ': ' + L.tasks[cur].detail;
        document.getElementById('labCount').textContent = '(' + done.length + '/' + L.tasks.length + ')';
        document.getElementById('labBanner').classList.toggle('on', done.length === L.tasks.length);
    }
    function afterChange() { renderPanel(); updateTasks(false); save(); Kafra.state(); }

    taskEls.forEach(function (el, i) {
        el.querySelector('.lab-hint-btn').addEventListener('click', function () {
            var on = el.classList.toggle('show-hint');
            this.textContent = on ? 'ซ่อนเฉลย' : 'ดูเฉลย';
        });
        var ask = el.querySelector('.lab-ask');
        if (!ask) return;
        var inp = ask.querySelector('input');
        function send() { answers[i] = inp.value.trim(); updateTasks(i); save(); Kafra.state(); }
        ask.querySelector('button').addEventListener('click', send);
        inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); send(); } });
    });
    function fillAnswers() {
        taskEls.forEach(function (el, i) { var inp = el.querySelector('.lab-ask input'); if (inp) inp.value = answers[i] || ''; });
    }
    document.getElementById('labCheck').addEventListener('click', function () { updateTasks(true); });
    // เรียนใหม่ = ล้างแล้ว Kafra สอนทีละข้อ · เริ่มใหม่ = ล้างแล้วทำแบบสอบ (ไม่มีสอน ไม่มีเฉลย)
    function showStudy() {
        document.body.classList.toggle('lab-exam', studyMode === 'exam');
        var t = document.getElementById('labMode');
        if (t) t.textContent = studyMode === 'exam' ? 'โหมดสอบ: ทำเอง ไม่มีสอน ไม่มีเฉลย' : 'โหมดเรียน: Kafra สอนทีละข้อ';
    }
    function restart(m, ask) {
        if (!confirm(ask)) return;
        reset(); studyMode = m; mode = { name: 'exec' };
        outEl.innerHTML = ''; banner(); refreshPrompt(); fillAnswers(); afterChange();
        taskEls.forEach(function (el) { el.querySelector('.why').textContent = ''; el.classList.remove('show-hint'); var hb = el.querySelector('.lab-hint-btn'); if (hb) hb.textContent = 'ดูเฉลย'; });
        showStudy(); save();
        Kafra.start(false);
        if (m === 'exam') inEl.focus();
    }
    document.getElementById('labLearn').addEventListener('click', function () { restart('learn', 'ล้างทุกอย่างแล้วเรียนใหม่ โดยให้ Kafra สอนทีละข้อ?'); });
    document.getElementById('labReset').addEventListener('click', function () { restart('exam', 'ล้างทุกอย่างแล้วเริ่มทำแบบสอบ (ไม่มีสอน ไม่มีเฉลย)?'); });

    // ---------- Kafra: ครูสอนทีละข้อ (มุมขวาล่าง) ----------
    // แต่ละข้อ = แนวคิด (lesson.teach[i] หรือ detail) → คำสั่งในเฉลยทีละคำสั่งพร้อมความหมาย → (กรอกคำตอบ)
    // พิมพ์คำสั่งตรงกับขั้นที่สอน = ชม + ไปขั้นถัดไป · พิมพ์คำสั่งอื่น = อธิบายคำสั่งนั้น · error = บอกวิธีแก้ · ข้อผ่าน = ชม + ไปข้อถัดไป
    var Kafra = (function () {
        var root = document.getElementById('kf');
        if (!root) return { exec: function () {}, state: function () {}, start: function () {}, teach: function () {} };
        var say = root.querySelector('.kf-say'), girl = root.querySelector('.kf-girl'), mouth = girl.querySelector('.kf-mouth'),
            body = root.querySelector('.kf-body'), bPrev = root.querySelector('[data-kf=prev]'), bPut = { hidden: true }, bNext = root.querySelector('[data-kf=next]');
        var quiet = matchMedia('(prefers-reduced-motion: reduce)').matches;
        var run = 0, ti = 0, si = 0, steps = [], lastDone = [], timer = null;
        var TEACH = L.teach || [];
        function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
        function talk(on) { girl.classList.toggle('talk', on); if (!on) mouth.style.setProperty('--o', 0.15); }
        function add(tag, cls, text, parent) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return (parent || body).appendChild(e); }
        function code(text, parent) { return add('code', 'kf-code', text, parent); }
        function firstOpen() { for (var i = 0; i < L.tasks.length; i++) if (done.indexOf(i) < 0) return i; return -1; }
        function nextMode(m, full) {
            if (/^configure/.test(full)) return 'config';
            if (full === 'end') return 'exec';
            if (full === 'exit') return m === 'config' ? 'exec' : (m === 'exec' ? 'exec' : 'config');
            if (/^interface vlan /.test(full)) return 'svi';
            if (/^interface lag /.test(full)) return 'lag';
            if (/^interface /.test(full)) return 'if';
            if (/^vlan \d/.test(full) && (m === 'config' || m === 'vlan' || m === 'if' || m === 'lag' || m === 'svi')) return 'vlan';
            if (/^router ospf /.test(full)) return 'ospf';
            return m;
        }
        function build(i) {
            var t = L.tasks[i], s = [{ kind: 'concept' }], sim = 'exec';
            (t.hint || []).forEach(function (h) {
                var x = /[฀-๿]/.test(h) ? null : explainCmd(h, sim);
                if (x) { s.push({ kind: 'cmd', cmd: h, x: x }); sim = nextMode(x.mode || sim, x.full); }
                else s.push({ kind: 'note', text: h });
            });
            if (t.checks.some(function (c) { return c.type === 'answer'; })) s.push({ kind: 'answer' });
            return s;
        }
        function nCmds() { return steps.filter(function (x) { return x.kind === 'cmd'; }).length; }
        var speaking = false;
        function open() { if (say.hidden) { say.hidden = false; } if (document.activeElement === inEl) inEl.blur(); }
        function close() { say.hidden = true; run++; speaking = false; talk(false); inEl.focus(); }
        function render(pre, show) {
            if (show) open();
            body.replaceChildren();
            if (pre) pre();
            var t = L.tasks[ti], st = steps[si], k = steps.slice(0, si + 1).filter(function (x) { return x.kind === 'cmd'; }).length;
            if (ti < 0) {
                add('div', 'hi kf-t', 'ผ่านบทเรียนนี้ครบทุกข้อแล้วค่ะ ♪');
                addBenefits();
                add('div', 'kf-t kf-small', 'ลองกด "เริ่มใหม่ (สอบ)" ทำซ้ำโดยไม่มีสอน หรือไปบทถัดไปที่หน้า Lab ก็ได้นะคะ');
            } else if (st.kind === 'concept') {
                add('div', 'hi kf-t', 'ข้อ ' + (ti + 1) + ': ' + t.title);
                add('div', 'kf-t', TEACH[ti] || t.detail);
                if (TEACH[ti]) add('div', 'kf-t kf-task', 'โจทย์: ' + t.detail);
                add('div', 'kf-t kf-small', nCmds() ? 'ข้อนี้ใช้ ' + nCmds() + ' คำสั่ง กด "ถัดไป" แล้ว Kafra จะสอนทีละคำสั่งค่ะ' : 'ข้อนี้ไม่ต้องพิมพ์คำสั่ง กด "ถัดไป" ดูเคล็ดลับได้ค่ะ');
            } else if (st.kind === 'cmd') {
                add('div', 'hi kf-t', 'ข้อ ' + (ti + 1) + ' · คำสั่งที่ ' + k + '/' + nCmds());
                code(st.cmd);
                add('div', 'kf-t', st.x.meaning || 'คำสั่งนี้ใช้ในขั้นตอนของข้อนี้ค่ะ');
                add('div', 'kf-t kf-small', (st.x.mode ? 'พิมพ์ในโหมด ' + MODE_LABEL[st.x.mode] : 'ใช้ได้ทุกโหมด') + ' · กด Enter แล้วพิมพ์เองใน terminal นะคะ Kafra จะบอกว่าถูกหรือผิดค่ะ');
            } else if (st.kind === 'note') {
                add('div', 'hi kf-t', 'ข้อ ' + (ti + 1) + ' · เคล็ดลับ');
                add('div', 'kf-t', st.text);
            } else {
                add('div', 'hi kf-t', 'ข้อ ' + (ti + 1) + ' · กรอกคำตอบ');
                add('div', 'kf-t', 'อ่านผลจากคำสั่งแล้วกรอกคำตอบในช่องของข้อ ' + (ti + 1) + ' ทางซ้าย แล้วกด "ส่ง" นะคะ');
            }
            bPrev.disabled = ti < 0 || si === 0;
            bPut.hidden = !(st && st.kind === 'cmd');
            bNext.textContent = ti < 0 ? 'เริ่มใหม่' : (st && st.kind === 'cmd' ? 'ไปพิมพ์เอง ⌨' : si < steps.length - 1 ? 'ถัดไป ▶' : (ti < L.tasks.length - 1 ? 'ข้อถัดไป ▶' : 'จบ'));
            taskEls.forEach(function (e, i) { e.classList.toggle('kf-on', i === ti); });
            if (!say.hidden) speak();
        }
        async function speak() {
            var me = ++run, lines = Array.prototype.slice.call(body.querySelectorAll('.kf-t')).map(function (e) { return { el: e, text: e.textContent }; });
            if (quiet) return;
            speaking = true;
            lines.forEach(function (l) { l.el.dataset.full = l.text; l.el.textContent = ''; l.el.classList.add('wait'); });
            for (var n = 0; n < lines.length; n++) {
                var l = lines[n]; if (me !== run) return;
                l.el.classList.remove('wait'); l.el.classList.add('typing'); talk(true);
                var ch = Array.from(l.text);
                for (var i = 0; i < ch.length; i++) {
                    if (me !== run) { l.el.textContent = l.text; return; }
                    l.el.textContent += ch[i];
                    mouth.style.setProperty('--o', /[\s,.!?·♪]/.test(ch[i]) ? 0.15 : (i % 2 ? 0.35 : 0.65 + Math.random() * 0.35));
                    await sleep(/[\s,]/.test(ch[i]) ? 45 : 22);
                }
                l.el.classList.remove('typing'); talk(false);
                await sleep(260);
            }
            if (me === run) speaking = false;
        }
        function showAll() {
            run++; talk(false); speaking = false;
            body.querySelectorAll('.kf-t').forEach(function (e) { e.classList.remove('wait', 'typing'); if (e.dataset.full) e.textContent = e.dataset.full; });
        }
        function teach(i, step) {
            clearTimeout(timer);
            ti = i; si = step || 0; steps = ti < 0 ? [] : build(ti);
            render(null, true);
        }
        function go(d) {
            if (ti < 0) return si === -1 ? teach(-1) : teach(0);
            si += d;
            if (si < 0) si = 0;
            if (si >= steps.length) { if (ti < L.tasks.length - 1) return teach(ti + 1); si = steps.length - 1; }
            render(null, true);
        }
        // ขั้นที่เป็นคำสั่ง: ปิดกรอบให้ไปพิมพ์เองใน terminal (Kafra ไม่พิมพ์ให้ แค่บอกถูก/ผิด)
        function put() { close(); inEl.value = ''; inEl.focus(); }
        bPrev.addEventListener('click', function (e) { e.stopPropagation(); go(-1); });
        // ประกาศสั้นๆ (ใช้ในโหมดสอบ): ปุ่มขวา = ปิด
        var noticing = false;
        // สรุปประโยชน์ที่ได้จากบทนี้ (benefits ใน JSON ของบทเรียน) ตอนทำครบทุกข้อ
        function addBenefits() {
            var B = L.benefits || [];
            if (!B.length) return;
            add('div', 'kf-t kf-small', 'สรุปประโยชน์ที่เจ้านายได้จากบท "' + L.title + '" ค่ะ');
            B.forEach(function (b) { add('div', 'kf-t kf-ben', '✓ ' + b); });
        }
        function notice(title, text, extra) {
            clearTimeout(timer);
            noticing = true;
            body.replaceChildren();
            add('div', 'hi kf-t', title);
            add('div', 'kf-t', text);
            if (extra) extra();
            bPrev.disabled = true; bNext.textContent = 'ปิด ✕';
            taskEls.forEach(function (e) { e.classList.remove('kf-on'); });
            open(); speak();
        }
        var _render = render;
        render = function (pre, show) { noticing = false; _render(pre, show); };
        function examNote() {
            notice('โหมดสอบค่ะ', 'รอบนี้ Kafra จะไม่สอน ไม่บอกถูกผิดระหว่างทาง และไม่มีเฉลย ลองทำเองให้ครบนะคะ ข้อที่ผ่านจะติ๊กเขียวเอง ถ้าอยากเรียนแบบมีสอน กดปุ่ม "เรียนใหม่" ค่ะ');
        }
        bNext.addEventListener('click', function (e) {
            e.stopPropagation();
            if (noticing) return close();
            var st = steps[si];
            if (ti >= 0 && st && st.kind === 'cmd') return put();
            go(1);
        });
        say.addEventListener('click', function (e) { if (!e.target.closest('button')) showAll(); });
        root.querySelector('.kf-x').addEventListener('click', function (e) { e.stopPropagation(); close(); });
        girl.addEventListener('click', function () {
            if (!say.hidden) return close();
            if (studyMode === 'exam') return examNote();
            render(null, true);
        });
        // คีย์ลัดตอนกรอบเปิด: Enter = ข้ามการพิมพ์ / ถัดไป / ใส่คำสั่ง · Esc = ปิด · พิมพ์ตัวอักษร = ปิดแล้วพิมพ์ลง terminal
        document.addEventListener('keydown', function (e) {
            if (say.hidden || e.isComposing) return;
            var ae = document.activeElement;
            if (ae && ae.closest && ae.closest('.lab-ask')) return;     // กำลังพิมพ์คำตอบ
            if (e.key === 'Enter' && ae === inEl && inEl.value.trim()) return;   // มีคำสั่งรอในช่องพิมพ์ = ให้ terminal รัน
            if (e.key === 'Enter') {
                e.preventDefault(); e.stopPropagation();
                if (speaking) return showAll();
                if (noticing) return close();
                var st = steps[si];
                if (ti >= 0 && st && st.kind === 'cmd') return put();
                if (ti >= 0 && st && st.kind === 'answer') {
                    close();
                    var a = taskEls[ti].querySelector('.lab-ask input'); if (a) a.focus();
                    return;
                }
                return go(1);
            }
            if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); return close(); }
            if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && ae !== inEl) close();
        }, true);

        // คำสั่งที่ผลเหมือนกันนับว่าถูก (configure = configure terminal, copy running-config startup-config = write memory, ntp server x = ntp server x iburst)
        function canon(s) {
            s = s.toLowerCase().trim();
            if (s === 'configure') return 'configure terminal';
            if (s === 'copy running-config startup-config') return 'write memory';
            return s.replace(/^(ntp server \S+) iburst$/, '$1').replace(/^show logging/, 'show events');
        }
        function exec(pm) {
            if (studyMode === 'exam') return;   // โหมดสอบ: ไม่บอกถูกผิด
            var e = lastExec; if (!e || !e.raw || ti < 0) return;
            if (si < 0) { clearTimeout(timer); si = 0; }   // พิมพ์ต่อทันทีระหว่างหน้า "เก่งมากค่ะ" = เริ่มข้อใหม่เลย
            var st = steps[si];
            if (e.code === 'invalid' || e.code === 'incomplete' || e.code === 'ambiguous' || (e.full && !e.ok)) {
                var help = e.code === 'invalid' ? 'คำสั่งนี้พิมพ์ผิด หรือไม่มีในโหมดที่อยู่ตอนนี้ค่ะ กด ? เพื่อดูคำสั่งที่ใช้ได้นะคะ'
                    : e.code === 'incomplete' ? 'คำสั่งยังไม่ครบค่ะ พิมพ์ต่อแล้วเว้นวรรคกด ? เพื่อดูว่าต้องใส่อะไรต่อ'
                    : e.code === 'ambiguous' ? 'คำย่อสั้นไปจนตรงกับหลายคำสั่งค่ะ พิมพ์ให้ยาวขึ้นอีกนิดนะคะ'
                    : 'เครื่องไม่ยอมรับคำสั่งนี้ค่ะ อ่านข้อความสีแดงใน terminal ดูนะคะ';
                if (st && st.kind === 'cmd' && st.x.mode && st.x.mode !== mode.name && e.code === 'invalid') help += ' (คำสั่งของขั้นนี้ต้องพิมพ์ในโหมด ' + MODE_LABEL[st.x.mode] + ')';
                render(function () { var b = add('div', 'kf-pre bad'); add('b', '', 'อุ๊ย มี error ค่ะ ', b); add('span', '', help, b); }, true);
                return;
            }
            if (!e.full) return;
            // ตรงกับขั้นที่สอน (หรือขั้นถัดๆ ไป) → ชมแล้วไปต่อ
            // ข้ามไปขั้นข้างหน้าได้ แต่ห้ามข้ามขั้นที่แก้ค่า (เช่นพิมพ์ exit ทั้งที่ยังไม่ได้ vlan access 20)
            var NAV = /^(show|ping|traceroute|no page|page|exit|end|configure)\b/;
            for (var j = si; j < steps.length; j++) {
                var s2 = steps[j];
                if (s2.kind === 'cmd' && canon(s2.x.full) === canon(e.full)) {
                    si = Math.min(j + 1, steps.length - 1);
                    if (j + 1 >= steps.length) si = j;
                    var lastCmd = !steps.slice(j + 1).some(function (x) { return x.kind === 'cmd'; });
                    var why = lastCmd ? taskWhy(L.tasks[ti], ti) : '';
                    var firstCmd = steps.findIndex(function (x) { return x.kind === 'cmd'; });
                    // พิมพ์ครบทุกคำสั่งแล้วแต่ข้อยังไม่ผ่าน (ยกเว้นข้อที่ต้องกรอกคำตอบต่อ) → บอกว่าขาดอะไร แล้วเริ่มคำสั่งของข้อนี้ใหม่
                    if (why && !(steps[si] && steps[si].kind === 'answer') && !/ยังไม่ได้ตอบ/.test(why)) {
                        si = firstCmd < 0 ? 0 : firstCmd;
                        render(function () {
                            var b = add('div', 'kf-pre bad'); add('b', '', 'คำสั่งนี้ถูกค่ะ แต่ข้อ ' + (ti + 1) + ' ยังไม่ผ่าน ✗ ', b);
                            add('span', '', 'ยังขาด: ' + why + ' ลองไล่ทำตามคำสั่งด้านล่างใหม่อีกรอบนะคะ', b);
                        }, true);
                        return;
                    }
                    render(function () { var b = add('div', 'kf-pre good'); add('b', '', 'ถูกต้องค่ะ ✓ ', b); add('span', '', s2.x.meaning, b); }, true);
                    return;
                }
                // ขั้นนี้ยังไม่ได้ทำและเป็นคำสั่งแก้ค่า: คำสั่งที่พิมพ์มาจะนับเป็นขั้นข้างหน้าไม่ได้
                if (s2.kind === 'cmd' && !NAV.test(s2.x.full) && j >= si && NAV.test(e.full)) break;
            }
            // พิมพ์ซ้ำคำสั่งขั้นก่อนหน้าของข้อนี้ (เช่นออกโหมดแล้วกลับเข้า interface ใหม่) → ถอยกลับไปขั้นถัดจากนั้น
            for (var k2 = si - 1; k2 >= 0; k2--) {
                var s3 = steps[k2];
                if (s3.kind === 'cmd' && !NAV.test(s3.x.full) && canon(s3.x.full) === canon(e.full)) {
                    si = k2 + 1;
                    render(function () { var b = add('div', 'kf-pre good'); add('b', '', 'ถูกต้องค่ะ ✓ ', b); add('span', '', s3.x.meaning + ' ต่อคำสั่งถัดไปได้เลยค่ะ', b); }, true);
                    return;
                }
            }
            // ไม่ตรงกับขั้นที่สอน: คำสั่งดูค่า (show/ping/traceroute) = แค่อธิบาย · คำสั่งที่แก้ค่า = บอกว่ายังไม่ถูก
            var readOnly = /^(show|ping|traceroute|no page|page|exit|end|configure)\b/.test(e.full);
            // exit/end ออกจากโหมดที่ต้องพิมพ์คำสั่งของขั้นนี้ ทั้งที่ยังไม่ได้พิมพ์ = ยังไม่ถูก
            var leftMode = /^(exit|end)\b/.test(e.full) && st && st.kind === 'cmd' && !NAV.test(st.x.full) && st.x.mode && pm === st.x.mode;
            var wrong = (!readOnly || leftMode) && st && st.kind === 'cmd';
            render(function () {
                var b = add('div', 'kf-pre' + (wrong ? ' bad' : ''));
                add('b', '', wrong ? 'ยังไม่ถูกค่ะ ✗ ' : 'เมื่อกี้พิมพ์ ', b);
                if (wrong) add('span', '', 'เจ้านายพิมพ์ ', b);
                code(e.full, b);
                add('span', '', ' = ' + (e.meaning || 'คำสั่งนี้ทำงานแล้วค่ะ'), b);
                if (wrong) add('div', '', 'ขั้นนี้ต้องพิมพ์คำสั่งด้านล่างค่ะ' + (st.x.mode && st.x.mode !== mode.name ? ' (ตอนนี้อยู่โหมด ' + MODE_LABEL[mode.name] + ' ต้องไปโหมด ' + MODE_LABEL[st.x.mode] + ' ก่อนนะคะ)' : ''), b);
            }, wrong);
        }
        var started = false;
        function state() {
            if (!started) { lastDone = done.slice(); return; }
            var newly = done.filter(function (i) { return lastDone.indexOf(i) < 0; });
            lastDone = done.slice();
            if (studyMode === 'exam') {
                if (newly.length && done.length === L.tasks.length)
                    notice('ผ่านโหมดสอบครบทุกข้อแล้วค่ะ ♪', 'เก่งมากเลยค่ะเจ้านาย ทำเองได้ครบ ' + L.tasks.length + ' ข้อโดยไม่ต้องมีคนสอน', addBenefits);
                return;
            }
            if (ti >= 0 && newly.indexOf(ti) >= 0) {
                clearTimeout(timer);
                var finished = ti, next = firstOpen();
                if (next < 0) {   // ข้อสุดท้าย: สรุปประโยชน์ที่ได้จากบทนี้
                    ti = -1; si = 0; steps = [];
                    render(function () { var b = add('div', 'kf-pre good'); add('b', '', 'เก่งมากค่ะ! ผ่านข้อ ' + (finished + 1) + ' แล้ว ✓ ', b); add('span', '', 'อย่าลืมว่าในงานจริงต้องบันทึก config ทุกครั้งนะคะ', b); }, true);
                    return;
                }
                body.replaceChildren();
                add('div', 'hi kf-t', 'เก่งมากค่ะ! ผ่านข้อ ' + (finished + 1) + ' แล้ว ✓');
                add('div', 'kf-t', next < 0 ? 'ครบทุกข้อแล้วค่ะ อย่าลืมว่าในงานจริงต้องบันทึก config ทุกครั้งนะคะ' : 'ต่อไปข้อ ' + (next + 1) + ': ' + L.tasks[next].title + ' ค่ะ');
                bPut.hidden = true; bPrev.disabled = true;
                bNext.textContent = next < 0 ? 'จบ' : 'ข้อถัดไป ▶';
                ti = next; si = 0; steps = next < 0 ? [] : build(next);   // Enter / ถัดไป = ไปข้อใหม่ทันที (นับจากขั้นแนวคิด)
                si = -1;
                open(); speak();
                timer = setTimeout(function () { if (si === -1) teach(next); }, quiet ? 400 : 4000);
            }
        }
        function start(restored) {
            started = true;
            lastDone = done.slice();
            ti = firstOpen(); si = 0; steps = ti < 0 ? [] : build(ti);
            if (studyMode === 'exam') {
                if (restored) { say.hidden = true; return; }   // กลับมาทำต่อ: ไม่ต้องเด้งกรอบ
                return examNote();
            }
            render(function () {
                add('div', 'kf-pre', restored && done.length ? 'ยินดีต้อนรับกลับค่ะ ทำไปแล้ว ' + done.length + '/' + L.tasks.length + ' ข้อ มาต่อกันเลยนะคะ'
                    : 'เจ้านายคะ วันนี้ Kafra จะสอน "' + L.title + '" ทีละข้อนะคะ กดที่ข้อทางซ้ายเพื่อให้สอนข้อนั้นได้ค่ะ');
            }, true);
        }
        taskEls.forEach(function (e, i) { e.querySelector('b').addEventListener('click', function () { if (studyMode === 'exam') return examNote(); teach(i); }); });
        return { exec: exec, state: state, start: start, teach: teach };
    })();

    function banner() {
        print(['(Lab จำลอง AOS-CX ไม่ใช่เครื่องจริง) พิมพ์ ? ดูคำสั่ง · Tab เติมคำ · ↑ คำสั่งเดิม · Ctrl+Z กลับ #', ''], 'sys');
        print([(DEV.ip ? 'ssh admin@' + DEV.ip : 'switch login: admin'), 'Password:', '', 'Last login: ' + new Date().toLocaleString('en-GB'), 'User "admin" has logged in 1 time in the past 30 days', '']);
    }

    // ปุ่ม "จอใหญ่": ซ่อนเมนู/ท้ายเว็บ + เต็มจอ (จำค่าไว้) · ออกด้วยปุ่มเดิมหรือ Esc
    (function () {
        var b = document.getElementById('labBig'); if (!b) return;
        function set(on) {
            document.body.classList.toggle('lab-big', on);
            b.textContent = on ? '✕ ออกจากจอใหญ่' : '⛶ จอใหญ่';
            try { localStorage.setItem('arubaLab:big', on ? '1' : '0'); } catch (e) {}
            termEl.scrollTop = termEl.scrollHeight;
        }
        b.addEventListener('click', function () {
            var on = !document.body.classList.contains('lab-big');
            set(on);
            try {
                if (on && !document.fullscreenElement) document.documentElement.requestFullscreen();
                if (!on && document.fullscreenElement) document.exitFullscreen();
            } catch (e) {}
            inEl.focus();
        });
        document.addEventListener('fullscreenchange', function () { if (!document.fullscreenElement && document.body.classList.contains('lab-big')) set(false); });
        try { if (localStorage.getItem('arubaLab:big') === '1') set(true); } catch (e) {}
    })();

    var restored = load();
    banner();
    if (restored) print(['(กู้งานที่ทำค้างไว้ในเบราว์เซอร์นี้แล้ว ใช้ show running-config เพื่อดู config)', ''], 'sys');
    refreshPrompt(); fillAnswers(); afterChange();
    showStudy();
    Kafra.start(restored);
    inEl.focus();
})();
