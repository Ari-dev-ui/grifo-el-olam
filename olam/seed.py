import json
from pathlib import Path
from sqlalchemy import func, select
from werkzeug.security import generate_password_hash
from .models import User, Product, Client

def seed_demo(app):
    with app.extensions['db_factory'].begin() as db:
        if db.scalar(select(func.count()).select_from(User)) or db.scalar(select(func.count()).select_from(Product)) or db.scalar(select(func.count()).select_from(Client)):
            print('La base ya contiene registros. No se cambiaron ni reiniciaron datos.')
            return False
        for username, name, role in [('admin1', 'Administración · Demo', 'Administrador'), ('cajero1', 'Caja 1 · Demo', 'Cajero'),
                ('cajero2', 'Caja 2 · Demo', 'Cajero'), ('almacen1', 'Almacén · Demo', 'Encargado de almacén'), ('supervisor1', 'Supervisión · Demo', 'Supervisor')]:
            db.add(User(username=username, name=name, role=role, password_hash=generate_password_hash('OlamDemo2026!')))
        catalog = json.loads((Path(__file__).parent / 'catalogue.json').read_text(encoding='utf-8'))
        for p in catalog:
            db.add(Product(**p))
        db.add_all([Client(document='00000001', name='Cliente de demostración A', points=50),
                    Client(document='00000000001', name='Empresa de demostración B', points=100)])
    print('Demo creada. Usuarios: admin1, cajero1, cajero2, almacen1, supervisor1. Clave demo: OlamDemo2026!')
    return True
