const { chromium } = require('playwright-core');
const path = require('path');
(async () => {
  const S = __dirname;
  const out = process.argv[2] || path.join(S, 'out.pdf');
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 680, height: 1000 } });
  await page.emulateMedia({ media: 'print' });
  await page.goto('file://' + path.join(S, 'summary.html'), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  // <보기> 항목(ⓐ, ㉠, (가), ㄱ. 등으로 시작): 기호 폭만큼 내어쓰기
  await page.evaluate(() => document.querySelectorAll('.bg-hang').forEach(p => {
    const w = p.querySelector('.hl').getBoundingClientRect().width;
    p.style.textIndent = (-w) + 'px'; p.style.paddingLeft = w + 'px';
  }));
  // Lay out each 원본 지문 및 문제 section into fixed pages: passage at full width, questions in two
  // columns. Questions never split; a shared <보기> stays with the question after it; spare space in a
  // column is spread between its questions.
  const xlay = await page.evaluate(() => {
    const clipped = [], shrunk = [];
    const mm = v => v * 96 / 25.4;
    const PH = mm(262), GAP = mm(5), MINQ = mm(55), MAXADD = mm(24);
    const log = [];
    document.querySelectorAll('.xflow').forEach((sec, si) => {
      const head = sec.querySelector('.xf-head');
      const paras = [...sec.querySelector('.xf-pass').children];
      const qsrc = [...sec.querySelector('.xf-qs').children];
      // units: a group (shared <보기>) is glued to the question after it
      const units = [];
      for (let i = 0; i < qsrc.length; i++) {
        const u = document.createElement('div'); u.className = 'xunit';
        u.appendChild(qsrc[i]);
        if (qsrc[i].classList.contains('xg') && i + 1 < qsrc.length) u.appendChild(qsrc[++i]);
        units.push(u);
      }
      sec.innerHTML = '';
      const pages = [];
      const newPage = () => { const p = document.createElement('div'); p.className = 'xpg'; sec.appendChild(p); pages.push(p); return p; };
      let pg = newPage();
      pg.appendChild(head);
      let box = document.createElement('div'); box.className = 'x-passage'; pg.appendChild(box);
      for (const p of paras) {
        box.appendChild(p);
        if (pg.scrollHeight > PH + 1 && box.children.length > 1) {
          box.removeChild(p);
          pg = newPage(); box = document.createElement('div'); box.className = 'x-passage'; pg.appendChild(box);
          box.appendChild(p);
        }
      }
      const bottom = el => el.offsetTop + el.offsetHeight;
      let avail = PH - bottom(box) - GAP;
      const makeCols = h => {
        const w = document.createElement('div'); w.className = 'x-qs2'; w.style.height = h + 'px';
        const a = document.createElement('div'), b = document.createElement('div'); a.className = b.className = 'xcol';
        w.append(a, b); pg.appendChild(w); return [a, b];
      };
      if (avail < MINQ) { pg = newPage(); avail = PH - GAP; }
      let cols = makeCols(avail), ci = 0;
      const allCols = [cols];
      const over = c => c.scrollHeight > c.clientHeight + 1;
      const fullHeight = c => c.clientHeight > PH - mm(20);
      for (const u of units) {
        if (u.querySelector('[data-colbreak]') && cols[ci].children.length) {   // 손 배치: 다음 단에서 시작
          ci++;
          if (ci > 1) { pg = newPage(); cols = makeCols(PH - GAP); allCols.push(cols); ci = 0; }
        }
        cols[ci].appendChild(u);
        // move on while it doesn't fit, unless it is already alone in a full-height column
        while (over(cols[ci]) && (cols[ci].children.length > 1 || !fullHeight(cols[ci]))) {
          cols[ci].removeChild(u);
          ci++;
          if (ci > 1) { pg = newPage(); cols = makeCols(PH - GAP); allCols.push(cols); ci = 0; }
          cols[ci].appendChild(u);
        }
        if (over(cols[ci])) {  // taller than a whole column: shrink just this question to fit
          const z = cols[ci].clientHeight / u.offsetHeight * 0.98;
          u.style.transformOrigin = 'top left'; u.style.transform = `scale(${z})`; u.style.width = (100 / z) + '%';
          u.style.marginBottom = (-(1 - z) * u.offsetHeight) + 'px';
          shrunk.push([si + 1, +z.toFixed(2)]);
        }
      }
      // last page: if everything sits in the left column, balance it across both columns
      {
        const [L, R] = allCols[allCols.length - 1];
        const h = c => { const k = c.lastElementChild; return k ? k.offsetTop - c.offsetTop + k.offsetHeight : 0; };
        if (!R.children.length) {
          while (L.children.length > 1) {
            const u = L.lastElementChild, uh = u.offsetHeight;
            if (h(R) + uh > h(L) - uh + mm(10)) break;
            R.insertBefore(u, R.firstChild);
            if (R.scrollHeight > R.clientHeight + 1) { L.appendChild(u); break; }
          }
        }
      }
      // spread spare space between the questions of each column
      for (const pair of allCols) for (const c of pair) {
        const items = [...c.children];
        if (items.length < 2) continue;
        const last = items[items.length - 1];
        const free = c.clientHeight - (last.offsetTop - c.offsetTop + last.offsetHeight);
        if (free <= 0) continue;
        // 한 단에 두 문항뿐이면 남는 공간의 절반까지(최대 60mm) 띄워 넉넉하게
        const add = items.length === 2 ? Math.min(free * 0.5, mm(60)) : Math.min(free / (items.length - 1) * 0.9, MAXADD);
        items.slice(1).forEach(it => { it.style.marginTop = (parseFloat(getComputedStyle(it).marginTop) + add) + 'px'; });
      }
      // a page that ends with an empty question area loses its column wrapper height
      pages.forEach(p => p.querySelectorAll('.x-qs2').forEach(w => { if (!w.textContent.trim()) w.remove(); }));
      for (const pair of allCols) for (const c of pair) if (c.scrollHeight > c.clientHeight + 1) clipped.push(si + 1);
      pages.forEach((p, k) => { if (p.scrollHeight > p.clientHeight + 1) clipped.push(`${si + 1}p${k + 1}`); });
      log.push([si + 1, pages.length]);
    });
    return { log, clipped, shrunk };
  });
  console.log('exam layout (section, pages):', JSON.stringify(xlay));
  // 기호(ⓐ ㉠ …)가 뒤 말과 함께 다음 줄로 넘어가 앞줄 끝이 비면, 그 문단 자간을 조금 좁혀(최대 -0.04em) 앞줄에 함께 들어가게 함
  const symfit = await page.evaluate(() => {
    let n = 0;
    const SYM = /(?:[㉠-㉭ⓐ-ⓩ㉮-㉻Ⓐ-Ⓩ]|\()\u00a0/g;   // 기호, 빈칸 괄호 ‘( ㉠ )’의 여는 괄호
    document.querySelectorAll('.bogi .bg-p, .x-p, .xq-stem, .xq-ch li').forEach(el => {
      const syms = [];
      const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      while (tw.nextNode()) { const t = tw.currentNode; let m; SYM.lastIndex = 0; while ((m = SYM.exec(t.textContent))) syms.push([t, m.index]); }
      if (!syms.length) return;
      const top = ([t, i]) => { const r = document.createRange(); r.setStart(t, i); r.setEnd(t, i + 1); return r.getClientRects()[0]; };
      const lineLeft = el.getBoundingClientRect().left + parseFloat(getComputedStyle(el).paddingLeft);
      for (const sm of syms) {
        const r0 = top(sm); if (!r0) continue;
        if (r0.left - lineLeft > 20) continue;                       // 줄 첫머리가 아님
        const h0 = el.getBoundingClientRect().height;
        let ok = false;
        for (const ls of [-0.01, -0.02, -0.03, -0.04]) {
          el.style.letterSpacing = ls + 'em';
          const r1 = top(sm);
          if (r1 && r1.top < r0.top - 2 && el.getBoundingClientRect().height <= h0 + 0.5) { ok = true; n++; break; }
        }
        if (!ok) el.style.letterSpacing = '';
      }
    });
    return n;
  });
  console.log('기호 앞줄로:', symfit);
  // 선지: 첫 줄 끝이 크게 비면(다음 말이 통째로 넘어감) 자간을 조금 좁혀(최대 -0.05em) 다음 말을 첫 줄로 올림
  const chfit = await page.evaluate(() => {
    let n = 0;
    document.querySelectorAll('.xq-ch li').forEach(el => {
      const lines = () => { const r = document.createRange(); r.selectNodeContents(el); const tops = []; [...r.getClientRects()].forEach(q => { if (q.width > 0 && !tops.some(t => Math.abs(t - q.top) < 3)) tops.push(q.top); }); return tops.length; };
      const firstEnd = () => { const r = document.createRange(); r.selectNodeContents(el); const qs = [...r.getClientRects()].filter(q => q.width > 0); const t0 = Math.min(...qs.map(q => q.top)); return Math.max(...qs.filter(q => Math.abs(q.top - t0) < 3).map(q => q.right)); };
      const fs = parseFloat(getComputedStyle(el).fontSize);
      const right = el.getBoundingClientRect().right;
      const n0 = lines(); if (n0 < 2) return;
      // 마지막 줄이 짧게 넘어간 선지(‘겠군.’만 남는 등): 자간을 좁혀(최대 -0.08em) 줄 수를 줄일 수 있으면 그렇게
      // 마지막 줄이 아주 짧으면(5글자 남짓) -0.12em까지
      const lastW = (() => { const r = document.createRange(); r.selectNodeContents(el); const qs = [...r.getClientRects()].filter(q => q.width > 0); const tb = Math.max(...qs.map(q => q.top)); return qs.filter(q => Math.abs(q.top - tb) < 3).reduce((a, q) => a + q.width, 0); })();
      const steps = [-0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08].concat(lastW < fs * 5.5 ? [-0.09, -0.1, -0.11, -0.12] : []);
      for (const ls of steps) {
        el.style.letterSpacing = ls + 'em';
        if (lines() < n0) { n++; return; }
      }
      el.style.letterSpacing = '';
      const e0 = firstEnd(); if (right - e0 < fs * 2.2) return;
      for (const ls of [-0.01, -0.02, -0.03, -0.04, -0.05]) {
        el.style.letterSpacing = ls + 'em';
        if (lines() <= n0 && firstEnd() > e0 + fs) { n++; return; }
      }
      el.style.letterSpacing = '';
    });
    return n;
  });
  console.log('선지 첫 줄 채움:', chfit);
  // <보기> 문단: 한 단어가 통째로 다음 줄로 넘어가 줄 끝이 크게 비는 곳은 어간·어미(조사) 경계에서 끊어 앞줄을 채움.
  // 실제로 줄이 바뀐 곳에만 끊김 자리(​)를 남김(글을 복사할 때 띄어쓰기처럼 보이지 않게).
  const bsplit = await page.evaluate(() => {
    // 끊어도 되는 뒷부분: 조사 전체, 어미 전체, 또는 ‘하다·되다·시키다’ 꼴(5음절 이하). 앞부분은 2음절 이상(어미면 1음절도)
    const JOSA = ['을','를','은','는','이','가','의','에','에서','에게','와','과','로','으로','도','만','까지','부터','처럼','보다','이다','이며','이고','이나','이면','에는','에서는','으로는','으로서','로서','에도','과는','와는','이라는','라는','이란','이라고','라고','에서도','에게는','만큼','마다','과의','와의','에서의','으로의','이었다','였다'];
    const EOMI = ['었다','았다','였다','었고','았고','였고','었으며','았으며','였으며','었는데','았는데','였는데','었던','았던','였던','는다','어서','아서','여서','으며','으면','으나','지만','는데','도록','더니','었을','았을','였을','겠다','겠군','었다고','았다고'];
    const VERB = ['하','되','했','된','될','한','할','함','해','시키','시킨','시켜','되었','하였','되어','하여'];
    const okSplit = (pre, rest) => {
      const core = rest.replace(/[.,?!’”)\]]+$/, '');
      if (!core || !/^[가-힣]+$/.test(core)) return false;
      if (EOMI.includes(core)) return pre.length >= 1;
      if (pre.length < 2) return false;
      if (JOSA.includes(core)) return true;
      return VERB.some(v => core.startsWith(v)) && core.length <= 5;
    };
    let n = 0;
    document.querySelectorAll('.bogi .bg-p, .xq-stem > span:last-child, .xq-ch li').forEach(el => {
      // 글자 노드 → 단어 단위 span
      const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      const nodes = []; while (tw.nextNode()) nodes.push(tw.currentNode);
      nodes.forEach(t => {
        const parts = t.textContent.split(/(\s+)/); if (parts.length < 2 && !/[가-힣]{3,}/.test(t.textContent)) return;
        const f = document.createDocumentFragment();
        parts.forEach(x => { if (!x) return; if (/^\s+$/.test(x)) f.appendChild(document.createTextNode(x)); else { const sp = document.createElement('span'); sp.className = 'bw'; sp.textContent = x; f.appendChild(sp); } });
        t.replaceWith(f);
      });
      const fs = parseFloat(getComputedStyle(el).fontSize);
      for (let pass = 0; pass < 6; pass++) {
        const ta = el.style.textAlign; el.style.textAlign = 'left';
        const r = el.getBoundingClientRect(), right = r.right - parseFloat(getComputedStyle(el).paddingRight);
        const lines = [];
        el.querySelectorAll('.bw').forEach(w => { const q = w.getClientRects(); if (!q.length) return; const t = q[0], L = lines[lines.length - 1];
          if (!L || Math.abs(L.top - t.top) > 2) lines.push({ top: t.top, first: w, end: q[q.length - 1].right }); else L.end = Math.max(L.end, q[q.length - 1].right);
          if (q.length > 1) lines.push({ top: q[q.length - 1].top, first: null, end: q[q.length - 1].right }); });
        let changed = false;
        for (let k = 0; k + 1 < lines.length; k++) {
          const slack = right - lines[k].end, nw = lines[k + 1].first;
          if (slack < fs * 1.6 || !nw) continue;
          const txt = nw.textContent; if (txt.includes('​') || txt.length < 3) continue;
          let best = -1;
          for (let c = 1; c <= txt.length - 1; c++) {
            const rest = txt.slice(c);
            if (!/[가-힣]/.test(txt[c - 1]) || !/[가-힣]/.test(txt[c])) continue;
            if (!okSplit(txt.slice(0, c).replace(/^[‘“(\[]+/, ''), rest)) continue;
            const m = document.createElement('span'); m.style.cssText = 'visibility:hidden;position:absolute;white-space:nowrap'; m.textContent = ' ' + txt.slice(0, c); el.appendChild(m);
            const wpx = m.getBoundingClientRect().width; m.remove();
            if (wpx <= slack - fs * 0.2 && c > best) best = c;
          }
          if (best > 0) { nw.textContent = txt.slice(0, best) + '​' + txt.slice(best); nw.classList.add('bs'); changed = true; n++; }
        }
        el.style.textAlign = ta;
        if (!changed) break;
      }
      el.querySelectorAll('.bw').forEach(w => { if (w.textContent.includes('​') && w.getClientRects().length < 2) { w.textContent = w.textContent.replace(/​/g, ''); n--; } });
    });
    return n;
  });
  console.log('보기 어간·어미 끊기:', bsplit);
  // <보기> 문단: 줄 끝이 크게 비는 줄이 남아 있으면 문단 자간을 조금씩(최대 -0.05em) 좁혀 가장 고르게 되는 값으로
  const btight = await page.evaluate(() => {
    let n = 0;
    document.querySelectorAll('.bogi .bg-p, .xq-stem > span:last-child').forEach(el => {
      const fs = parseFloat(getComputedStyle(el).fontSize);
      const stat = () => {
        const ta = el.style.textAlign; el.style.textAlign = 'left';
        const r = document.createRange(); r.selectNodeContents(el);
        const L = [];
        [...r.getClientRects()].forEach(q => { if (q.width <= 0) return; const l = L.find(x => Math.abs(x.top - q.top) < 3); if (l) l.end = Math.max(l.end, q.right); else L.push({ top: q.top, end: q.right }); });
        el.style.textAlign = ta;
        const right = el.getBoundingClientRect().right - parseFloat(getComputedStyle(el).paddingRight);
        const slack = L.slice(0, -1).map(l => right - l.end);
        return { n: L.length, max: slack.length ? Math.max(...slack) : 0 };
      };
      const s0 = stat(); if (s0.n < 2 || s0.max < fs * 2) return;
      let best = null;
      for (const ls of [-0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08, -0.09, -0.1]) {
        el.style.letterSpacing = ls + 'em';
        const s1 = stat();
        // -0.05em까지는 줄 끝 여백이 1글자 이상 줄면 / -0.08em까지는 줄 수가 줄거나 가장 큰 줄 끝 여백이 2글자 이상 줄면 / -0.1em까지는 줄 수가 줄 때만
        const good = ls >= -0.05 ? (s1.n <= s0.n && s1.max < s0.max - fs)
          : ls >= -0.08 ? (s1.n <= s0.n && (s1.n < s0.n || s1.max < s0.max - 2 * fs)) : (s1.n < s0.n);
        if (good && (!best || s1.n < best[2] || s1.max < best[1] - 0.5)) best = [ls, s1.max, s1.n];
      }
      el.style.letterSpacing = best ? best[0] + 'em' : '';
      if (best) n++;
    });
    return n;
  });
  console.log('보기 자간 조정:', btight);
  // 어간·어미에서 끊긴 말(‘활용/한다고’)은 자간을 조금 좁혀(최대 -0.08em) 통째로 앞줄에 들어가면 그렇게
  const joinfit = await page.evaluate(() => {
    let n = 0;
    document.querySelectorAll('.bw.bs').forEach(w => {   // 자동으로 끊은 말만(데이터에서 정한 끊김 ‘암/세포’는 그대로)
      if (!w.textContent.includes('​')) return;
      const qs = w.getClientRects(); if (qs.length < 2) return;
      const el = w.closest('.bg-p, .xq-ch li, .xq-stem > span:last-child'); if (!el) return;
      const top0 = qs[0].top, h0 = el.getBoundingClientRect().height, ls0 = el.style.letterSpacing, txt = w.textContent;
      const base = parseFloat(ls0) || 0;
      w.textContent = txt.replace(/​/g, '');
      for (const d of [-0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08, -0.09, -0.1, -0.11, -0.12, -0.13, -0.14, -0.15]) {
        if (base + d < (el.closest('.xq-ch') ? -0.12 : -0.15)) break;
        el.style.letterSpacing = (base + d) + 'em';
        const r = w.getClientRects();
        if (r.length === 1 && Math.abs(r[0].top - top0) < 3 && el.getBoundingClientRect().height <= h0 + 0.5) { n++; return; }
      }
      el.style.letterSpacing = ls0; w.textContent = txt;
    });
    return n;
  });
  console.log('끊긴 말 앞줄로:', joinfit);
  const fits = await page.evaluate(() => {
    const res = [];
    document.querySelectorAll('.pg').forEach((pg, i) => {
      const f = pg.querySelector('.fit');
      let z = 1;
      while (f.scrollHeight * z > pg.clientHeight && z > 0.8) {
        z = +(z - 0.01).toFixed(2);
        f.style.transform = `scale(${z})`;
        f.style.width = (100 / z) + '%';
        if (f.getBoundingClientRect().height <= pg.clientHeight) break;
      }
      const ol = f.querySelector('.struct');
      if (ol && z === 1) {
        const items = ol.querySelectorAll('li');
        const spare = pg.clientHeight - f.getBoundingClientRect().height - 8;
        const extra = Math.min(Math.max(spare, 0) / items.length / 2, 14);
        items.forEach(li => {
          const cs = getComputedStyle(li);
          li.style.paddingTop = (parseFloat(cs.paddingTop) + extra) + 'px';
          li.style.paddingBottom = (parseFloat(cs.paddingBottom) + extra) + 'px';
        });
      }
      res.push([i + 1, z, Math.round(f.getBoundingClientRect().height / pg.clientHeight * 100)]);
    });
    return res;
  });
  console.log('fit (page, zoom, fill%):', JSON.stringify(fits));
  const title = await page.title();
  const foot = `<div style="width:100%;font-size:7pt;color:#8a8f9b;padding:0 15mm;display:flex;justify-content:space-between;font-family:Pretendard,sans-serif">
    <span>${title}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`;
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<div></div>', footerTemplate: foot });
  await browser.close();
  console.log('wrote', out);
})();
