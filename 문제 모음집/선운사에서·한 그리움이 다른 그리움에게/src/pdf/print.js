// render.py가 만든 HTML → PDF (paginate.js가 쪽 나눔을 끝낼 때까지 기다림)
// 사용: NODE_PATH=$(npm root -g) node print.js 입력.html 출력.pdf
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--allow-file-access-from-files'] });
  const p = await b.newPage();
  await p.emulateMedia({ media: 'print' });
  await p.goto('file://' + process.argv[2]);
  await p.waitForFunction(() => document.body.dataset.done === '1', null, { timeout: 60000 });
  await p.evaluate(() => document.fonts.ready);
  console.log('pages', await p.evaluate(() => window.PAGES));
  await p.pdf({ path: process.argv[3], preferCSSPageSize: true, printBackground: true });
  await b.close();
})();
