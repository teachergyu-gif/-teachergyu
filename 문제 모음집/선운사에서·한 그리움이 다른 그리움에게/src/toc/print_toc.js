// toc.html → 1쪽 PDF(A4). 사용: NODE_PATH=$(npm root -g) node print_toc.js 출력.pdf
let pw; try { pw = require('playwright-core'); } catch (e) { pw = require('playwright'); }
(async () => {
  const b = await pw.chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--allow-file-access-from-files'] });
  const p = await b.newPage();
  await p.goto('file://' + __dirname + '/toc.html');
  await p.waitForFunction(() => document.body.dataset.done === '1', null, { timeout: 30000 });
  console.log('title px', await p.evaluate(() => getComputedStyle(document.getElementById('h')).fontSize));
  await p.pdf({ path: process.argv[2], preferCSSPageSize: true, printBackground: true });
  await b.close();
})();
