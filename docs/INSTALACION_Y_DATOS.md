# Instalación, datos y recuperación

## El proyecto anterior

La versión original está en la etiqueta `v1.0.0-original` del historial Git incluido.
El archivo ZIP original tiene historial de versiones. La entrega nueva no se conecta a tu servidor
MySQL salvo que configures expresamente `OLAM_DATABASE_URL`.

Esta versión cambia la estructura de tablas: añade cabecera y detalle de ventas, hashes, unidades
escaladas, estados, movimientos y auditoría. **No es una actualización SQL que se ejecute sobre las
tablas antiguas.** No importes el SQL antiguo en la base nueva.

## Antes de trasladar una base real

1. Detén la captura de nuevas operaciones durante el traslado y conserva una copia exportada completa.
2. Crea una base nueva `grifo_olam_v2` y verifica el acceso mediante un usuario limitado a esa base.
3. Ejecuta `python -m flask --app app create-admin` para crear el primer administrador, sin `--demo`.
4. Traslada productos y clientes mediante un proceso de migración revisado y probado en copia.
5. Los saldos iniciales se concilian con el inventario y con los puntos actuales de clientes.
6. Las contraseñas originales están en texto: deben transformarse a hash o reemplazarse por claves nuevas.
7. Los registros originales de ventas no tienen identificador común para agrupar artículos de un carrito.
   No se debe inventar esa relación a partir de fechas cercanas. El traslado de ventas requiere acordar
   una política de archivo histórico y conciliación con el negocio.
8. El historial antiguo de premios no identifica de forma fiable cada producto y no registra el movimiento
   de existencias: conserva el archivo original; no vuelvas a descontar esos canjes al trasladarlo.

No se incluye ni se ha ejecutado una migración automática de tus registros de MySQL.
El catálogo demo proviene del SQL recibido; los dos clientes demo son ficticios y explícitos.

## Respaldo de la demostración

1. Cierra el servidor con Ctrl+C.
2. Copia la carpeta `instance` completa a una ubicación de respaldo.
3. Para restaurar, con el servidor detenido, reemplaza esa carpeta por la copia elegida.
4. No combines una base antigua con tablas v2. Conserva la versión de código correspondiente al respaldo.

## Despliegue en servidor

El BAT y `python app.py` son entradas de desarrollo local. Para una instalación controlada:

```bash
python -m pip install -r requirements.txt
python -m flask --app app create-admin
waitress-serve --listen=127.0.0.1:8000 app:app
```

Configura `OLAM_DATABASE_URL` y una clave aleatoria persistente `OLAM_SECRET_KEY` desde el entorno del
servidor. Usa HTTPS a través de un proxy y activa `OLAM_HTTPS=1` allí. No actives esa opción en la demo
HTTP local: las cookies Secure no se enviarán por HTTP. No publiques `instance`, `.env` ni respaldos.

La limitación de intentos de acceso es en memoria del proceso. En un despliegue con varios procesos
se necesita un limitador compartido. No se realizaron pruebas de carga, disponibilidad, pentesting,
restauración en tu infraestructura ni operación MySQL real; no se presenta esta entrega como certificada.

Si aparece un error de tablas en MySQL, revisa que estés apuntando a la base nueva, con InnoDB y permisos
correctos. No soluciones ese error borrando tus tablas antiguas.

## Historial Git portable

Con Git instalado, desde la carpeta que contiene el bundle:

```bash
git clone historial_git.bundle grifo-olam-con-historial
cd grifo-olam-con-historial
git log --oneline --decorate --all
git diff v1.0.0-original..v2.0.0 --stat
```

El bundle contiene el código y sus versiones; las bases locales y las claves de sesión no se incluyen.
