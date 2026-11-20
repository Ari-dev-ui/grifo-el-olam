from bs4 import BeautifulSoup
import pytest
from sqlalchemy import select
from werkzeug.security import check_password_hash
from olam.models import User, Product, Client
from conftest import csrf, login

@pytest.mark.parametrize('role,allowed_paths,denied_paths', [
    ('cajero1', ['/ventas','/historial','/clientes','/canjes'], ['/productos','/usuarios','/actividad','/movimientos']),
    ('almacen1', ['/productos','/movimientos'], ['/ventas','/historial','/clientes','/canjes','/usuarios','/actividad']),
    ('supervisor1', ['/ventas','/clientes','/canjes','/productos','/actividad'], ['/usuarios','/usuarios/nuevo'])])
def test_role_boundaries(client, role, allowed_paths, denied_paths):
    login(client, role)
    for path in allowed_paths:
        assert client.get(path).status_code == 200, path
    for path in denied_paths:
        assert client.get(path).status_code == 403, path

def test_post_permissions_are_enforced_on_server(client):
    token=login(client,'cajero1')
    for path in ['/productos/nuevo','/usuarios/nuevo','/ventas/1/anular','/canjes/1/anular']:
        assert client.post(path, data={'csrf_token':token}).status_code == 403

def test_anonymous_cannot_access_data_or_modify(client):
    for path in ['/clientes','/ventas','/productos','/usuarios']:
        assert client.get(path).status_code == 302
    assert client.get('/api/productos').status_code == 401
    token=csrf(client)
    assert client.post('/api/ventas',json={},headers={'X-CSRF-Token':token}).status_code == 401

def test_csrf_and_unsafe_get_requests_are_rejected(admin):
    client, token=admin
    assert client.post('/api/ventas',json={}).status_code == 400
    assert client.post('/clientes/nuevo',data={}).status_code == 400
    assert client.get('/ventas/1/anular').status_code == 405
    assert client.get('/logout').status_code == 405

def test_password_hash_and_session_revocation(app, admin):
    client,token=admin
    with app.extensions['db_factory'].begin() as db:
        user=db.scalar(select(User).where(User.username=='admin1'))
        assert user.password_hash != 'OlamDemo2026!'
        assert check_password_hash(user.password_hash,'OlamDemo2026!')
        user.session_version += 1
    assert client.get('/resumen').status_code == 302

def test_last_administrator_cannot_be_disabled(app, admin):
    client, token=admin
    data=dict(csrf_token=token,name='Admin',username='admin1',role='Administrador',active='0',version='1',password='')
    response=client.post('/usuarios/1/editar',data=data)
    assert response.status_code == 400 and 'al menos un administrador' in response.get_data(as_text=True)
    with app.extensions['db_factory']() as db:
        assert db.get(User,1).active is True

def test_stale_product_form_does_not_overwrite_sale_stock(app, admin):
    client,token=admin
    data=dict(csrf_token=token,version='1',name='Gasolina Regular',brand='Primax',presentation='Galón',category='combustibles',price='17.79',stock='4000',minimum='500',active='1',reason='Revisión')
    with app.extensions['db_factory'].begin() as db:
        p=db.get(Product,'L021');p.version=2;p.stock_milli=3999000
    response=client.post('/productos/L021/editar',data=data)
    assert response.status_code == 400
    with app.extensions['db_factory']() as db:
        assert db.get(Product,'L021').stock_milli == 3999000

def test_client_validation_preserves_entered_values(admin):
    client,token=admin
    response=client.post('/clientes/nuevo',data=dict(csrf_token=token,document='123',name='Mi cliente',email='persona@example.com',active='1'))
    assert response.status_code == 400
    soup=BeautifulSoup(response.data,'html.parser')
    assert soup.select_one('#name')['value']=='Mi cliente'
    assert soup.select_one('[role="alert"]')

def test_client_create_edit_and_deactivate_keeps_points(app,admin):
    client,token=admin
    data=dict(csrf_token=token,document='12345678',name='Cliente QA',phone='900000000',email='qa@example.com',active='1')
    assert client.post('/clientes/nuevo',data=data).status_code == 302
    with app.extensions['db_factory'].begin() as db:
        db.get(Client,'12345678').points=12
    data.update(active='0',version='1')
    assert client.post('/clientes/12345678/editar',data=data).status_code == 302
    with app.extensions['db_factory']() as db:
        c=db.get(Client,'12345678');assert c.points==12 and c.active is False

def test_xss_is_escaped_in_views(app,admin):
    with app.extensions['db_factory'].begin() as db:
        db.get(Client,'00000001').name='<script>alert(1)</script>'
    response=admin[0].get('/clientes')
    assert b'<script>alert(1)</script>' not in response.data
    assert b'&lt;script&gt;' in response.data

def test_authentication_error_does_not_enumerate_accounts(client):
    token=csrf(client)
    first=client.post('/login',data=dict(csrf_token=token,username='admin1',password='wrong'))
    second=client.post('/login',data=dict(csrf_token=token,username='nobody',password='wrong'))
    assert BeautifulSoup(first.data,'html.parser').select_one('[role="alert"]').text==BeautifulSoup(second.data,'html.parser').select_one('[role="alert"]').text

def test_login_throttle(client):
    token=csrf(client)
    for _ in range(5):
        assert client.post('/login',data=dict(csrf_token=token,username='admin1',password='wrong')).status_code==200
    assert client.post('/login',data=dict(csrf_token=token,username='admin1',password='wrong')).status_code==429

def test_all_screens_render_with_labelled_inputs_and_no_broken_internal_links(admin):
    client,_=admin
    paths=['/resumen','/ventas','/historial','/productos','/productos/nuevo','/productos/L021/editar','/clientes','/clientes/nuevo','/clientes/00000001/editar','/canjes','/usuarios','/usuarios/nuevo','/usuarios/2/editar','/perfil','/actividad','/movimientos','/ayuda']
    links=set()
    for path in paths:
        response=client.get(path);assert response.status_code==200,path
        soup=BeautifulSoup(response.data,'html.parser')
        assert soup.html['lang']=='es'
        assert soup.select_one('main#main')
        for field in soup.select('input:not([type="hidden"]), select, textarea'):
            assert field.get('id') and soup.find('label',attrs={'for':field['id']}), (path,str(field))
        links.update(a['href'] for a in soup.select('a[href]') if a['href'].startswith('/'))
    for link in links:
        assert client.get(link).status_code==200,link

def test_headers_and_cookie(admin):
    response=admin[0].get('/resumen')
    assert response.headers['Cache-Control']=='no-store'
    assert response.headers['X-Frame-Options']=='DENY'
    assert "script-src 'self'" in response.headers['Content-Security-Policy']

def test_mysql_schema_compiles_without_using_a_live_database():
    from sqlalchemy.schema import CreateTable
    from sqlalchemy.dialects.mysql import dialect
    from olam.models import Base
    for table in Base.metadata.sorted_tables:
        sql=str(CreateTable(table).compile(dialect=dialect()))
        assert 'CREATE TABLE' in sql

def test_original_database_is_detected_before_schema_changes(tmp_path):
    from sqlalchemy import create_engine, inspect
    from olam import create_app
    url='sqlite:///'+str(tmp_path/'legacy.db')
    engine=create_engine(url)
    with engine.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, password VARCHAR(255))')
    with pytest.raises(RuntimeError,match='versión anterior'):
        create_app({'DATABASE_URL':url,'TESTING':True})
    assert inspect(engine).get_table_names()==['usuarios']
    engine.dispose()
