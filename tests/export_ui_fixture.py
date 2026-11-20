"""Fixtures para pruebas DOM; no usa la base de trabajo."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from olam import create_app
from olam.seed import seed_demo
app=create_app({'TESTING':True,'DATABASE_URL':'sqlite://','CSRF_ENABLED':False})
seed_demo(app)
client=app.test_client()
root=Path(__file__).parent/'.fixtures'
root.mkdir(exist_ok=True)
(root/'login.html').write_text(client.get('/login').get_data(as_text=True),encoding='utf-8')
client.post('/login',data={'username':'admin1','password':'OlamDemo2026!'})
for name,path in [('sales','/ventas'),('dashboard','/resumen'),('products','/productos'),('help','/ayuda')]:
    (root/(name+'.html')).write_text(client.get(path).get_data(as_text=True),encoding='utf-8')
(root/'catalogue_api.json').write_text(json.dumps(client.get('/api/productos').json),encoding='utf-8')
app.extensions['engine'].dispose()
