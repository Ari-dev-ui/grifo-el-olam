"""Reglas de negocio; cada llamador confirma o revierte la transacción completa."""
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_HALF_EVEN
from uuid import UUID
from sqlalchemy import select, update
from .models import Audit, Product, Client, Sale, SaleItem, Movement, Redemption, utcnow

class RuleError(ValueError):
    pass

def required(value, name, maximum=150):
    value = str(value or '').strip()
    if not value or len(value) > maximum:
        raise RuleError(f'{name}: ingresa entre 1 y {maximum} caracteres.')
    return value

def number(value, name, places=3, allow_zero=False):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result > Decimal('1000000'):
            raise InvalidOperation
        if result < 0 or (result == 0 and not allow_zero):
            raise InvalidOperation
        if result != result.quantize(Decimal(1).scaleb(-places)):
            raise InvalidOperation
        return result
    except (InvalidOperation, ValueError, TypeError):
        raise RuleError(f'{name}: ingresa un número {"mayor o igual a 0" if allow_zero else "mayor a 0"}, con hasta {places} decimales (máximo 1 000 000).') from None

def document_number(value):
    value = str(value or '').strip()
    if not re.fullmatch(r'(?:[0-9]{8}|[0-9]{11})', value):
        raise RuleError('Documento: ingresa 8 dígitos para DNI u 11 para RUC.')
    return value

def validate_password(value):
    if not value or len(value) < 10 or len(value) > 128:
        raise RuleError('La contraseña debe tener entre 10 y 128 caracteres.')

def audit(db, user_id, action, detail):
    db.add(Audit(user_id=user_id, action=action, detail=detail))

def valid_key(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise RuleError('Actualiza el formulario para iniciar una operación válida.') from None

def sale_signature(data):
    return hashlib.sha256(json.dumps({k: data.get(k) for k in ('client', 'items', 'payment', 'cash')}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def register_sale(db, data, user_id):
    if not isinstance(data, dict):
        raise RuleError('Revisa los datos de la venta.')
    key = valid_key(data.get('request_key'))
    signature = sale_signature(data)
    prior = db.scalar(select(Sale).where(Sale.request_key == key))
    if prior:
        if prior.request_hash != signature or prior.user_id != user_id:
            raise RuleError('Este identificador ya corresponde a otra venta. Abre una nueva venta.')
        return prior, True
    items = data.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        raise RuleError('Agrega entre 1 y 50 productos a la venta.')
    payment = data.get('payment')
    if payment not in ('Efectivo', 'Tarjeta', 'Yape'):
        raise RuleError('Selecciona Efectivo, Tarjeta o Yape.')
    client_doc = str(data.get('client') or '').strip()
    client = None
    if client_doc:
        document_number(client_doc)
        client = db.scalar(select(Client).where(Client.document == client_doc, Client.active.is_(True)))
        if not client:
            raise RuleError('El cliente no está registrado o está inactivo. Regístralo o deja el documento vacío.')
    product_ids = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('product_id'), str):
            raise RuleError('Hay un producto inválido en el carrito.')
        product_ids.append(item['product_id'])
    if len(set(product_ids)) != len(product_ids):
        raise RuleError('Combina las cantidades del mismo producto en una sola fila.')
    products = db.scalars(select(Product).where(Product.id.in_(product_ids)).order_by(Product.id).with_for_update()).all()
    by_id = {p.id: p for p in products}
    details, total, points = [], 0, 0
    for item in items:
        product = by_id.get(item['product_id'])
        if not product or not product.active:
            raise RuleError('Un producto dejó de estar disponible. Actualiza el catálogo.')
        quantity = number(item.get('quantity'), f'Cantidad de {product.name}', places=3 if product.unit == 'gal' else 0)
        milli = int(quantity * 1000)
        if item.get('price_cents') != product.price_cents:
            raise RuleError(f'El precio de {product.name} cambió. Actualiza el catálogo y revisa el total.')
        cents = int((quantity * product.price_cents).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        if cents <= 0:
            raise RuleError(f'El importe de {product.name} debe ser al menos S/ 0.01.')
        earned = int((quantity * Decimal('0.2')).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)) if client else 0
        details.append((product, milli, cents, earned))
        total += cents
        points += earned
    if total > 100000000:
        raise RuleError('El total de una venta no puede superar S/ 1 000 000.')
    if data.get('expected_total_cents') != total:
        raise RuleError('El total cambió. Revisa el carrito antes de confirmar otra vez.')
    cash = None
    if payment == 'Efectivo' and data.get('cash') not in (None, ''):
        cash = int(number(data.get('cash'), 'Efectivo recibido', 2) * 100)
        if cash < total:
            raise RuleError('El efectivo recibido es menor al total de la venta.')
    sale = Sale(request_key=key, request_hash=signature, client_document=client_doc or None,
                client_name=client.name if client else 'Cliente sin registro', user_id=user_id,
                total_cents=total, points=points, payment=payment, cash_cents=cash)
    db.add(sale)
    db.flush()
    for product, milli, cents, earned in details:
        changed = db.execute(update(Product).where(Product.id == product.id, Product.active.is_(True), Product.stock_milli >= milli)
                             .values(stock_milli=Product.stock_milli - milli, version=Product.version + 1))
        if changed.rowcount != 1:
            raise RuleError(f'Existencias insuficientes de {product.name}. Revisa la cantidad y vuelve a intentarlo.')
        db.add(SaleItem(sale_id=sale.id, product_id=product.id, product_name=product.name, unit=product.unit,
                        quantity_milli=milli, price_cents=product.price_cents, subtotal_cents=cents, points=earned))
        db.add(Movement(product_id=product.id, delta_milli=-milli, reason=f'Venta V-{sale.id:05d}', user_id=user_id))
    if client:
        db.execute(update(Client).where(Client.document == client_doc).values(points=Client.points + points))
    audit(db, user_id, 'Venta registrada', f'V-{sale.id:05d} · {len(details)} productos · {total} céntimos')
    return sale, False

def cancel_sale(db, sale_id, reason, user_id):
    reason = required(reason, 'Motivo de anulación', 250)
    sale = db.scalar(select(Sale).where(Sale.id == sale_id).with_for_update())
    if not sale:
        raise RuleError('La venta no existe.')
    changed = db.execute(update(Sale).where(Sale.id == sale_id, Sale.status == 'Registrada').values(
        status='Anulada', cancellation_reason=reason, cancelled_at=utcnow()))
    if changed.rowcount != 1:
        raise RuleError('La venta ya fue anulada. No se modificarán las existencias otra vez.')
    if sale.client_document and sale.points:
        result = db.execute(update(Client).where(Client.document == sale.client_document, Client.points >= sale.points).values(points=Client.points - sale.points))
        if result.rowcount != 1:
            raise RuleError('El cliente ya utilizó los puntos de esta venta. Un supervisor debe anular primero el canje correspondiente.')
    for item in db.scalars(select(SaleItem).where(SaleItem.sale_id == sale_id).order_by(SaleItem.product_id)):
        db.execute(update(Product).where(Product.id == item.product_id).values(stock_milli=Product.stock_milli + item.quantity_milli, version=Product.version + 1))
        db.add(Movement(product_id=item.product_id, delta_milli=item.quantity_milli, reason=f'Anulación V-{sale_id:05d}: {reason}'[:250], user_id=user_id))
    audit(db, user_id, 'Venta anulada', f'V-{sale_id:05d}: {reason}')

def redeem(db, document, product_id, quantity, key, user_id):
    key, document = valid_key(key), document_number(document)
    quantity = int(number(quantity, 'Cantidad del premio', 0))
    prior = db.scalar(select(Redemption).where(Redemption.request_key == key))
    if prior:
        if (prior.client_document, prior.product_id, prior.quantity, prior.user_id) != (document, product_id, quantity, user_id):
            raise RuleError('Este formulario ya fue utilizado. Inicia un nuevo canje.')
        return prior
    product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if not product or not product.active or not product.reward_points or product.unit != 'und':
        raise RuleError('Selecciona un premio disponible del catálogo de canjes.')
    total = product.reward_points * quantity
    changed = db.execute(update(Client).where(Client.document == document, Client.active.is_(True), Client.points >= total).values(points=Client.points - total))
    if changed.rowcount != 1:
        raise RuleError('El cliente está inactivo, no existe o tiene puntos insuficientes para este canje.')
    changed = db.execute(update(Product).where(Product.id == product_id, Product.stock_milli >= quantity * 1000).values(
        stock_milli=Product.stock_milli - quantity * 1000, version=Product.version + 1))
    if changed.rowcount != 1:
        raise RuleError('No hay existencias suficientes del premio. Los puntos se conservarán.')
    redemption = Redemption(request_key=key, client_document=document, product_id=product_id, product_name=product.name,
                            quantity=quantity, points=total, user_id=user_id)
    db.add(redemption)
    db.add(Movement(product_id=product_id, delta_milli=-quantity * 1000, reason=f'Canje de {total} puntos', user_id=user_id))
    audit(db, user_id, 'Canje registrado', f'{product_id} · {quantity} unidades · {total} puntos')
    return redemption

def cancel_redemption(db, redemption_id, reason, user_id):
    reason = required(reason, 'Motivo de anulación', 250)
    redemption = db.scalar(select(Redemption).where(Redemption.id == redemption_id).with_for_update())
    if not redemption:
        raise RuleError('El canje no existe.')
    changed = db.execute(update(Redemption).where(Redemption.id == redemption_id, Redemption.status == 'Registrado').values(status='Anulado'))
    if changed.rowcount != 1:
        raise RuleError('El canje ya está anulado.')
    db.execute(update(Client).where(Client.document == redemption.client_document).values(points=Client.points + redemption.points))
    db.execute(update(Product).where(Product.id == redemption.product_id).values(stock_milli=Product.stock_milli + redemption.quantity * 1000, version=Product.version + 1))
    db.add(Movement(product_id=redemption.product_id, delta_milli=redemption.quantity * 1000, reason=f'Anulación canje C-{redemption.id:05d}', user_id=user_id))
    audit(db, user_id, 'Canje anulado', f'C-{redemption.id:05d}: {reason}')
