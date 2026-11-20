'use strict';
document.querySelectorAll('[data-password]').forEach(button => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.password);
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    button.textContent = show ? 'Ocultar' : 'Mostrar';
    button.setAttribute('aria-label', show ? 'Ocultar contraseña' : 'Mostrar contraseña');
    button.setAttribute('aria-pressed', String(show));
  });
});
const menuButton = document.querySelector('.menu-toggle');
if (menuButton) {
  const sidebar = document.getElementById('sidebar');
  const close = () => { sidebar.classList.remove('open'); menuButton.setAttribute('aria-expanded','false'); menuButton.setAttribute('aria-label','Abrir menú'); document.querySelector('.workspace').inert=false; sidebar.removeAttribute('aria-modal'); sidebar.removeAttribute('role'); };
  menuButton.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Cerrar menú' : 'Abrir menú');
    document.querySelector('.workspace').inert=open;
    if(open){sidebar.setAttribute('role','dialog');sidebar.setAttribute('aria-modal','true');sidebar.querySelector('.sidebar-close').focus();}
  });
  sidebar.querySelector('.sidebar-close').addEventListener('click',()=>{close();menuButton.focus();});
  document.addEventListener('keydown',e=>{
    if(e.key!=='Tab'||!sidebar.classList.contains('open'))return;
    const focusable=[...sidebar.querySelectorAll('a[href],button')],first=focusable[0],last=focusable[focusable.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  });
  window.matchMedia('(max-width: 900px)').addEventListener('change',close);
  document.addEventListener('click', e => { if (!sidebar.contains(e.target) && !menuButton.contains(e.target)) close(); });
  document.addEventListener('keydown', e => { if(e.key === 'Escape') { close(); menuButton.focus(); } });
}
document.querySelectorAll('[data-print]').forEach(b => b.addEventListener('click', () => window.print()));
const confirmDialog = document.getElementById('confirm-dialog');
let pendingForm = null;
document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (form.dataset.confirmed === 'yes') return;
    event.preventDefault();
    pendingForm = form;
    document.getElementById('confirm-title').textContent = form.dataset.title || 'Confirmar operación';
    document.getElementById('confirm-message').textContent = form.dataset.confirm;
    const needsReason = form.hasAttribute('data-reason');
    document.getElementById('confirm-reason-field').hidden = !needsReason;
    const reason = document.getElementById('confirm-reason');
    reason.required = needsReason;
    reason.value = '';
    confirmDialog.returnValue = '';
    confirmDialog.showModal();
  });
});
if (confirmDialog) confirmDialog.addEventListener('close', () => {
  if(confirmDialog.returnValue !== 'accept' || !pendingForm) { pendingForm = null; return; }
  const form = pendingForm;
  if(form.hasAttribute('data-reason')) form.querySelector('[name="reason"]').value = document.getElementById('confirm-reason').value.trim();
  pendingForm = null;
  form.dataset.confirmed = 'yes';
  form.requestSubmit();
});
document.querySelectorAll('form[data-busy],form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if(event.defaultPrevented) return;
    const button = form.querySelector('button:not([type="button"])');
    if(button) { button.disabled = true; button.textContent = 'Guardando…'; }
    form.setAttribute('aria-busy','true');
  });
});
window.addEventListener('pageshow', event => {
  if(event.persisted) location.reload();
});
const errorSummary = document.querySelector('[data-error]');
if(errorSummary) errorSummary.focus();
document.querySelectorAll('[data-client-lookup]').forEach(button => {
  button.addEventListener('click', async () => {
    const doc = document.getElementById(button.dataset.clientLookup).value.trim();
    const result = document.getElementById(button.dataset.result);
    if(!/^(?:[0-9]{8}|[0-9]{11})$/.test(doc)) { result.textContent = 'Ingresa 8 dígitos para DNI u 11 para RUC.'; return; }
    result.textContent = 'Consultando saldo…'; button.disabled = true;
    try {
      const response = await fetch('/api/clientes/' + encodeURIComponent(doc));
      const data = await response.json();
      result.textContent = data.ok ? `${data.name} · ${data.points} puntos disponibles.` : data.message;
    } catch { result.textContent = 'No pudimos consultar el cliente. Comprueba la conexión y vuelve a intentar.'; }
    finally { button.disabled = false; }
  });
});
const rewardProduct = document.getElementById('product_id');
const rewardQuantity = document.getElementById('quantity');
if(rewardProduct && rewardQuantity) {
  const update = () => {
    const points = Number(rewardProduct.selectedOptions[0]?.dataset.points || 0);
    const qty = Number(rewardQuantity.value || 0);
    document.getElementById('reward-total').textContent = Number.isInteger(qty) && qty > 0 ? `${points * qty} pts` : 'Revisa la cantidad';
  };
  rewardProduct.addEventListener('change', update); rewardQuantity.addEventListener('input', update); update();
}
