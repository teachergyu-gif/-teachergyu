const {chromium}=require('playwright-core');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--allow-file-access-from-files']});
const p=await b.newPage();for(const [i,o] of [[process.argv[2],process.argv[3]]]){await p.goto('file://'+i);await p.waitForTimeout(500);await p.pdf({path:o,preferCSSPageSize:true,printBackground:true});}
await b.close();})();
