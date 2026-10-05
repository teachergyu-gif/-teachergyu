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
  const fits = await page.evaluate(() => {
    const res = [];
    document.querySelectorAll('.pg').forEach((pg, i) => {
      const f = pg.querySelector('.fit');
      let z = 1;
      while (f.scrollHeight * z > pg.clientHeight && z > 0.8) {
        z = +(z - 0.01).toFixed(2);
        f.style.zoom = z;
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
  const foot = `<div style="width:100%;font-size:7pt;color:#8a8f9b;padding:0 15mm;display:flex;justify-content:space-between;font-family:Pretendard,sans-serif">
    <span>부산외고 2학년 중간고사 대비 비문학 요약자료</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`;
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<div></div>', footerTemplate: foot });
  await browser.close();
  console.log('wrote', out);
})();
