# Grifo El Olam · Versión 2.0.0

Sistema académico de ventas, inventario y fidelización para IHC e Ingeniería de Software II.
Conserva Python y Flask, el catálogo de 23 productos del proyecto original y los cuatro roles.
Incluye una interfaz nueva y operaciones transaccionales. No modifica la base original.

## Empezar en Windows

1. Instala Python 3.11 o posterior desde https://www.python.org/downloads/. Marca **Add Python to PATH**.
2. Extrae **todo** el ZIP. Abre la carpeta `grifo-olam`.
3. Ejecuta `INICIAR_WINDOWS.bat`. La primera vez instala las dependencias; requiere Internet.
4. Cuando aparezca `Running on http://127.0.0.1:5000`, abre esa dirección en tu navegador.
5. Ingresa con `admin1` y la contraseña de demostración `OlamDemo2026!`.

También están disponibles `cajero1`, `cajero2`, `almacen1` y `supervisor1`, con la misma clave demo.
La contraseña tiene mayúsculas y termina con un signo de admiración.
Estos accesos son exclusivamente para la demostración local. En una instalación real crea tus propias cuentas.

Si una política de Windows impide abrir el archivo BAT, usa una terminal en esa carpeta:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py --demo
```

No abras las plantillas HTML con doble clic: necesitan que Flask esté ejecutándose.
Detén el servidor con **Ctrl+C**. Para regresar, vuelve a ejecutar el BAT.

## En Linux o macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py --demo
```

## Datos de demostración

- 23 productos del catálogo del archivo original; sus precios son ejemplos del proyecto, no precios vigentes.
- Dos clientes ficticios: `00000001` (50 puntos) y `00000000001` (100 puntos).
- Ventas, canjes y movimientos empiezan vacíos. No se presentan operaciones simuladas como reales.
- Repetir `--demo` **no** reinicia una base que ya contiene datos.
- Los datos se guardan en `instance/olam.db`, junto a la carpeta `olam`.
- La clave de sesión local se genera en `instance/session.key`. No publiques ese archivo.

## Qué probar primero

1. Ingresa como `admin1` y abre **Nueva venta**.
2. Agrega **10.125 galones de Gasolina Regular** y **2 Ambientadores para auto**.
3. Identifica al cliente `00000001` y elige Efectivo. Ingresa `200.00` como efectivo recibido.
4. Confirma: el total debe ser **S/ 195.12**, el vuelto **S/ 4.88** y los puntos de la venta **2**.
5. El comprobante debe contener ambos productos. Abre Inventario para comprobar el descuento.
6. Desde el comprobante, anula la venta escribiendo un motivo. Se restauran existencias y puntos.
7. Cierra sesión y entra como `cajero1` y luego `almacen1` para comprobar los menús y los permisos.

## Módulos

| Módulo | Comportamiento |
|---|---|
| Resumen | Ventas netas del día en Perú, operaciones, productos, clientes y mínimos |
| Nueva venta | Búsqueda, categorías, cantidades, equivalencia en soles, carrito recuperable, deshacer y confirmación |
| Historial | Consulta paginada, búsqueda, estado y comprobantes completos |
| Inventario | Altas, edición, galones decimales, unidades enteras, mínimos y desactivación |
| Clientes | Altas, edición, validación de formato de documento, saldo y desactivación |
| Canjes | Costo explícito en puntos, control de saldo y stock, historial y anulación |
| Usuarios | Roles, contraseñas con hash y cierre de sesiones al cambiar accesos |
| Actividad / movimientos | Registro de cambios, autor, fecha y motivo |
| Ayuda / Mi cuenta | Instrucciones por tarea y cambio de contraseña propia |

## MySQL / MariaDB

El modo de demostración usa SQLite para que puedas probar sin instalar un servidor.
El mismo modelo se configura para MySQL/MariaDB mediante SQLAlchemy y PyMySQL.
**Usa una base nueva llamada `grifo_olam_v2`; la estructura difiere de la original.**

En DBeaver o en tu cliente SQL, crea la base nueva y un usuario dedicado con permisos para esa base.
Ejemplo de creación de la base (no elimina ninguna existente):

```sql
CREATE DATABASE IF NOT EXISTS grifo_olam_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

En PowerShell, antes de iniciar:

```powershell
$env:OLAM_DATABASE_URL="mysql+pymysql://olam_app:TU_CLAVE@127.0.0.1/grifo_olam_v2?charset=utf8mb4"
.venv\Scripts\python.exe app.py --demo
```

Sustituye `olam_app` y `TU_CLAVE` por los datos de tu usuario dedicado. Si tu contraseña contiene caracteres
especiales, codifícalos para una URL. En este modo los datos se guardan en MySQL, no en `instance/olam.db`.
Usa InnoDB para transacciones y claves foráneas. Revisa `docs/INSTALACION_Y_DATOS.md` antes de trasladar registros.

## Pruebas reproducibles

Backend, integridad, concurrencia, permisos y formularios:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Las pruebas crean bases temporales y no usan tu base de trabajo.
También se incluyen pruebas del comportamiento JavaScript mediante DOM: con Node.js 22 o posterior,
activa el entorno Python, ejecuta `npm install` y luego `npm test`.

Consulta los resultados y límites de la validación en `docs/VALIDACION.md`.
La prueba real en tu navegador y con usuarios sigue siendo necesaria: no se declara certificación WCAG ni ISO.

## Para los cursos

- `docs/MATRIZ_IHC.md`: aplicación verificable de Nielsen, Norman, Shneiderman y Mandel/Pressman.
- `docs/INGENIERIA_SOFTWARE.md`: arquitectura, requisitos, criterios de aceptación, cambios y despliegue.
- `docs/EVALUACION_CON_USUARIOS.md`: protocolo breve para recoger evidencia real de IHC.
- `docs/REGLAS_DE_NEGOCIO.md`: cantidades, dinero, puntos y anulaciones.
- `CHANGELOG.md`: cambios respecto a la versión original.
- `historial_git.bundle`: historial portable con la versión original y la mejorada (no es necesario para ejecutar).

## Límites de esta entrega

Comprobante interno académico, sin emisión electrónica SUNAT. Tarjeta y Yape son registros del medio de pago,
sin integración bancaria. DNI/RUC se validan por formato; no se consulta identidad. Las reglas de puntos
deben validarse con el negocio antes de usar el sistema en una operación real.

La base SQLite y la lógica fueron probadas automáticamente. MySQL/MariaDB cuenta con configuración y esquema
compilable; la conexión a tu servidor real y las pruebas visuales en tu navegador están pendientes.
