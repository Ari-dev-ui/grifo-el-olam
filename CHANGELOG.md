# Historial de cambios

## 2.0.0 · 19 de noviembre de 2026

- Interfaz unificada y adaptable, sin fuentes ni bibliotecas externas cargadas desde Internet.
- Resumen con datos calculados; catálogo por categorías; carrito con recuperación y deshacer.
- Mensajes de estado, errores conservando datos y revisión previa a guardar ventas y canjes.
- Accesos por rol en servidor y navegación. Contraseñas con hash, CSRF, cookies HttpOnly/SameSite y límite de intentos.
- Ventas con cabecera y detalles: un comprobante por operación con todos los productos.
- Transacciones completas de venta, canje y anulación, más control condicional de stock y puntos.
- Dinero en céntimos, galones en milésimas y validación de unidades enteras.
- Reintentos de venta con identificador único para prevenir duplicados.
- Anulaciones y desactivaciones conservan historial; cambios de stock requieren motivo.
- Detección de fichas de producto desactualizadas; mínimos y movimientos de inventario.
- Configuración separada de credenciales y motor SQLite/MySQL/MariaDB.
- Pruebas automatizadas y matrices de criterios para ambos cursos, con evaluaciones empíricas pendientes identificadas.

## 1.0.0-original

Base del ZIP recibido. Flask/PyMySQL, plantillas independientes, tablas de ventas sin cabecera común,
contraseñas en texto, existencias enteras y controles de acceso incompletos. Conservada en el historial Git.
