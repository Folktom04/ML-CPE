/*
 * แบบทดสอบปรนัย (Lab Aruba › เตรียมสอบ)
 *   ?mode=practice[&d=1..5]  ฝึกทีละข้อ ตอบแล้วเฉลยทันที
 *   ?mode=mock               สอบจำลอง: สุ่มตามจำนวนข้อของแต่ละหมวด จับเวลา ส่งแล้วสรุปผลรายหมวด
 * สถิติเก็บใน localStorage 'arubaQuiz:stats' = {dom: {หมวด: {n, ok}}, mocks: [{date, score, pass, dom}]}
 */
(function () {
    'use strict';
    var B = window.QUIZ_BANK; if (!B) return;
    var box = document.getElementById('qzBox'), timerEl = document.getElementById('qzTimer'), domSel = document.getElementById('qzDom');
    var params = new URLSearchParams(location.search);
    var MODE = params.get('mode') === 'mock' ? 'mock' : 'practice';
    var DOM = params.get('d') || '';
    var KEYS = 'ABCDEF';

    document.querySelectorAll('.qz-seg a').forEach(function (a) { a.classList.toggle('on', a.dataset.mode === MODE); });
    domSel.value = DOM;
    domSel.disabled = MODE === 'mock';
    domSel.addEventListener('change', function () { location.search = '?mode=practice' + (domSel.value ? '&d=' + domSel.value : ''); });

    function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
    function shuffle(a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
    function dOf(q) { return q.o.split('.')[0]; }
    function stats() { try { return JSON.parse(localStorage.getItem('arubaQuiz:stats') || 'null') || { dom: {}, mocks: [] }; } catch (e) { return { dom: {}, mocks: [] }; } }
    function saveStats(s) { try { localStorage.setItem('arubaQuiz:stats', JSON.stringify(s)); } catch (e) {} }
    function record(q, ok) {
        var s = stats(), d = dOf(q);
        s.dom[d] = s.dom[d] || { n: 0, ok: 0 }; s.dom[d].n++; if (ok) s.dom[d].ok++;
        saveStats(s);
    }
    // เตรียมข้อ: สลับตัวเลือกแต่จำคำตอบที่ถูกตามตำแหน่งใหม่
    function prep(q) {
        var order = shuffle(q.c.map(function (_, i) { return i; }));
        return { q: q, order: order, ans: q.a.map(function (a) { return order.indexOf(a); }).sort(), pick: [] };
    }
    function same(a, b) { a = a.slice().sort(); b = b.slice().sort(); return a.length === b.length && a.every(function (x, i) { return x === b[i]; }); }
    function objName(o) { return 'ข้อ ' + o + ' ' + (B.objectives[o] || ''); }

    function qHtml(it, idx, total, locked) {
        var q = it.q, multi = q.a.length > 1;
        var h = '<div class="qz-top"><span>ข้อ ' + (idx + 1) + ' / ' + total + '</span><span>' + esc(objName(q.o)) + '</span></div>' +
            '<p class="qz-q">' + esc(q.q) + '</p>' + (multi ? '<div class="qz-multi">เลือก ' + q.a.length + ' ข้อ</div>' : '');
        it.order.forEach(function (orig, i) {
            var cls = 'qz-ch' + (it.pick.indexOf(i) >= 0 ? ' sel' : '');
            if (locked) { if (it.ans.indexOf(i) >= 0) cls += ' right'; else if (it.pick.indexOf(i) >= 0) cls += ' wrong'; }
            h += '<button type="button" class="' + cls + '" data-i="' + i + '"' + (locked ? ' disabled' : '') + '><span class="k">' + KEYS[i] + '</span><span>' + esc(q.c[orig]) + '</span></button>';
        });
        return h;
    }
    function bindChoices(it, onChange) {
        box.querySelectorAll('.qz-ch').forEach(function (b) {
            b.addEventListener('click', function () {
                var i = +b.dataset.i, multi = it.q.a.length > 1, k = it.pick.indexOf(i);
                if (multi) { if (k >= 0) it.pick.splice(k, 1); else if (it.pick.length < it.q.a.length) it.pick.push(i); }
                else it.pick = [i];
                onChange();
            });
        });
    }

    // ---------- โหมดฝึก ----------
    function practice() {
        var pool = shuffle(B.questions.filter(function (q) { return !DOM || dOf(q) === DOM; })).map(prep);
        var i = 0, ok = 0, seen = 0, locked = false;
        timerEl.textContent = '';
        function render() {
            if (i >= pool.length) {
                box.innerHTML = '<div class="qz-res"><h2>ครบ ' + pool.length + ' ข้อแล้ว</h2><p>ตอบถูก ' + ok + ' / ' + seen + ' ข้อ (' + (seen ? Math.round(ok / seen * 100) : 0) + '%)</p>' +
                    '<div class="qz-act"><button type="button" class="btn btn-primary" id="qzAgain">สุ่มใหม่</button></div></div>';
                document.getElementById('qzAgain').onclick = function () { location.reload(); };
                return;
            }
            var it = pool[i];
            box.innerHTML = '<div class="qz-top"><span>ถูก ' + ok + ' / ' + seen + '</span><span></span></div>' + qHtml(it, i, pool.length, locked) +
                '<div class="qz-exp' + (locked ? ' on' : '') + '" id="qzExp"></div>' +
                '<div class="qz-act">' + (locked ? '<button type="button" class="btn btn-primary" id="qzNext">ข้อต่อไป →</button>' :
                    '<button type="button" class="btn btn-primary" id="qzCheck"' + (it.pick.length === it.q.a.length ? '' : ' disabled') + '>ตรวจคำตอบ</button>') + '</div>';
            if (locked) {
                var right = same(it.pick, it.ans);
                document.getElementById('qzExp').innerHTML = (right ? '<b class="ok">ถูกต้อง ✓</b>' : '<b class="no">ยังไม่ถูก</b> คำตอบคือ ' + it.ans.map(function (a) { return KEYS[a]; }).join(', ')) + '<br>' + esc(it.q.e);
                document.getElementById('qzNext').onclick = function () { i++; locked = false; render(); };
            } else {
                bindChoices(it, render);
                document.getElementById('qzCheck').onclick = function () {
                    locked = true; seen++;
                    var r = same(it.pick, it.ans); if (r) ok++;
                    record(it.q, r); render();
                };
            }
        }
        render();
    }

    // ---------- โหมดสอบจำลอง ----------
    function mock() {
        box.innerHTML = '<div class="qz-start"><h2 style="margin-top:0">สอบจำลอง ' + B.exam + '</h2><ul>' +
            '<li>' + B.count + ' ข้อ สุ่มตามสัดส่วนหมวดของข้อสอบจริง</li><li>เวลา ' + B.minutes + ' นาที หมดเวลาแล้วส่งอัตโนมัติ</li>' +
            '<li>เกณฑ์ผ่าน ' + B.pass + '% · ไม่เฉลยระหว่างทำ ข้อที่ไม่แน่ใจกด "ทำเครื่องหมาย" ไว้ทบทวน</li>' +
            '<li>ข้อสอบจริงเป็นภาษาอังกฤษ คลังนี้จึงใช้ภาษาอังกฤษ ส่วนคำอธิบายเฉลยเป็นภาษาไทย</li></ul>' +
            '<div class="qz-act"><button type="button" class="btn btn-primary" id="qzStart">เริ่มสอบ</button></div></div>';
        document.getElementById('qzStart').onclick = start;
    }
    function start() {
        var set = [];
        Object.keys(B.domains).forEach(function (d) {
            set = set.concat(shuffle(B.questions.filter(function (q) { return dOf(q) === d; })).slice(0, B.domains[d].mock));
        });
        var items = shuffle(set).map(prep), cur = 0, flags = {}, end = Date.now() + B.minutes * 60000, timer, finished = false;
        window.onbeforeunload = function () { return finished ? undefined : 'ออกจากหน้านี้จะเสียผลสอบ'; };
        function tick() {
            var left = Math.max(0, end - Date.now()), m = Math.floor(left / 60000), s = Math.floor(left % 60000 / 1000);
            timerEl.textContent = '⏱ ' + m + ':' + ('0' + s).slice(-2);
            timerEl.classList.toggle('low', left < 300000);
            if (!left) finish();
        }
        timer = setInterval(tick, 1000); tick();
        function render() {
            var it = items[cur];
            var nav = items.map(function (x, i) {
                return '<button type="button" data-n="' + i + '" class="' + (x.pick.length ? 'ans ' : '') + (flags[i] ? 'flag ' : '') + (i === cur ? 'cur' : '') + '">' + (i + 1) + '</button>';
            }).join('');
            var answered = items.filter(function (x) { return x.pick.length; }).length;
            box.innerHTML = qHtml(it, cur, items.length, false) +
                '<div class="qz-act"><button type="button" class="btn" id="qzFlag">' + (flags[cur] ? 'เลิกทำเครื่องหมาย' : 'ทำเครื่องหมาย') + '</button>' +
                '<div style="flex:1"></div><button type="button" class="btn" id="qzPrev"' + (cur ? '' : ' disabled') + '>← ก่อนหน้า</button>' +
                (cur < items.length - 1 ? '<button type="button" class="btn btn-primary" id="qzNext">ถัดไป →</button>' : '') +
                '<button type="button" class="btn' + (cur === items.length - 1 ? ' btn-primary' : '') + '" id="qzSubmit">ส่งคำตอบ (' + answered + '/' + items.length + ')</button></div>' +
                '<div class="qz-nav">' + nav + '</div>';
            bindChoices(it, render);
            document.getElementById('qzFlag').onclick = function () { flags[cur] = !flags[cur]; render(); };
            document.getElementById('qzPrev').onclick = function () { cur--; render(); };
            var nx = document.getElementById('qzNext'); if (nx) nx.onclick = function () { cur++; render(); };
            document.getElementById('qzSubmit').onclick = function () {
                var left = items.length - answered;
                if (left && !confirm('ยังไม่ได้ตอบ ' + left + ' ข้อ ส่งเลยไหม?')) return;
                finish();
            };
            box.querySelectorAll('.qz-nav button').forEach(function (b) { b.onclick = function () { cur = +b.dataset.n; render(); }; });
        }
        function finish() {
            if (finished) return; finished = true; clearInterval(timer); window.onbeforeunload = null;
            var ok = 0, dom = {}, wrong = [];
            items.forEach(function (it) {
                var d = dOf(it.q), r = same(it.pick, it.ans);
                dom[d] = dom[d] || { n: 0, ok: 0 }; dom[d].n++;
                if (r) { ok++; dom[d].ok++; } else wrong.push(it);
                record(it.q, r);
            });
            var score = Math.round(ok / items.length * 100), pass = score >= B.pass;
            var s = stats(); s.mocks.push({ date: new Date().toISOString(), score: score, pass: pass, dom: dom }); saveStats(s);
            var h = '<div class="qz-res"><h2 class="' + (pass ? 'pass' : 'fail') + '">' + score + '% · ' + (pass ? 'ผ่าน' : 'ยังไม่ผ่าน') + '</h2>' +
                '<p>ถูก ' + ok + ' / ' + items.length + ' ข้อ (เกณฑ์ ' + B.pass + '%)</p><div class="qz-dom">';
            Object.keys(B.domains).forEach(function (d) {
                var x = dom[d] || { n: 0, ok: 0 }, p = x.n ? Math.round(x.ok / x.n * 100) : 0;
                h += '<div><span>หมวด ' + d + ': ' + esc(B.domains[d].name) + '</span><i><s style="width:' + p + '%"></s></i><b>' + p + '%</b></div>';
            });
            h += '</div><div class="qz-act"><a class="btn" href="?mode=practice">ไปฝึกทีละข้อ</a><button type="button" class="btn btn-primary" id="qzAgain">สอบใหม่</button></div>';
            if (wrong.length) h += '<h3 style="margin:18px 0 4px">ข้อที่ตอบผิด (' + wrong.length + ')</h3>';
            wrong.forEach(function (it) {
                h += '<div class="qz-rev"><b>' + esc(it.q.q) + '</b><br>' +
                    '<span class="y">คุณตอบ: ' + (it.pick.length ? it.pick.map(function (i) { return esc(it.q.c[it.order[i]]); }).join(' / ') : '(ไม่ได้ตอบ)') + '</span><br>' +
                    '<span class="c">คำตอบ: ' + it.ans.map(function (i) { return esc(it.q.c[it.order[i]]); }).join(' / ') + '</span><br>' +
                    esc(it.q.e) + ' <span class="sub">(' + esc(objName(it.q.o)) + ')</span></div>';
            });
            box.innerHTML = h + '</div>';
            timerEl.textContent = '';
            document.getElementById('qzAgain').onclick = function () { location.reload(); };
        }
        render();
    }

    if (MODE === 'mock') mock(); else practice();
})();
