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
  // pack every section's units into fixed pages; units never split; quiz pages spread spare space
  const lay = await page.evaluate(() => {
    const mm = v => v * 96 / 25.4;
    const PH = mm(262), MAXADD = mm(14);
    const res = { pages: 0, shrunk: [], clipped: [] };
    document.querySelectorAll('.hsec').forEach((sec, si) => {
      const kind = sec.dataset.kind;
      const head = sec.querySelector('.hs-head');
      const title = sec.querySelector('.hs-title').textContent;
      const us = [...sec.querySelectorAll('.hs-units > .hu')];
      sec.innerHTML = '';
      const pages = [];
      const newPage = (first) => {
        const p = document.createElement('div'); p.className = 'hpg';
        if (first) p.appendChild(head);
        else { const c = document.createElement('div'); c.className = 'hs-cont'; c.textContent = title + ' (계속)'; p.appendChild(c); }
        const body = document.createElement('div'); body.className = 'hbody'; p.appendChild(body);
        sec.appendChild(p); pages.push(p); return body;
      };
      let body = newPage(true);
      const over = () => body.parentElement.scrollHeight > PH + 1;
      const queue = [...us];
      while (queue.length) {
        const u = queue.shift();
        body.appendChild(u);
        if (over() && u.classList.contains('split') && u.children.length > 1) {
          // long explanations may continue on the next page, but only between their own paragraphs
          const rest = u.cloneNode(false); rest.classList.add('cont');
          while (over() && u.children.length > 1) rest.insertBefore(u.lastElementChild, rest.firstChild);
          if (!over() && rest.children.length) { queue.unshift(rest); continue; }
          while (rest.firstChild) u.appendChild(rest.firstChild);  // could not split: undo
        }
        if (over() && body.children.length > 1) {
          body.removeChild(u);
          // a short unit that opens with a sub-heading stays with what follows it
          const prev = body.lastElementChild;
          const lead = prev && body.children.length > 1 && prev.firstElementChild &&
            prev.firstElementChild.classList.contains('hsub') && prev.offsetHeight < mm(30) ? prev : null;
          if (lead) body.removeChild(lead);
          body = newPage(false); if (lead) body.appendChild(lead); body.appendChild(u);
          if (over() && u.classList.contains('split') && u.children.length > 1) {
            const rest = u.cloneNode(false); rest.classList.add('cont');
            while (over() && u.children.length > 1) rest.insertBefore(u.lastElementChild, rest.firstChild);
            if (rest.children.length) queue.unshift(rest);
          }
        }
        if (over()) {  // a single unit taller than a page: scale it down to fit
          const room = PH - body.offsetTop - 2;  // .hpg is the offset parent
          const z = Math.min(1, Math.max(room / u.offsetHeight, 0.5));
          u.style.transformOrigin = 'top left'; u.style.transform = `scale(${z})`; u.style.width = (100 / z) + '%';
          u.style.marginBottom = (-(1 - z) * u.offsetHeight) + 'px';
          res.shrunk.push([title, +z.toFixed(2)]);
        }
      }
      if (kind !== 'theory') {
        pages.forEach((p, k) => {
          const b = p.querySelector('.hbody'); const items = [...b.children];
          if (items.length < 2 || k === pages.length - 1) return;
          const last = items[items.length - 1];
          const free = PH - (last.offsetTop + last.offsetHeight);  // offsets are relative to .hpg
          if (free <= 0) return;
          const add = Math.min(free / (items.length - 1) * 0.9, MAXADD);
          items.slice(1).forEach(it => { it.style.marginTop = (parseFloat(getComputedStyle(it).marginTop) + add) + 'px'; });
        });
      }
      pages.forEach((p, k) => {
        const b = p.querySelector('.hbody'); const last = b.lastElementChild;
        const bottom = last ? last.getBoundingClientRect().bottom - p.getBoundingClientRect().top : 0;
        if (bottom > PH + 1) res.clipped.push(`${title} p${k + 1} +${Math.round(bottom - PH)}px`);
      });
      res.pages += pages.length;
    });
    return res;
  });
  console.log('layout:', JSON.stringify(lay));
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
