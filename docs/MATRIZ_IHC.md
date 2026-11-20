# Aplicación de criterios de IHC · Grifo El Olam

Estado: criterios incorporados al código y contrastados con pruebas técnicas. Esto no constituye una
certificación ni demuestra por sí solo que los usuarios tengan una buena experiencia. La eficacia,
eficiencia y satisfacción deben medirse con personas mediante el protocolo incluido.

## Las 10 heurísticas de Jakob Nielsen

| N.º | Criterio | Aplicación concreta | Evidencia / comprobación |
|---|---|---|---|
| H01 | Visibilidad del estado | Mensajes al cargar catálogo, consultar cliente y guardar; total y productos visibles | `sales.js`, estados con `role=status`, prueba DOM |
| H02 | Correspondencia con el mundo real | Soles, galones, unidades, efectivo, vuelto y puntos separados | Cantidades y precios del catálogo; prueba de venta mixta |
| H03 | Control y libertad | Cancelar formularios, volver al pedido, retirar y deshacer; anulación autorizada | Prueba DOM de deshacer; prueba de anulación única |
| H04 | Consistencia y estándares | Plantilla base, menú común, botones y estados con significado uniforme | `base.html`, `app.css`; recorrido de pantallas |
| H05 | Prevención de errores | Cantidades positivas, unidades enteras, stock, efectivo suficiente y revisión antes de confirmar | Pruebas de límites, venta inválida y falta de stock |
| H06 | Reconocimiento | Nombre, código, precio, cantidad y subtotal permanecen en el pedido | Catálogo y comprobante completo; revisar comprensión con usuarios |
| H07 | Flexibilidad y eficiencia | Búsqueda por nombre/código, filtros y entrada de combustible por importe o cantidad | Prueba DOM de búsqueda y equivalencia; medir tiempo de tareas |
| H08 | Estética y minimalismo | Jerarquía de información, secciones por tarea, acciones de cada rol y ayuda separada | Revisión de estructura; pendiente prueba visual en navegador |
| H09 | Reconocer y recuperarse de errores | Mensajes accionables, formularios con datos conservados, pedido recuperable y reintento seguro | Pruebas de formulario inválido y pérdida de conexión |
| H10 | Ayuda y documentación | Ayuda por tarea, instrucciones junto a campos y explicación de puntos y anulaciones | `/ayuda`, `README.md`; comprobar con un usuario nuevo |

No se añade un botón de borrado a una operación histórica para representar libertad: la anulación
conserva la trazabilidad. Deshacer retira y restaura filas del pedido antes de registrar la venta.

## Los 7 principios de Donald Norman del material del curso

Se conserva la lista del PDF «Principios de diseño de usabilidad de Donald Norman - S8 - 2026 - II (1)».
Su punto 4 se titula «Accesibilidad», pero el desarrollo describe **affordances o posibilidades de acción**.
No se confunde ese concepto con la accesibilidad digital evaluada mediante WCAG.

| N.º | Principio del material | Aplicación en el proyecto | Cómo comprobarlo |
|---|---|---|---|
| N01 | Descubrimiento | Nueva venta visible en el menú y en el resumen; botones nombran su acción | Pedir al usuario iniciar una venta sin indicarle dónde pulsar |
| N02 | Retroalimentación | Pedido y total cambian al agregar; resultados de búsqueda, guardado y canje | Prueba DOM y observación de comprensión del resultado |
| N03 | Modelo conceptual | Elegir productos → revisar pedido → confirmar → comprobante | Pedir al usuario explicar qué ocurrirá antes de confirmar |
| N04 | Posibilidades de acción | Botones distinguibles de texto, campos editables y opciones disponibles | Revisar si identifica dónde escribir y dónde actuar |
| N05 | Significantes | Etiquetas, unidades y textos «Agregar al pedido», «Anular venta», «Guardar» | Prueba de asociación entre botón y resultado esperado |
| N06 | Mapeo | Cantidad, equivalencia y subtotal junto al producto; total junto a confirmación | Modificar cantidad y observar si relaciona control y resultado |
| N07 | Restricciones | Unidades sin fracciones, stock suficiente, acciones por rol y revisión de canjes | Pruebas de datos inválidos, roles y saldo insuficiente |

## Las 8 reglas de Ben Shneiderman

Se usa la formulación publicada por el autor, que incluye usabilidad universal en la segunda regla.
Algunas ediciones antiguas la expresan con énfasis en atajos para usuarios frecuentes.

| N.º | Regla | Aplicación | Límite de la evidencia |
|---|---|---|---|
| S01 | Consistencia | Menú, formularios y componentes compartidos | Estructura comprobada; revisar en navegador |
| S02 | Usabilidad universal | Etiquetas, teclado nativo, foco visible, menú adaptable y reducción de movimiento | Pendientes lector de pantalla, ampliación y revisión móvil real |
| S03 | Retroalimentación informativa | Estados de carga, consulta y confirmación | Estados y cambios comprobados en DOM |
| S04 | Cierre de los diálogos | Comprobante final e historial después de registrar; éxito después de canjear | Venta y redirección comprobadas en backend |
| S05 | Prevención de errores | Validaciones y transacciones completas | Casos negativos automatizados |
| S06 | Reversibilidad | Deshacer en pedido y anular operaciones autorizadas | Deshacer y reversión única comprobados |
| S07 | Control del usuario | Confirmación explícita, cancelación y navegación por tarea | Pendiente observación con usuarios |
| S08 | Menor carga de memoria | Pedido, unidades y total visibles; ayuda contextual | Pendiente medir errores y aprendizaje |

## Mandel, presentado también por Pressman

| Regla | Aplicación |
|---|---|
| Mantener al usuario en control | Cancelar, revisar antes de confirmar, corregir el pedido y solicitar anulación |
| Reducir la carga de memoria | Catálogo con nombres y precios, cliente identificado, saldo y total visibles |
| Mantener consistencia | Componentes y navegación comunes; permisos coherentes entre pantalla y servidor |

## Cooper y Kendall

Cooper orienta el diseño hacia objetivos: se proponen cuatro perfiles de trabajo (caja, almacén,
supervisión y administración) y se restringe el menú a sus tareas. Son **perfiles de diseño provisionales**,
no personas validadas mediante entrevistas. Deben ajustarse a la investigación real.

Kendall aporta técnicas para conocer procesos y requisitos. El proyecto incorpora un protocolo de
entrevista y observación; no se inventaron participantes, transcripciones ni resultados.

## Accesibilidad digital considerada

| Aspecto | Implementación | Verificación pendiente |
|---|---|---|
| Lenguaje y estructura | `lang=es`, encabezados, navegación, tablas con encabezados y leyendas | Lector de pantalla y secuencia de lectura |
| Teclado | Controles HTML nativos, salto al contenido, foco visible, diálogos y menú móvil con salida | Recorrido completo en navegador, Escape y orden del foco |
| Campos | Etiquetas asociadas; obligatoriedad y unidades visibles | Comprensión por personas con diferentes habilidades |
| Errores | Resumen enfocable, mensajes específicos y datos conservados | Anuncio real en lector de pantalla |
| Estados | `role=status` y `role=alert` según el mensaje | Anuncios con tecnología de asistencia |
| Color | Estados incluyen texto, además de color; paleta con texto oscuro | Auditoría completa de contraste y componentes en estados interactivos |
| Adaptación | CSS para escritorio y móvil, tablas con desplazamiento propio | 320 px, zoom al 200/400%, orientación y controles táctiles |
| Movimiento | Respeta `prefers-reduced-motion` | Probar preferencia en dispositivo real |
| Acceso | Autocompletado de credenciales, pegar permitido, mostrar/ocultar contraseña | Revisar gestor de contraseñas y accesibilidad del inicio de sesión |

Las revisiones automáticas de estructura y DOM no cubren todos los criterios WCAG 2.2. No se afirma
conformidad AA completa. Ver `VALIDACION.md` y `EVALUACION_CON_USUARIOS.md`.

## Relación con el sílabo de IHC recibido

| Semanas / contenido | Aplicación actual | Trabajo que requiere evidencia de campo |
|---|---|---|
| 1–2: IHC y factores humanos | Tareas cortas, información visible y menor memorización | Observar atención, errores y aprendizaje |
| 3: DCU | Flujos e iteración previstos | Investigar contexto real y contrastar con usuarios |
| 4–5: UX y heurísticas | Matrices Nielsen y Norman, estados y recuperación | Evaluación heurística independiente y pruebas de tareas |
| 6–8: investigación | Instrumentos de entrevista y observación incluidos | Aplicar y registrar datos reales |
| 9–10: personas y recorridos | Roles y escenarios provisionales | Validar perfiles y construir journey basado en hallazgos |
| 11–12: arquitectura y UI | Navegación común, módulos por tarea y CSS adaptable | Card sorting si es necesario; verificar comprensión |
| 13: prototipado | Sistema funcional que puede probarse como prototipo de alta fidelidad | Conservar capturas y decisiones de iteración |
| 14: WCAG 2.2 | Medidas de accesibilidad incorporadas | Auditoría manual y con tecnologías de asistencia |
| 15: dispositivos emergentes | Interfaz adaptable a móvil | No se implementa asistente de voz; no se agrega sin una necesidad de usuario |
| 16–17: evaluación y métricas | Protocolo y registro de éxito, tiempo, errores y satisfacción | Ejecutar sesiones; no hay resultados ni prueba A/B fabricados |

## Referencias de trabajo

- Material y sílabos proporcionados por el estudiante, conservando la lista de Norman del docente.
- Nielsen: https://www.nngroup.com/articles/ten-usability-heuristics/
- Shneiderman, fuente del autor: https://www.cs.umd.edu/users/ben/goldenrules.html
- Mandel, fuente del autor: https://theomandel.com/resources/golden-rules-of-user-interface-design/
- W3C, foco visible: https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html
- W3C, mensajes de estado: https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html
- Cooper: *About Face*, referencia indicada en el sílabo. Kendall y Pressman se usan en el alcance
  previamente trabajado en clase; no se les atribuye la autoría de las diez heurísticas de Nielsen.
