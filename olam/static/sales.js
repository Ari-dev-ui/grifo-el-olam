'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const money = cents => 'S/ ' + (cents / 100).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2});
  const quantity = milli => (milli/1000).toFixed(3).replace(/\.?0+$/,'');
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const storageKey = 'olam-cart-' + document.body.dataset.user;
  let products = [], selected = null, category = '', removed = null, customer = null, pending = null;
  let cart = [], requestKey = crypto.randomUUID(), busy = false;
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
    if(saved && Array.isArray(saved.cart)) { cart = saved.cart; pending = saved.pending; requestKey = saved.requestKey || requestKey; }
  } catch { /* Si el almacenamiento no está disponible, la venta sigue funcionando. */ }
  function persist() {
    try { sessionStorage.setItem(storageKey, JSON.stringify({cart, pending, requestKey})); } catch { /* Navegación privada sin almacenamiento. */ }
  }
  function showError(message) { $('sale-error').textContent = message; $('sale-error').hidden = false; $('sale-error').focus(); }
  function clearError() { $('sale-error').hidden = true; }
  function toast(message) { const el=$('toast'); el.textContent=message; el.hidden=false; clearTimeout(toast.timer); toast.timer=setTimeout(()=>el.hidden=true,3500); }
  function el(tag, cls, text) { const n = document.createElement(tag); if(cls) n.className = cls; if(text !== undefined) n.textContent = text; return n; }
  function roundPoints(milli) { const base = Math.floor(milli/5000), rest=milli%5000; return rest>2500 || (rest===2500 && base%2===1) ? base+1 : base; }
  function subtotal(item) { return Math.floor((item.quantity_milli * item.price_cents + 500) / 1000); }
  function total() { return cart.reduce((sum,i)=>sum+subtotal(i),0); }
  function mutate() {
    if(pending || busy) { showError('Hay una confirmación pendiente. Reinténtala antes de modificar el pedido o consulta el historial.'); return false; }
    requestKey = crypto.randomUUID(); clearError(); return true;
  }
  function parseScaled(value, places) {
    if(!new RegExp('^(?:[0-9]+)(?:\\.[0-9]{1,'+places+'})?$').test(value)) return NaN;
    const [whole,frac=''] = value.split('.');
    const n = Number(whole) * (10**places) + Number(frac.padEnd(places,'0'));
    return Number.isSafeInteger(n) ? n : NaN;
  }
  async function loadCatalog() {
    if(pending) { products = []; $('catalog-status').hidden = false; $('catalog-status').textContent = 'Hay una confirmación pendiente. Reintenta la misma venta para conocer el resultado; no se duplicará.'; renderCatalog(); renderCart(); return; }
    $('catalog-status').hidden = false; $('catalog-status').textContent = 'Cargando catálogo…';
    $('refresh-catalog').disabled = true;
    try {
      const response = await fetch('/api/productos');
      const data = await response.json();
      if(!response.ok || !data.ok) throw new Error(data.message || 'No pudimos cargar los productos.');
      products = data.products;
      $('catalog-status').textContent = `${products.length} productos disponibles en el catálogo.`;
      renderCatalog();
      // No se sustituyen silenciosamente los precios ya revisados del carrito.
      if(cart.some(item => !products.some(p => p.id === item.product_id && p.price_cents === item.price_cents))) {
        showError('Un producto o precio del pedido cambió. Retira esa fila y vuelve a seleccionarlo del catálogo.');
      }
    } catch(error) { $('catalog-status').textContent = 'No se pudo cargar el catálogo. Pulsa Actualizar catálogo para reintentar.'; showError(error.message); }
    finally { $('refresh-catalog').disabled = false; }
  }
  function renderCatalog() {
    const text=$('catalog-search').value.trim().toLocaleLowerCase('es');
    const filtered=products.filter(p=>(!category || p.category===category) && (p.name+' '+p.id).toLocaleLowerCase('es').includes(text));
    $('catalog-grid').replaceChildren();
    $('catalog-count').textContent = `${filtered.length} productos encontrados`;
    filtered.forEach(p=>{
      const button=el('button','product-choice'+(selected?.id===p.id?' selected':''));
      button.type='button'; button.disabled=p.stock_milli<=0;
      button.setAttribute('aria-label', `Seleccionar ${p.name}, ${money(p.price_cents)} por ${p.unit}`);
      button.append(el('span','product-code',p.id+' · '+p.category),el('strong','',p.name),el('span','product-price',money(p.price_cents)),el('small','',p.stock_milli>0?`${quantity(p.stock_milli)} ${p.unit} disponibles`:'Sin existencias'));
      button.addEventListener('click',()=>selectProduct(p)); $('catalog-grid').append(button);
    });
    if(!filtered.length) $('catalog-grid').append(el('p','muted','No hay productos con esta búsqueda.'));
  }
  function selectProduct(product) {
    if(!mutate()) return;
    selected=product; $('add-item-form').hidden=false;
    $('selected-name').textContent=product.name;
    $('selected-info').textContent=`${money(product.price_cents)} por ${product.unit} · ${quantity(product.stock_milli)} ${product.unit} disponibles`;
    $('sale-mode').value='quantity'; $('sale-mode').options[1].disabled=product.unit!=='gal';
    $('item-quantity').value=product.unit==='und'?'1':'';
    updateMode(); renderCatalog(); $('item-quantity').focus();
    $('add-item-form').scrollIntoView({block:'nearest'});
  }
  function updateMode() {
    if(!selected) return;
    const amount=$('sale-mode').value==='amount';
    $('quantity-label').textContent=amount?'Importe (S/)':selected.unit==='gal'?'Cantidad (galones)':'Cantidad (unidades)';
    $('item-quantity').step=amount?'0.01':selected.unit==='gal'?'0.001':'1';
    $('item-quantity').min=$('item-quantity').step; updatePreview();
  }
  function currentMilli() {
    if(!selected) return NaN;
    const value=$('item-quantity').value;
    return $('sale-mode').value==='amount' ? Math.round(parseScaled(value,2)*1000/selected.price_cents) : parseScaled(value,3);
  }
  function updatePreview() {
    const milli=currentMilli();
    $('quantity-preview').textContent=Number.isFinite(milli)&&milli>0 ? `${quantity(milli)} ${selected.unit} · Subtotal: ${money(subtotal({quantity_milli:milli,price_cents:selected.price_cents}))}${$('sale-mode').value==='amount'?' (equivalencia a 3 decimales)':''}` : 'Ingresa una cantidad para ver el importe.';
  }
  $('add-item-form').addEventListener('submit',event=>{
    event.preventDefault(); if(!selected || !mutate()) return;
    const milli=currentMilli();
    if(!Number.isSafeInteger(milli)||milli<=0||milli>1e9||(selected.unit==='und'&&milli%1000!==0)) { showError('Ingresa una cantidad válida. Los productos por unidad no permiten fracciones.'); return; }
    const existing=cart.find(i=>i.product_id===selected.id);
    if(existing && existing.price_cents!==selected.price_cents) { showError('El precio de esta fila cambió. Retírala y vuelve a agregar el producto.'); return; }
    const combined=milli+(existing?.quantity_milli||0);
    if(combined>selected.stock_milli) { showError(`Solo hay ${quantity(selected.stock_milli)} ${selected.unit} de ${selected.name}. Revisa la cantidad.`); return; }
    if(subtotal({quantity_milli:combined,price_cents:selected.price_cents})<=0) { showError('La cantidad debe generar un importe de al menos S/ 0.01.'); return; }
    if(existing) existing.quantity_milli=combined;
    else cart.push({product_id:selected.id,name:selected.name,unit:selected.unit,price_cents:selected.price_cents,quantity_milli:milli});
    persist(); renderCart(); toast('Producto agregado al pedido.'); $('item-quantity').value=''; updatePreview();
  });
  function renderCart() {
    const area=$('cart-items'); area.replaceChildren();
    if(!cart.length) area.append(el('div','cart-empty','Tu pedido está vacío. Selecciona un producto para comenzar.'));
    cart.forEach((item,index)=>{
      const row=el('div','cart-row'), info=el('div');
      info.append(el('strong','',item.name),el('small','',`${quantity(item.quantity_milli)} ${item.unit} × ${money(item.price_cents)}`));
      const remove=el('button','icon-button','×'); remove.type='button'; remove.setAttribute('aria-label','Retirar '+item.name); remove.disabled=!!pending;
      remove.addEventListener('click',()=>{if(!mutate())return;removed={item,index};cart.splice(index,1);persist();renderCart();$('undo-row').hidden=false;$('undo-remove').focus();});
      row.append(info,el('span','cart-price',money(subtotal(item))),remove); area.append(row);
    });
    $('cart-count').textContent=`${cart.length} ${cart.length===1?'producto':'productos'}`;
    $('cart-total').textContent=money(total()); $('review-sale').disabled=!cart.length || busy;
    $('review-sale').textContent=pending?'Reintentar confirmación':'Revisar y confirmar venta';
    ['client-document','find-client','payment','cash','catalog-search','refresh-catalog'].forEach(id=>$(id).disabled=!!pending);
    updateCash(); updatePoints();
  }
  function updatePoints() {
    $('points-preview').textContent=pending?.client ? 'Los puntos se confirmarán al completar la venta del cliente '+pending.client+'.' : customer ? `Acumulará ${cart.reduce((sum,i)=>sum+roundPoints(i.quantity_milli),0)} puntos · ${customer.name}` : 'Sin cliente registrado: no acumula puntos.';
  }
  function updateCash() {
    $('cash-field').hidden=$('payment').value!=='Efectivo';
    const cash=parseScaled($('cash').value,2);
    $('change-preview').textContent=!$('cash').value?'Si no lo ingresas, se considera pago exacto.':Number.isFinite(cash)&&cash>=total()?`Vuelto: ${money(cash-total())}`:'El efectivo debe cubrir el total de la venta.';
  }
  let lookupVersion=0;
  async function findCustomer() {
    const version=++lookupVersion, doc=$('client-document').value.trim(); customer=null;updatePoints();
    if(!doc) {$('client-result').textContent='Venta sin cliente registrado.';return true;}
    if(!/^(?:[0-9]{8}|[0-9]{11})$/.test(doc)) {$('client-result').textContent='Ingresa 8 dígitos para DNI u 11 para RUC.';return false;}
    $('client-result').textContent='Buscando cliente…';
    try {
      const response=await fetch('/api/clientes/'+encodeURIComponent(doc)),data=await response.json();
      if(version!==lookupVersion) return false;
      if(!data.ok){$('client-result').textContent=data.message;return false;}
      customer={...data,document:doc};$('client-result').textContent=`${data.name} · ${data.points} puntos disponibles.`;updatePoints();return true;
    } catch {$('client-result').textContent='No pudimos consultar el cliente. Reintenta la búsqueda.';return false;}
  }
  $('client-document').addEventListener('input',()=>{lookupVersion++;customer=null;updatePoints();$('client-result').textContent='Pulsa Buscar para identificar al cliente.';});
  $('find-client').addEventListener('click',findCustomer);
  $('catalog-search').addEventListener('input',renderCatalog);
  document.querySelectorAll('[data-category]').forEach(button=>button.addEventListener('click',()=>{category=button.dataset.category;document.querySelectorAll('[data-category]').forEach(b=>{b.classList.toggle('selected',b===button);b.setAttribute('aria-pressed',String(b===button));});renderCatalog();}));
  $('sale-mode').addEventListener('change',()=>{updateMode();$('item-quantity').focus();});
  $('item-quantity').addEventListener('input',updatePreview);
  $('close-editor').addEventListener('click',()=>{$('add-item-form').hidden=true;selected=null;renderCatalog();$('catalog-search').focus();});
  $('refresh-catalog').addEventListener('click',loadCatalog);
  $('undo-remove').addEventListener('click',()=>{if(!removed||!mutate())return;cart.splice(removed.index,0,removed.item);removed=null;$('undo-row').hidden=true;persist();renderCart();toast('Producto restaurado.');});
  $('cash').addEventListener('input',updateCash);$('payment').addEventListener('change',updateCash);
  const dialog=$('sale-dialog');
  $('review-sale').addEventListener('click',async()=>{
    if(!cart.length||busy)return;clearError();
    if(!pending){
      if(!(await findCustomer())){showError('Revisa el documento del cliente o déjalo vacío para continuar sin registro.');return;}
      if($('payment').value==='Efectivo'&&$('cash').value){const cash=parseScaled($('cash').value,2);if(!Number.isFinite(cash)||cash<total()){showError('El efectivo recibido debe ser un importe válido y cubrir el total.');return;}}
    }
    const summary=$('sale-summary');summary.replaceChildren();const list=el('ul');
    cart.forEach(i=>list.append(el('li','',`${quantity(i.quantity_milli)} ${i.unit} · ${i.name} · ${money(subtotal(i))}`)));
    const box=el('div','summary-box');box.append(el('span','','Total de la venta'),el('strong','',money(total())));
    summary.append(list,el('p','muted small-text',(pending?.payment||$('payment').value)+' · '+(customer?.name||(pending?.client?'Documento '+pending.client:'Cliente sin registro'))),box);
    dialog.showModal();
  });
  $('back-to-cart').addEventListener('click',()=>dialog.close());
  $('submit-sale').addEventListener('click',async()=>{
    if(busy)return;
    busy=true; $('submit-sale').disabled=true;$('submit-sale').textContent='Procesando…';$('back-to-cart').disabled=true;
    if(!pending){pending={request_key:requestKey,client:$('client-document').value.trim(),payment:$('payment').value,cash:$('payment').value==='Efectivo'?$('cash').value:'',expected_total_cents:total(),items:cart.map(i=>({product_id:i.product_id,quantity:(i.quantity_milli/1000).toFixed(3),price_cents:i.price_cents}))};persist();}
    try {
      const response=await fetch('/api/ventas',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(pending)});
      const data=await response.json();
      if(!response.ok||!data.ok){if(response.status<500){pending=null;persist();}throw new Error(data.message||'La operación no se completó. Revisa el historial antes de reintentar.');}
      cart=[];pending=null;persist();window.location.assign(data.redirect);
    } catch(error){dialog.close();showError(error.message||'Se perdió la conexión. Reintenta esta misma confirmación para consultar su resultado sin duplicarla.');}
    finally {busy=false;$('submit-sale').disabled=false;$('submit-sale').textContent='Confirmar venta';$('back-to-cart').disabled=false;renderCart();}
  });
  if(pending){$('client-document').value=pending.client||'';$('payment').value=pending.payment;$('cash').value=pending.cash||'';}
  renderCart();loadCatalog();
})();
