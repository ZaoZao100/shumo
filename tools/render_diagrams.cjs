const {chromium}=require('C:/Users/lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path');const {pathToFileURL}=require('url');
(async()=>{const root=path.resolve(__dirname,'..');const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
for(const [name,height] of [['fig_roadmap',365],['fig_energy_flow',275],['fig_arch_solver',292]]){
 const page=await browser.newPage({viewport:{width:720,height},deviceScaleFactor:3});await page.goto(pathToFileURL(path.join(root,'figures',name+'.html')).href);await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:path.join(root,'figures',name+'.png')});await page.pdf({path:path.join(root,'figures',name+'.pdf'),preferCSSPageSize:true,printBackground:true});await page.close();console.log(name);
}await browser.close();})();
