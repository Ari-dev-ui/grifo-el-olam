import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from functools import wraps
from uuid import uuid4
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.security import check_password_hash, generate_password_hash
from . import ROLES, SALES_ROLES, STOCK_ROLES, MANAGERS
from .models import User, Product, Client, Sale, SaleItem, Redemption, Movement, Audit
from .services import (RuleError, required, number, document_number, validate_password,
                       audit, register_sale, cancel_sale, redeem, cancel_redemption, sale_signature)

bp = Blueprint('web', __name__)

def allowed(*roles):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not g.user:
                if request.path.startswith('/api/'):
                    return {'ok': False, 'message': 'Tu sesión terminó. Inicia sesión para continuar.'}, 401
                flash('Inicia sesión para continuar.', 'info')
                return redirect(url_for('web.login'))
            if roles and g.user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorate

def factory():
    return current_app.extensions['db_factory']

def paginated(db, query):
    page = max(1, request.args.get('page', 1, type=int))
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    page = min(page, max(1, (total + 19) // 20))
    return db.scalars(query.limit(20).offset((page - 1) * 20)).all(), dict(page=page, total=total, pages=max(1, (total + 19) // 20))

def error_message(exc):
    if isinstance(exc, RuleError):
        return str(exc)
    if isinstance(exc, IntegrityError):
        return 'Ese código, documento, nombre de producto o usuario ya existe. Revisa el registro y vuelve a intentarlo.'
    current_app.logger.exception('Error de persistencia')
    return 'La base de datos está ocupada. Espera un momento y vuelve a intentarlo.'

@bp.get('/')
def home():
    return redirect(url_for('web.dashboard' if g.user else 'web.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('web.dashboard'))
    error, username = None, ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()[:50]
        password = request.form.get('password', '')
        bucket = (request.remote_addr or '', username)
        attempts = current_app.extensions['login_attempts']
        with current_app.extensions['login_lock']:
            now = time.monotonic()
            history = [t for t in attempts.get(bucket, []) if now - t < 60]
            if len(history) >= 5:
                return render_template('login.html', error='Has realizado varios intentos. Espera un minuto antes de volver a ingresar.', username=username), 429
            if len(attempts) > 5000:
                attempts.clear()
            attempts[bucket] = history + [now]
        with factory()() as db:
            user = db.scalar(select(User).where(User.username == username))
            valid = bool(user and user.active and len(password) <= 128 and check_password_hash(user.password_hash, password))
            if not user:
                # Un trabajo criptográfico también para usuarios inexistentes.
                generate_password_hash(password[:128])
            if valid:
                session.clear()
                session.permanent = True
                session.update(user_id=user.id, session_version=user.session_version, csrf=secrets.token_hex(32))
                with current_app.extensions['login_lock']:
                    attempts.pop(bucket, None)
                return redirect(url_for('web.dashboard'))
        error = 'No pudimos iniciar sesión. Revisa tu usuario y contraseña o consulta al administrador.'
    return render_template('login.html', error=error, username=username)

@bp.post('/logout')
@allowed()
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('web.login'))

@bp.get('/resumen')
@allowed()
def dashboard():
    lima = ZoneInfo('America/Lima')
    local_now = datetime.now(lima)
    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).replace(tzinfo=None)
    end = (local_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).astimezone(timezone.utc).replace(tzinfo=None)
    with factory()() as db:
        revenue, count = db.execute(select(func.coalesce(func.sum(Sale.total_cents), 0), func.count(Sale.id)).where(
            Sale.created_at >= start, Sale.created_at < end, Sale.status == 'Registrada')).one()
        products = db.scalar(select(func.count()).select_from(Product).where(Product.active.is_(True)))
        clients = db.scalar(select(func.count()).select_from(Client).where(Client.active.is_(True))) if g.user.role in SALES_ROLES else None
        low = db.scalars(select(Product).where(Product.active.is_(True), Product.stock_milli <= Product.minimum_milli).order_by(Product.stock_milli).limit(5)).all()
        recent = db.scalars(select(Sale).order_by(Sale.id.desc()).limit(5)).all() if g.user.role in SALES_ROLES else []
    months = ('enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre')
    today = f'{local_now.day} de {months[local_now.month-1]} de {local_now.year}'
    return render_template('dashboard.html', title='Resumen', revenue=revenue, sales_count=count, product_count=products,
                           client_count=clients, low=low, recent=recent, today=today)

@bp.get('/ventas')
@allowed(*SALES_ROLES)
def sales():
    return render_template('sales.html', title='Nueva venta')

@bp.get('/api/productos')
@allowed()
def catalog():
    with factory()() as db:
        products = db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.category, Product.name)).all()
        return {'ok': True, 'products': [dict(id=p.id, name=p.name, category=p.category, unit=p.unit,
            price_cents=p.price_cents, stock_milli=p.stock_milli, reward_points=p.reward_points) for p in products]}

@bp.get('/api/clientes/<document>')
@allowed(*SALES_ROLES)
def find_client(document):
    try:
        document_number(document)
    except RuleError as exc:
        return {'ok': False, 'message': str(exc)}, 400
    with factory()() as db:
        client = db.get(Client, document)
        if not client or not client.active:
            return {'ok': False, 'message': 'Cliente no registrado o inactivo. Puedes registrarlo en Clientes o vender sin documento.'}, 404
        return {'ok': True, 'name': client.name, 'points': client.points}

@bp.post('/api/ventas')
@allowed(*SALES_ROLES)
def process_sale():
    data = request.get_json(silent=True)
    try:
        with factory().begin() as db:
            sale, repeated = register_sale(db, data, g.user.id)
            sale_id = sale.id
        return {'ok': True, 'redirect': url_for('web.receipt', sale_id=sale_id), 'repeated': repeated}, 200 if repeated else 201
    except (RuleError, IntegrityError, OperationalError) as exc:
        if isinstance(exc, IntegrityError) and isinstance(data, dict):
            with factory()() as db:
                prior = db.scalar(select(Sale).where(Sale.request_key == str(data.get('request_key'))))
                if prior and prior.user_id == g.user.id and prior.request_hash == sale_signature(data):
                    return {'ok': True, 'redirect': url_for('web.receipt', sale_id=prior.id), 'repeated': True}
        return {'ok': False, 'message': error_message(exc)}, 400

@bp.get('/historial')
@allowed(*SALES_ROLES)
def history():
    query = select(Sale)
    term = request.args.get('q', '').strip()[:150]
    state = request.args.get('state', '')
    if term:
        query = query.where(or_(Sale.client_name.contains(term, autoescape=True), Sale.client_document.contains(term, autoescape=True)))
    if state in ('Registrada', 'Anulada'):
        query = query.where(Sale.status == state)
    with factory()() as db:
        rows, pagination = paginated(db, query.order_by(Sale.id.desc()))
    return render_template('history.html', title='Historial de ventas', rows=rows, pagination=pagination, q=term, state=state)

@bp.get('/ventas/<int:sale_id>')
@allowed(*SALES_ROLES)
def receipt(sale_id):
    with factory()() as db:
        sale = db.get(Sale, sale_id)
        if not sale:
            abort(404)
        items = db.scalars(select(SaleItem).where(SaleItem.sale_id == sale_id).order_by(SaleItem.id)).all()
        seller = db.get(User, sale.user_id)
    return render_template('receipt.html', title=f'Comprobante V-{sale_id:05d}', sale=sale, items=items, seller=seller)

@bp.post('/ventas/<int:sale_id>/anular')
@allowed(*MANAGERS)
def annul_sale(sale_id):
    try:
        with factory().begin() as db:
            cancel_sale(db, sale_id, request.form.get('reason'), g.user.id)
        flash('Venta anulada. Se restauraron las existencias y se revirtieron los puntos.', 'success')
    except (RuleError, IntegrityError, OperationalError) as exc:
        flash(error_message(exc), 'error')
    return redirect(url_for('web.receipt', sale_id=sale_id))

@bp.get('/productos')
@allowed(*STOCK_ROLES)
def products():
    term = request.args.get('q', '').strip()[:150]
    query = select(Product)
    if term:
        query = query.where(or_(Product.name.contains(term, autoescape=True), Product.id.contains(term, autoescape=True)))
    if request.args.get('low') == '1':
        query = query.where(Product.active.is_(True), Product.stock_milli <= Product.minimum_milli)
    with factory()() as db:
        rows, pagination = paginated(db, query.order_by(Product.active.desc(), Product.name))
    return render_template('products.html', title='Inventario', rows=rows, pagination=pagination, q=term)

@bp.route('/productos/nuevo', methods=['GET', 'POST'])
@bp.route('/productos/<product_id>/editar', methods=['GET', 'POST'])
@allowed(*STOCK_ROLES)
def product_form(product_id=None):
    with factory()() as db:
        product = db.get(Product, product_id) if product_id else None
        if product_id and not product:
            abort(404)
    error = None
    if request.method == 'POST':
        values = request.form
        try:
            code = product_id or required(values.get('id'), 'Código', 10).upper()
            if not re.fullmatch(r'[A-Z0-9-]{1,10}', code):
                raise RuleError('Código: utiliza de 1 a 10 letras, números o guiones.')
            category = values.get('category')
            if category not in ('combustibles', 'lubricantes', 'accesorios'):
                raise RuleError('Selecciona una categoría válida.')
            unit = 'gal' if category == 'combustibles' else 'und'
            price = int(number(values.get('price'), 'Precio', 2) * 100)
            stock = int(number(values.get('stock'), 'Existencias', 3 if unit == 'gal' else 0, True) * 1000)
            minimum = int(number(values.get('minimum'), 'Mínimo', 3 if unit == 'gal' else 0, True) * 1000)
            reward = int(number(values['reward_points'], 'Costo en puntos', 0)) if values.get('reward_points') else None
            if reward and unit != 'und':
                raise RuleError('Los premios se entregan por unidades. Deja vacío el costo en puntos del combustible.')
            reason = required(values.get('reason'), 'Motivo del cambio', 200)
            changes = dict(name=required(values.get('name'), 'Nombre'), brand=required(values.get('brand'), 'Marca', 50),
                presentation=required(values.get('presentation'), 'Presentación', 50), category=category, unit=unit,
                price_cents=price, stock_milli=stock, minimum_milli=minimum, reward_points=reward, active=values.get('active') == '1')
            with factory().begin() as db:
                if product_id:
                    old = db.scalar(select(Product).where(Product.id == code).with_for_update())
                    if old.unit != unit:
                        raise RuleError('No se puede cambiar entre galones y unidades. Registra un producto con otro código.')
                    delta = stock - old.stock_milli
                    result = db.execute(update(Product).where(Product.id == code, Product.version == int(values.get('version', '0'))).values(**changes, version=Product.version + 1))
                    if result.rowcount != 1:
                        raise RuleError('Las existencias o el producto cambiaron mientras editabas. Abre de nuevo la ficha antes de guardar.')
                else:
                    db.add(Product(id=code, **changes))
                    db.flush()
                    delta = stock
                if delta:
                    db.add(Movement(product_id=code, delta_milli=delta, reason=reason, user_id=g.user.id))
                audit(db, g.user.id, 'Producto actualizado' if product_id else 'Producto creado', f'{code}: {reason}')
            flash('Producto guardado. El cambio quedó registrado en el historial.', 'success')
            return redirect(url_for('web.products'))
        except (RuleError, IntegrityError, OperationalError, ValueError) as exc:
            error = error_message(exc) if not isinstance(exc, ValueError) or isinstance(exc, RuleError) else 'Actualiza la ficha antes de guardar.'
    values = request.form if request.method == 'POST' else dict(id=product.id, name=product.name, brand=product.brand,
        presentation=product.presentation, category=product.category, price=str(Decimal(product.price_cents) / 100),
        stock=str(Decimal(product.stock_milli) / 1000), minimum=str(Decimal(product.minimum_milli) / 1000),
        reward_points=product.reward_points or '', active='1' if product.active else '0', version=product.version) if product else dict(active='1', minimum='10')
    return render_template('product_form.html', title='Editar producto' if product_id else 'Nuevo producto', product=product, values=values, error=error), 400 if error else 200

@bp.get('/clientes')
@allowed(*SALES_ROLES)
def clients():
    term = request.args.get('q', '').strip()[:150]
    query = select(Client)
    if term:
        query = query.where(or_(Client.name.contains(term, autoescape=True), Client.document.contains(term, autoescape=True)))
    with factory()() as db:
        rows, pagination = paginated(db, query.order_by(Client.active.desc(), Client.name))
    return render_template('clients.html', title='Clientes', rows=rows, pagination=pagination, q=term)

@bp.route('/clientes/nuevo', methods=['GET', 'POST'])
@bp.route('/clientes/<document>/editar', methods=['GET', 'POST'])
@allowed(*SALES_ROLES)
def client_form(document=None):
    with factory()() as db:
        client = db.get(Client, document) if document else None
        if document and not client:
            abort(404)
    error = None
    if request.method == 'POST':
        values = request.form
        try:
            doc = document_number(document or values.get('document'))
            email = values.get('email', '').strip()
            phone = values.get('phone', '').strip()
            if email and (len(email) > 100 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)):
                raise RuleError('Correo: escribe una dirección válida o deja el campo vacío.')
            if phone and not re.fullmatch(r'[0-9+() -]{6,20}', phone):
                raise RuleError('Teléfono: utiliza de 6 a 20 números, espacios o signos + ( ).')
            changes = dict(name=required(values.get('name'), 'Nombre o razón social'), phone=phone, email=email,
                kind='Empresa' if len(doc) == 11 else 'Particular', active=values.get('active') == '1')
            with factory().begin() as db:
                if document:
                    changed = db.execute(update(Client).where(Client.document == doc, Client.version == int(values.get('version', '0'))).values(**changes, version=Client.version + 1))
                    if changed.rowcount != 1:
                        raise RuleError('La ficha cambió. Ábrela de nuevo antes de guardar.')
                else:
                    db.add(Client(document=doc, points=0, **changes))
                audit(db, g.user.id, 'Cliente actualizado' if document else 'Cliente creado', 'Ficha de cliente modificada; puntos conservados.')
            flash('Cliente guardado correctamente.', 'success')
            return redirect(url_for('web.clients'))
        except (RuleError, IntegrityError, OperationalError, ValueError) as exc:
            error = error_message(exc) if isinstance(exc, (RuleError, IntegrityError, OperationalError)) else 'Actualiza la ficha antes de guardar.'
    values = request.form if request.method == 'POST' else dict(document=client.document, name=client.name, phone=client.phone,
        email=client.email, active='1' if client.active else '0', version=client.version) if client else dict(active='1')
    return render_template('client_form.html', title='Editar cliente' if document else 'Nuevo cliente', client=client, values=values, error=error), 400 if error else 200

@bp.route('/canjes', methods=['GET', 'POST'])
@allowed(*SALES_ROLES)
def redemptions():
    error = None
    if request.method == 'POST':
        try:
            with factory().begin() as db:
                redeem(db, request.form.get('document'), request.form.get('product_id'), request.form.get('quantity'), request.form.get('request_key'), g.user.id)
            flash('Canje registrado. Se descontaron los puntos y las existencias del premio.', 'success')
            return redirect(url_for('web.redemptions'))
        except (RuleError, IntegrityError, OperationalError) as exc:
            error = error_message(exc)
    with factory()() as db:
        rewards = db.scalars(select(Product).where(Product.active.is_(True), Product.reward_points.is_not(None), Product.unit == 'und').order_by(Product.name)).all()
        rows, pagination = paginated(db, select(Redemption).order_by(Redemption.id.desc()))
    return render_template('redemptions.html', title='Canje de puntos', rows=rows, pagination=pagination, rewards=rewards,
        values=request.form if request.method == 'POST' else request.args, request_key=request.form.get('request_key') or str(uuid4()), error=error), 400 if error else 200

@bp.post('/canjes/<int:redemption_id>/anular')
@allowed(*MANAGERS)
def annul_redemption(redemption_id):
    try:
        with factory().begin() as db:
            cancel_redemption(db, redemption_id, request.form.get('reason'), g.user.id)
        flash('Canje anulado. Se devolvieron los puntos y las existencias del premio.', 'success')
    except (RuleError, IntegrityError, OperationalError) as exc:
        flash(error_message(exc), 'error')
    return redirect(url_for('web.redemptions'))

@bp.get('/usuarios')
@allowed('Administrador')
def users():
    with factory()() as db:
        rows, pagination = paginated(db, select(User).order_by(User.name))
    return render_template('users.html', title='Usuarios y permisos', rows=rows, pagination=pagination)

@bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@bp.route('/usuarios/<int:user_id>/editar', methods=['GET', 'POST'])
@allowed('Administrador')
def user_form(user_id=None):
    with factory()() as db:
        user = db.get(User, user_id) if user_id else None
        if user_id and not user:
            abort(404)
    error = None
    if request.method == 'POST':
        values = request.form
        try:
            username = required(values.get('username'), 'Usuario', 50).lower()
            if not re.fullmatch(r'[a-z0-9_.-]{3,50}', username):
                raise RuleError('Usuario: utiliza entre 3 y 50 letras minúsculas, números, puntos, guiones o guiones bajos.')
            role = values.get('role')
            if role not in ROLES:
                raise RuleError('Selecciona un rol válido.')
            password = values.get('password', '')
            if not user_id or password:
                validate_password(password)
            active = values.get('active') == '1'
            with factory().begin() as db:
                admins = db.scalars(select(User).where(User.role == 'Administrador', User.active.is_(True)).order_by(User.id).with_for_update()).all()
                if user_id and user.role == 'Administrador' and user.active and (role != 'Administrador' or not active) and len(admins) <= 1:
                    raise RuleError('Debe permanecer al menos un administrador activo. Crea otro antes de cambiar este acceso.')
                changes = dict(name=required(values.get('name'), 'Nombre'), username=username, role=role, active=active)
                if password:
                    changes['password_hash'] = generate_password_hash(password)
                if user_id:
                    changed = db.execute(update(User).where(User.id == user_id, User.session_version == int(values.get('version', '0'))).values(**changes, session_version=User.session_version + 1))
                    if changed.rowcount != 1:
                        raise RuleError('El usuario fue modificado. Abre de nuevo su ficha.')
                else:
                    db.add(User(**changes))
                audit(db, g.user.id, 'Acceso actualizado' if user_id else 'Usuario creado', f'{username} · {role} · {"activo" if active else "inactivo"}')
            flash('Usuario guardado. Sus sesiones anteriores se cerrarán por seguridad.', 'success')
            return redirect(url_for('web.users'))
        except (RuleError, IntegrityError, OperationalError, ValueError) as exc:
            error = error_message(exc) if isinstance(exc, (RuleError, IntegrityError, OperationalError)) else 'Actualiza la ficha antes de guardar.'
    values = request.form if request.method == 'POST' else dict(name=user.name, username=user.username, role=user.role,
        active='1' if user.active else '0', version=user.session_version) if user else dict(active='1')
    return render_template('user_form.html', title='Editar usuario' if user else 'Nuevo usuario', user=user, values=values, error=error), 400 if error else 200

@bp.route('/perfil', methods=['GET', 'POST'])
@allowed()
def profile():
    error = None
    if request.method == 'POST':
        try:
            validate_password(request.form.get('new_password'))
            if request.form.get('new_password') != request.form.get('confirm_password'):
                raise RuleError('La confirmación no coincide con la nueva contraseña.')
            with factory().begin() as db:
                user = db.get(User, g.user.id)
                if not check_password_hash(user.password_hash, request.form.get('current_password', '')):
                    raise RuleError('La contraseña actual no es correcta.')
                user.password_hash = generate_password_hash(request.form['new_password'])
                user.session_version += 1
                audit(db, user.id, 'Contraseña actualizada', 'Cambio realizado por el titular de la cuenta.')
            session.clear()
            flash('Contraseña actualizada. Inicia sesión con tu nueva contraseña.', 'success')
            return redirect(url_for('web.login'))
        except RuleError as exc:
            error = str(exc)
    return render_template('profile.html', title='Mi cuenta', error=error), 400 if error else 200

@bp.get('/actividad')
@allowed(*MANAGERS)
def activity():
    with factory()() as db:
        rows, pagination = paginated(db, select(Audit).order_by(Audit.id.desc()))
        names = {u.id: u.name for u in db.scalars(select(User))}
    return render_template('activity.html', title='Registro de actividad', rows=rows, pagination=pagination, names=names)

@bp.get('/movimientos')
@allowed(*STOCK_ROLES)
def movements():
    with factory()() as db:
        rows, pagination = paginated(db, select(Movement).order_by(Movement.id.desc()))
        products = {p.id: p for p in db.scalars(select(Product))}
    return render_template('movements.html', title='Movimientos de inventario', rows=rows, pagination=pagination, products=products)

@bp.get('/ayuda')
@allowed()
def help_page():
    return render_template('help.html', title='Centro de ayuda')
