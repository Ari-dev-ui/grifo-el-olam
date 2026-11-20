import os
import secrets
import threading
from datetime import timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import click
from flask import Flask, g, request, session, render_template, url_for
from sqlalchemy import create_engine, event, select, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash
from .models import Base, User

ROLES = ('Administrador', 'Supervisor', 'Cajero', 'Encargado de almacén')
SALES_ROLES = ROLES[:3]
STOCK_ROLES = ('Administrador', 'Supervisor', 'Encargado de almacén')
MANAGERS = ('Administrador', 'Supervisor')

def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    key_path = Path(app.instance_path) / 'session.key'
    key = os.getenv('OLAM_SECRET_KEY')
    if not key:
        try:
            with key_path.open('x') as stream:
                stream.write(secrets.token_hex(32))
            key_path.chmod(0o600)
        except FileExistsError:
            pass
        key = key_path.read_text().strip()
    app.config.from_mapping(SECRET_KEY=key,
        DATABASE_URL=os.getenv('OLAM_DATABASE_URL', 'sqlite:///' + str(Path(app.instance_path) / 'olam.db')),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('OLAM_HTTPS') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30), MAX_CONTENT_LENGTH=128 * 1024, CSRF_ENABLED=True)
    if config:
        app.config.update(config)
    options = {'pool_pre_ping': True}
    if app.config['DATABASE_URL'].startswith('sqlite'):
        options['connect_args'] = {'check_same_thread': False, 'timeout': 15}
        if app.config['DATABASE_URL'] in ('sqlite://', 'sqlite:///:memory:'):
            options['poolclass'] = StaticPool
    engine = create_engine(app.config['DATABASE_URL'], **options)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def sqlite_config(conn, _):
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA busy_timeout=15000')
    inspector = inspect(engine)
    existing = inspector.get_table_names()
    if ('usuarios' in existing and 'password_hash' not in {c['name'] for c in inspector.get_columns('usuarios')}) or ('articulos' in existing and 'stock_milli' not in {c['name'] for c in inspector.get_columns('articulos')}):
        engine.dispose()
        raise RuntimeError('Esta base pertenece a la versión anterior. Configura una base nueva grifo_olam_v2. No se modificaron sus tablas.')
    Base.metadata.create_all(engine)
    app.extensions['engine'] = engine
    app.extensions['db_factory'] = sessionmaker(engine, expire_on_commit=False)
    app.extensions['login_attempts'] = {}
    app.extensions['login_lock'] = threading.Lock()

    @app.before_request
    def security():
        g.user = None
        if session.get('user_id'):
            with app.extensions['db_factory']() as db:
                user = db.get(User, session['user_id'])
                if user and user.active and user.session_version == session.get('session_version'):
                    g.user = user
                else:
                    session.clear()
        if 'csrf' not in session:
            session['csrf'] = secrets.token_hex(32)
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH') and app.config['CSRF_ENABLED']:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            if not secrets.compare_digest(token, session['csrf']):
                if request.path.startswith('/api/'):
                    return {'ok': False, 'message': 'La sesión del formulario venció. Actualiza la página y vuelve a intentarlo.'}, 400
                return render_template('error.html', title='Actualiza la página', message='El formulario venció. Vuelve a abrirlo antes de guardar.'), 400

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.context_processor
    def context():
        def page_url(page):
            args = request.args.to_dict()
            args['page'] = page
            return url_for(request.endpoint, **args)
        return dict(ROLES=ROLES, SALES_ROLES=SALES_ROLES, STOCK_ROLES=STOCK_ROLES, MANAGERS=MANAGERS,
                    csrf_token=lambda: session.get('csrf', ''), version='2.0.0', page_url=page_url)

    @app.template_filter('money')
    def money(value):
        return f'{Decimal(value or 0) / 100:,.2f}'

    @app.template_filter('quantity')
    def quantity(value):
        return format(Decimal(value or 0) / 1000, '.3f').rstrip('0').rstrip('.')

    @app.template_filter('localtime')
    def localtime(value):
        return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/Lima')).strftime('%d/%m/%Y · %H:%M') if value else '—'

    @app.errorhandler(403)
    def forbidden(_):
        if request.path.startswith('/api/'):
            return {'ok': False, 'message': 'Tu rol no tiene permiso para esta operación.'}, 403
        return render_template('error.html', title='Acceso restringido', message='Tu rol no tiene permiso para esta sección. Puedes volver al resumen.'), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template('error.html', title='No encontramos esta página', message='La dirección o el registro no existe. Vuelve al resumen para continuar.'), 404

    @app.errorhandler(500)
    def failure(_):
        if request.path.startswith('/api/'):
            return {'ok': False, 'message': 'No pudimos completar la operación. Consulta el historial antes de reintentar.'}, 500
        return render_template('error.html', title='No pudimos completar la operación', message='Inténtalo de nuevo. Si continúa, informa al administrador.'), 500

    @app.cli.command('init-demo')
    def init_demo():
        from .seed import seed_demo
        seed_demo(app)

    @app.cli.command('create-admin')
    @click.option('--username', prompt=True)
    @click.option('--name', prompt=True)
    @click.password_option()
    def create_admin(username, name, password):
        from .services import validate_password
        validate_password(password)
        with app.extensions['db_factory'].begin() as db:
            if db.scalar(select(User).where(User.username == username.lower())):
                raise click.ClickException('Ese usuario ya existe.')
            db.add(User(name=name, username=username.lower(), password_hash=generate_password_hash(password), role='Administrador'))
        click.echo('Administrador creado.')

    from .routes import bp
    app.register_blueprint(bp)
    return app
