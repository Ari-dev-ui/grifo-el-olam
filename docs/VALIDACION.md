# Registro de validación técnica · 19 de noviembre de 2026

Versión: 2.0.0. Entorno: Linux, Python 3.12, SQLite, Node.js y DOM simulado.
La base de pruebas es independiente de la base de demostración y de cualquier servidor del estudiante.

## Resultados observados

| Revisión | Resultado observado | Alcance |
|---|---|---|
| Pytest | **46 pruebas aprobadas** | Operaciones, transacciones, acceso, formularios, datos y concurrencia |
| JavaScript | Dos grupos de pruebas DOM aprobados | Catálogo, pedido, búsqueda, equivalencia, total, deshacer, efectivo, confirmación y reintento |
| Estructura accesible | Sin incidencias reportadas por las reglas ejecutadas en cinco páginas | axe-core sobre DOM; contraste, layout e interacción visual excluidos |
| HTTP local en un mismo proceso de prueba | Login, cookie, redirección, seis módulos y cinco recursos responden correctamente | Servidor WSGI local temporal, sin navegador |
| Sintaxis | Python compila y ambos scripts JavaScript pasan `node --check` | No equivale a prueba completa de interfaz |
| MySQL | El DDL de las tablas compila con el dialecto MySQL | No se probó conexión ni transacciones en un servidor MySQL/MariaDB real |
| Navegador real | **Pendiente** | El navegador de este entorno no pudo conectarse al servidor local |
| Investigación de usuarios | **Pendiente** | No se hicieron entrevistas, pruebas con personas ni mediciones de satisfacción |

Las pruebas de estructura accesible se ejecutaron sobre login, resumen, ventas, inventario y ayuda.
No se declara conformidad WCAG 2.2 completa a partir de esas comprobaciones.

## Casos críticos comprobados

- Venta de 10.125 galones de Regular y dos ambientadores: **S/ 195.12**.
- Efectivo recibido de S/ 200: vuelto **S/ 4.88**. Cliente demo acumula **2 puntos**.
- Comprobante con todos los artículos, cantidades y precio de la operación.
- Segundo artículo sin existencias: se conserva el stock, los puntos y la ausencia de venta completa.
- Cantidades negativas, cero, no finitas, precisión excesiva y unidades fraccionarias: rechazadas.
- Precio alterado, total alterado, documento inválido, cliente inexistente y efectivo insuficiente: rechazados.
- Doble confirmación con el mismo identificador: una sola venta y el mismo comprobante.
- Identificador usado con un pedido distinto: rechazado.
- Dos ventas concurrentes de la última unidad: una aceptada y otra rechazada; stock final cero.
- Anulación repetida: una sola devolución de stock y puntos, conservando el comprobante.
- Canje sin saldo suficiente, con stock insuficiente o cantidad inválida: no deja descuentos parciales.
- Repetición y anulación del canje: efecto único sobre saldo e inventario.
- Puntos gastados: la anulación de venta se bloquea sin reversión parcial.
- Permisos por rol comprobados en navegación y acciones POST.
- CSRF ausente, sesión revocada, contraseña incorrecta y acceso anónimo: controles comprobados.
- Protección del último administrador y del stock cambiado por otra operación.
- Texto potencialmente malicioso escapado en plantillas.
- Formularios inválidos conservan valores; los campos revisados tienen etiquetas asociadas.
- Base antigua detectada antes de crear tablas nuevas: no se modifica su esquema.
- Interrupción simulada de conexión: pedido pendiente conservado y reintento con el mismo contenido.

## Reproducir

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Con Node.js 22 o posterior y el entorno Python activado:

```bash
npm ci
npm test
```

`npm test` exporta fixtures desde una base temporal y ejecuta las pruebas de comportamiento DOM y
estructura accesible. No abre un navegador ni modifica datos de trabajo.

## Comprobaciones necesarias en el equipo del estudiante

1. Ejecutar `INICIAR_WINDOWS.bat` y recorrer el flujo de ejemplo del README.
2. Revisar el aspecto en Chrome o Edge, a tamaño normal y con zoom.
3. Revisar navegación móvil, teclado, Escape en diálogos, foco y lector de pantalla.
4. Revisar impresión y la opción Guardar como PDF del navegador.
5. Probar en una base nueva MySQL/MariaDB con la configuración real, si se usará ese motor.
6. Aplicar el protocolo de evaluación a usuarios y registrar resultados reales.

No hay pruebas de carga, pentesting, certificación ISO/WCAG, integración tributaria ni aprobación del
negocio. Es una versión académica mejorada con validación técnica y pendientes explícitos.
