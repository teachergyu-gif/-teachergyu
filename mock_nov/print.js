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
  // Lay out each 원본 지문 및 문제 section into fixed pages: passage at full width, questions in two
  // columns. Questions never split; a shared <보기> stays with the question after it; spare space in a
  // column is spread between its questions.
  const xlay = await page.evaluate(() => {
    const clipped = [], shrunk = [];
    const mm = v => v * 96 / 25.4;
    const PH = mm(262), GAP = mm(5), MINQ = mm(55), MAXADD = mm(16);
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
        const add = Math.min(free / (items.length - 1) * 0.9, MAXADD);
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
