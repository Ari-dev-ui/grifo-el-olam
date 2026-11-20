from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import func, select, update
from olam.models import Product, Client, Sale, SaleItem, Movement, Redemption
from conftest import login

def payload(items=None, **changes):
    data = dict(request_key=str(uuid4()), client='00000001', payment='Efectivo', cash='200.00',
                expected_total_cents=19512, items=items or [
                    dict(product_id='L021', quantity='10.125', price_cents=1779),
                    dict(product_id='L020', quantity='2', price_cents=750)])
    data.update(changes)
    return data

def post_sale(admin, data):
    client, token = admin
    return client.post('/api/ventas', json=data, headers={'X-CSRF-Token': token})

def snapshot(app):
    with app.extensions['db_factory']() as db:
        return (db.scalar(select(func.count()).select_from(Sale)),
                db.scalar(select(func.count()).select_from(SaleItem)),
                db.scalar(select(func.count()).select_from(Movement)),
                db.get(Product, 'L021').stock_milli, db.get(Product, 'L020').stock_milli,
                db.get(Client, '00000001').points)

def test_multiple_products_exact_totals_complete_receipt_and_persistence(app, admin):
    response = post_sale(admin, payload())
    assert response.status_code == 201, response.json
    receipt = admin[0].get(response.json['redirect']).get_data(as_text=True)
    assert 'Gasolina Regular' in receipt and 'Ambientador para auto' in receipt
    assert '195.12' in receipt and '4.88' in receipt
    assert snapshot(app) == (1, 2, 2, 3989875, 118000, 52)
    # Una nueva conexión de base comprueba persistencia, no solo estado de la sesión.
    with app.extensions['db_factory']() as db:
        assert db.get(Sale, 1).total_cents == 19512
        assert db.get(Sale, 1).cash_cents == 20000

def test_last_item_insufficient_rolls_back_whole_sale(app, admin):
    with app.extensions['db_factory'].begin() as db:
        db.get(Product, 'L020').stock_milli = 1000
    before = snapshot(app)
    response = post_sale(admin, payload())
    assert response.status_code == 400 and 'insuficientes' in response.json['message']
    assert snapshot(app) == before

@pytest.mark.parametrize('quantity', ['-1', '0', 'NaN', 'Infinity', '0.0001', '1000001'])
def test_invalid_quantities_never_change_data(app, admin, quantity):
    before = snapshot(app)
    response = post_sale(admin, payload(items=[dict(product_id='L021', quantity=quantity, price_cents=1779)]))
    assert response.status_code == 400
    assert snapshot(app) == before

def test_units_cannot_be_fractional(app, admin):
    response = post_sale(admin, payload(items=[dict(product_id='L020', quantity='0.5', price_cents=750)]))
    assert response.status_code == 400
    assert snapshot(app)[0] == 0

@pytest.mark.parametrize('changes', [dict(expected_total_cents=1), dict(client='123'), dict(client='99999999'), dict(payment='Crédito'), dict(cash='1.00')])
def test_tampered_or_invalid_sale_rejected_atomically(app, admin, changes):
    before = snapshot(app)
    assert post_sale(admin, payload(**changes)).status_code == 400
    assert snapshot(app) == before

def test_price_must_match_current_catalog(app, admin):
    data = payload()
    data['items'][0]['price_cents'] = 1
    result = post_sale(admin, data)
    assert result.status_code == 400 and 'precio' in result.json['message']
    assert snapshot(app)[0] == 0

def test_duplicate_product_rejected(app, admin):
    data = payload()
    data['items'].append(data['items'][0])
    assert post_sale(admin, data).status_code == 400
    assert snapshot(app)[0] == 0

def test_double_confirmation_returns_same_sale_once(app, admin):
    data = payload()
    first = post_sale(admin, data)
    second = post_sale(admin, data)
    assert first.status_code == 201 and second.status_code == 200
    assert first.json['redirect'] == second.json['redirect']
    assert second.json['repeated'] is True
    assert snapshot(app) == (1, 2, 2, 3989875, 118000, 52)

def test_idempotency_key_cannot_hide_modified_payload(app, admin):
    data = payload()
    assert post_sale(admin, data).status_code == 201
    data['payment'] = 'Tarjeta'
    assert post_sale(admin, data).status_code == 400
    assert snapshot(app)[0] == 1

def test_sale_without_client_does_not_earn_points(app, admin):
    assert post_sale(admin, payload(client='')).status_code == 201
    with app.extensions['db_factory']() as db:
        assert db.get(Sale, 1).points == 0
        assert db.get(Client, '00000001').points == 50

def test_annul_reverses_once_preserving_receipt(app, admin):
    assert post_sale(admin, payload()).status_code == 201
    client, token = admin
    for _ in range(2):
        response = client.post('/ventas/1/anular', data={'csrf_token': token, 'reason': 'Error de cantidad'})
        assert response.status_code == 302
    assert snapshot(app) == (1, 2, 4, 4000000, 120000, 50)
    with app.extensions['db_factory']() as db:
        sale = db.get(Sale, 1)
        assert sale.status == 'Anulada' and sale.cancellation_reason == 'Error de cantidad'
    assert 'Anulada' in client.get('/ventas/1').get_data(as_text=True)

def test_redemption_deducts_stock_and_points_once_then_can_reverse(app, admin):
    client, token = admin
    data = dict(csrf_token=token, document='00000001', product_id='L020', quantity='2', request_key=str(uuid4()))
    for _ in range(2):
        assert client.post('/canjes', data=data).status_code == 302
    with app.extensions['db_factory']() as db:
        assert db.get(Client, '00000001').points == 20
        assert db.get(Product, 'L020').stock_milli == 118000
        assert db.scalar(select(func.count()).select_from(Redemption)) == 1
    for _ in range(2):
        assert client.post('/canjes/1/anular', data={'csrf_token': token, 'reason': 'Devolución del premio'}).status_code == 302
    with app.extensions['db_factory']() as db:
        assert db.get(Client, '00000001').points == 50
        assert db.get(Product, 'L020').stock_milli == 120000

def test_failed_redemption_stock_preserves_points(app, admin):
    with app.extensions['db_factory'].begin() as db:
        db.get(Product, 'L020').stock_milli = 1000
    client, token = admin
    assert client.post('/canjes', data=dict(csrf_token=token, document='00000001', product_id='L020', quantity='2', request_key=str(uuid4()))).status_code == 400
    with app.extensions['db_factory']() as db:
        assert db.get(Client, '00000001').points == 50
        assert db.get(Product, 'L020').stock_milli == 1000
        assert db.scalar(select(func.count()).select_from(Redemption)) == 0

@pytest.mark.parametrize('quantity', ['-1','0','1.5','4'])
def test_invalid_or_unaffordable_redemption_changes_nothing(app,admin,quantity):
    client,token=admin
    before=snapshot(app)
    result=client.post('/canjes',data=dict(csrf_token=token,document='00000001',product_id='L020',quantity=quantity,request_key=str(uuid4())))
    assert result.status_code==400
    assert snapshot(app)==before

def test_used_points_block_sale_annul_without_partial_reversal(app, admin):
    assert post_sale(admin, payload()).status_code == 201
    with app.extensions['db_factory'].begin() as db:
        db.get(Client, '00000001').points = 0
    before = snapshot(app)
    client, token = admin
    client.post('/ventas/1/anular', data={'csrf_token': token, 'reason': 'Revisión'})
    assert snapshot(app) == before
    with app.extensions['db_factory']() as db:
        assert db.get(Sale, 1).status == 'Registrada'

def test_simultaneous_sales_cannot_oversell(app):
    with app.extensions['db_factory'].begin() as db:
        db.get(Product, 'L020').stock_milli = 1000
    clients = [app.test_client(), app.test_client()]
    tokens = [login(c, 'cajero1') for c in clients]
    def run(i):
        data = payload(items=[dict(product_id='L020', quantity='1', price_cents=750)], expected_total_cents=750, cash='10')
        return clients[i].post('/api/ventas', json=data, headers={'X-CSRF-Token': tokens[i]}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [0,1]))
    assert sorted(results) == [201,400]
    with app.extensions['db_factory']() as db:
        assert db.get(Product, 'L020').stock_milli == 0
        assert db.scalar(select(func.count()).select_from(Sale)) == 1
