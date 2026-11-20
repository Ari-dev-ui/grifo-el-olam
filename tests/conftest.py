import re
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from olam import create_app
from olam.seed import seed_demo

@pytest.fixture
def app(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'test.db'), 'SECRET_KEY': 'test-only-key'})
    seed_demo(app)
    yield app
    app.extensions['engine'].dispose()

def csrf(client, path='/login'):
    response = client.get(path)
    match = re.search(r'name="csrf-token" content="([a-f0-9]+)"', response.get_data(as_text=True))
    assert match, response.status_code
    return match.group(1)

def login(client, username='admin1'):
    token = csrf(client)
    response = client.post('/login', data={'csrf_token': token, 'username': username, 'password': 'OlamDemo2026!'})
    assert response.status_code == 302
    return csrf(client, '/resumen')

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin(client):
    return client, login(client)
