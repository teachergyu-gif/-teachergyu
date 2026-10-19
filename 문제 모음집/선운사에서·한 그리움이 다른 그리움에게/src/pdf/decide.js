let pw; try { pw = require('playwright-core'); } catch (e) { pw = require('playwright'); } const {chromium} = pw;
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--allow-file-access-from-files']});
const p=await b.newPage();await p.goto('file://'+process.argv[2]);await p.emulateMedia({media:'print'});await p.waitForTimeout(300);
const r=await p.evaluate(()=>[...document.querySelectorAll('.u.set')].filter(w=>w.querySelector('.sethd')).map(w=>{const c=w.parentElement;return {mid:!!w.dataset.mid, gap:w.dataset.mid?parseFloat(w.style.marginTop):0, top:w===c.firstElementChild, colh:c.clientHeight}}));
require('fs').writeFileSync(process.argv[3],JSON.stringify(r));await b.close();})();
