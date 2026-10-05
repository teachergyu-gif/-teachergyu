const { chromium } = require('playwright-core');
const path = require('path');
(async () => {
  const S = __dirname;
  const out = process.argv[2] || path.join(S, 'out.pdf');
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  await page.goto('file://' + path.join(S, 'summary.html'), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  const foot = `<div style="width:100%;font-size:7pt;color:#8a8f9b;padding:0 15mm;display:flex;justify-content:space-between;font-family:Pretendard,sans-serif">
    <span>부산외고 2학년 중간고사 대비 비문학 요약자료</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`;
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<div></div>', footerTemplate: foot });
  await browser.close();
  console.log('wrote', out);
})();
