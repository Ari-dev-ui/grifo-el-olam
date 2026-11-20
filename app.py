"""Entrada local: python app.py --demo"""
import argparse
from olam import create_app
from olam.seed import seed_demo

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grifo El Olam')
    parser.add_argument('--demo', action='store_true', help='Crear datos demo solo si la base está vacía')
    args = parser.parse_args()
    if args.demo:
        seed_demo(app)
    print('Abrir http://127.0.0.1:5000 en el navegador. Ctrl+C para cerrar.')
    app.run(host='127.0.0.1', port=5000, debug=False)
