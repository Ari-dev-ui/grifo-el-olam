const fs=require('fs');
const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const {randomUUID}=require('node:crypto');
const path=require('path');
const root=path.resolve(__dirname,'../olam/static')+'/';
const fixtures=path.resolve(__dirname,'.fixtures');
const pause=()=>new Promise(r=>setTimeout(r,5));
async function build(options={}) {
 const html=fs.readFileSync(fixtures+'/sales.html','utf8');
 const dom=new JSDOM(html,{url:'http://local.test/ventas',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,document=w.document;
 w.crypto.randomUUID=randomUUID;
 w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});
 w.HTMLElement.prototype.scrollIntoView=function(){};
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
 w.HTMLDialogElement.prototype.close=function(value=''){this.open=false;this.returnValue=value;this.dispatchEvent(new w.Event('close'));};
 let posts=[],fail=options.networkFailure;
 const products=JSON.parse(fs.readFileSync(fixtures+'/catalogue_api.json')).products;
 w.fetch=async (url,config)=>{
  if(url==='/api/productos')return {ok:true,json:async()=>({ok:true,products})};
  if(url.startsWith('/api/clientes/'))return {ok:true,json:async()=>({ok:true,name:'Cliente QA',points:50})};
  if(url==='/api/ventas') {
   posts.push(JSON.parse(config.body));
   if(fail){fail=false;throw new Error('Prueba: conexión interrumpida');}
   return {ok:false,status:400,json:async()=>({ok:false,message:'Prueba de respuesta controlada'})};
  }
  throw Error('Unexpected request '+url);
 };
 w.eval(fs.readFileSync(root+'app.js','utf8'));
 w.eval(fs.readFileSync(root+'sales.js','utf8'));
 await pause();
 return {dom,w,document,posts};
}
function clickChoice(document,name){const b=[...document.querySelectorAll('.product-choice')].find(b=>b.textContent.includes(name));assert(b,'Producto visible '+name);b.click();}
function change(w,field,value){field.value=value;field.dispatchEvent(new w.Event('input',{bubbles:true}));}
function add(w,document,name,value){clickChoice(document,name);change(w,document.getElementById('item-quantity'),value);document.getElementById('add-item-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));}
(async()=>{
 let {dom,w,document,posts}=await build();
 assert.equal(document.querySelectorAll('.product-choice').length,23);
 add(w,document,'Gasolina Regular','10.125');
 add(w,document,'Ambientador para auto','2');
 assert.equal(document.getElementById('cart-total').textContent,'S/ 195.12');
 document.querySelector('[aria-label="Retirar Ambientador para auto"]').click();
 assert.equal(document.getElementById('cart-total').textContent,'S/ 180.12');
 document.getElementById('undo-remove').click();
 assert.equal(document.getElementById('cart-total').textContent,'S/ 195.12');
 change(w,document.getElementById('catalog-search'),'diesel');
 assert.equal(document.querySelectorAll('.product-choice').length,1);
 change(w,document.getElementById('catalog-search'),'');
 add(w,document,'Shell Helix HX5','0.5');
 assert.equal(document.querySelectorAll('.cart-row').length,2,'Fracción por unidad rechazada');
 clickChoice(document,'Gasolina Premium');
 document.getElementById('sale-mode').value='amount';document.getElementById('sale-mode').dispatchEvent(new w.Event('change'));
 change(w,document.getElementById('item-quantity'),'100');
 assert.match(document.getElementById('quantity-preview').textContent,/5\.498 gal/);
 document.getElementById('client-document').value='00000001';document.getElementById('find-client').click();await pause();
 assert.match(document.getElementById('client-result').textContent,/50 puntos/);
 document.getElementById('cash').value='1.00';
 document.getElementById('review-sale').click();await pause();
 assert.equal(document.getElementById('sale-dialog').open,false,'Efectivo insuficiente no abre confirmación');
 document.getElementById('cash').value='200.00';
 document.getElementById('review-sale').click();await pause();
 assert.equal(document.getElementById('sale-dialog').open,true);
 document.getElementById('submit-sale').click();await pause();
 assert.equal(posts[0].expected_total_cents,19512);
 assert.equal(posts[0].items.length,2);
 assert.equal(posts[0].items[0].quantity,'10.125');
 assert.equal(document.querySelectorAll('.cart-row').length,2,'Error del servidor conserva pedido');
 console.log('PASS UI: catálogo, búsqueda, cantidades, soles, totales, deshacer, cliente, efectivo, confirmación y conservación del carrito.');
 dom.window.close();
 let t=await build({networkFailure:true});
 add(t.w,t.document,'Gasolina Regular','10');
 t.document.getElementById('review-sale').click();await pause();
 t.document.getElementById('submit-sale').click();await pause();
 const stored=JSON.parse(t.w.sessionStorage.getItem('olam-cart-1'));
 assert(stored.pending,'La operación pendiente se conserva al cortar conexión');
 assert.equal(t.document.getElementById('client-document').disabled,true);
 t.document.getElementById('review-sale').click();await pause();
 t.document.getElementById('submit-sale').click();await pause();
 assert.equal(t.posts.length,2);
 assert.deepEqual(t.posts[0],t.posts[1],'El reintento envía exactamente el mismo identificador y pedido');
 console.log('PASS UI: pérdida de conexión, bloqueo de edición y reintento con el mismo identificador.');
 t.dom.window.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
