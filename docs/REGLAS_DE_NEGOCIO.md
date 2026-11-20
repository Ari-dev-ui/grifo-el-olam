# Reglas de negocio y decisiones de esta versión

| Tema | Regla implementada | Origen / alcance |
|---|---|---|
| Productos | Conserva los 23 productos del SQL recibido | Datos iniciales del proyecto; no se verifican precios actuales |
| Cantidades | Combustibles en galones, hasta 3 decimales; lubricantes y accesorios en unidades enteras | Corrige la incompatibilidad entre ventas fraccionarias e inventario entero |
| Dinero | Precios y totales persistidos en céntimos enteros; aritmética Decimal en servidor | Evita errores de coma flotante |
| Subtotal | Cantidad × precio vigente, redondeado a céntimos con ROUND_HALF_UP | Regla técnica explícita; todos los detalles suman el total |
| Venta por soles | La pantalla convierte soles a galones y redondea a 3 decimales; muestra el importe recalculado antes de agregar | El resultado puede diferir un céntimo del monto ingresado por la precisión de galones |
| Precios | El servidor valida el precio visto y recalcula el subtotal. Si cambió, bloquea para revisar | El cliente no controla el importe que se persiste |
| Existencias | Nunca negativas; descuentos y puntos se confirman en la misma transacción | Un error en cualquier producto revierte la operación entera |
| Concurrencia | Actualización condicional de stock; bloqueo de filas en MySQL; versión de ficha para edición | Dos cajas no deben vender la última unidad simultáneamente |
| Cliente | Opcional en ventas; obligatorio para acumular y canjear puntos | Si se escribe un documento, debe corresponder a un cliente activo |
| Puntos de venta | Por cada producto: round(cantidad × 0.2), redondeo al entero con empates al par; luego se suman | Conserva la fórmula efectiva del código original. Se valida con el negocio antes de uso real |
| Ejemplos | 10 gal → 2 pts; 2 und → 0 pts; 2.5 gal → 0 pts; 7.5 gal → 2 pts | Explica los empates al par del round original, sin sustituirlo silenciosamente por otra regla |
| Premios | Campo `reward_points` independiente del precio. Sin valor no se ofrece como premio | Corrige el uso anterior del precio truncado como si fueran puntos |
| Demo de premios | Ambientador 15 pts; líquido de frenos DOT 3, 30 pts | Costos iniciales ilustrativos, editables en inventario; no son un acuerdo comercial real |
| Canje | Cliente activo, cantidad entera, saldo y stock suficientes | Descuenta puntos y existencias juntos |
| Anulación de venta | Solo administrador/supervisor; requiere motivo; devuelve stock y revierte puntos una sola vez | Conserva la venta como Anulada; no borra registros |
| Puntos gastados | Si no alcanza el saldo para revertir una venta, se bloquea la anulación | Primero revisar y anular los canjes correspondientes; nunca dejar saldo negativo |
| Anulación de canje | Solo administrador/supervisor; devuelve stock y puntos una sola vez | Motivo almacenado en auditoría |
| Productos/clientes/usuarios | Desactivar conserva referencias históricas | No existe eliminación física desde la interfaz |
| Unidad de producto | No se convierte un código existente entre galones y unidades | Crear otro código; evita alterar el significado de movimientos anteriores |
| Identidad | DNI: 8 dígitos; RUC: 11 dígitos, únicamente formato | No valida existencia, titularidad ni dígito verificador tributario |
| Pago | Efectivo, Tarjeta o Yape | Registro interno; no confirma cobros externos |
| Comprobante | Conserva nombre, precio y cantidades de cada producto al vender | Interno y académico; sin numeración ni autorización electrónica SUNAT |
| Tiempo | Se guarda UTC; se muestra America/Lima; resumen según día peruano | Windows usa tzdata incluida en dependencias |
| Sesiones | 30 minutos deslizantes de inactividad; cambio de acceso invalida sesiones | La clave local de firma se genera una sola vez |
| Reintento | UUID único + huella del pedido; misma solicitud devuelve el comprobante existente | Cortes de red no deben duplicar ventas; pendiente bloquea edición hasta resolver |

Decisiones pendientes con el negocio: política comercial de puntos y premios, permisos definitivos de
supervisión, límites de venta, campos de identificación, política de datos y alcance de comprobantes.
El usuario final solo ve instrucciones útiles; los detalles técnicos permanecen en esta carpeta.
