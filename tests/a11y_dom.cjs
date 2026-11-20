/* Revisión parcial de estructura: no evalúa contraste ni disposición visual real. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const axe=fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8');
(async()=>{
 for(const name of ['login','dashboard','sales','products','help']){
  const html=fs.readFileSync(path.join(__dirname,'.fixtures',name+'.html'),'utf8');
  const dom=new JSDOM(html,{url:'https://local.test',runScripts:'outside-only'});
  dom.window.HTMLCanvasElement.prototype.getContext=()=>null;
  dom.window.eval(axe);
  const result=await dom.window.axe.run(dom.window.document,{rules:{'color-contrast':{enabled:false}}});
  assert.equal(result.violations.length,0,name+': '+result.violations.map(v=>v.id).join(', '));
  console.log('PASS estructura accesible DOM: '+name+' (contraste y comportamiento visual excluidos)');
  dom.window.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
