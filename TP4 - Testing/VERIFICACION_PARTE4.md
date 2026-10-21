# Parte 4 — Integración y end-to-end

Verificación realizada el 21/10/2026 con Python 3.12.10 y pytest 9.1.1.

Se completaron `test_integracion.py` y `test_e2e.py`. Los tests usan una base
SQLite en archivo nueva por caso, conexiones reales y requests HTTP al
servidor real en 127.0.0.1 con un puerto libre asignado por el sistema.
Las fixtures cierran conexiones, servidor e hilo incluso cuando un assert falla.
No se usan mocks, skips ni xfails. No se modificaron `pedidos.py`, `api.py`,
`checkout.py` ni la especificación.

## Resultados

| Suite | Casos ejecutados | Pasan | Fallan | Errores de preparación |
| --- | ---: | ---: | ---: | ---: |
| Integración | 29 | 12 | 17 | 0 |
| E2E | 46 | 5 | 41 | 0 |
| Parte 4 completa | **75** | **17** | **58** | **0** |
| Regresión: unitarios de la Parte 3 | 125 | 125 | 0 | 0 |

`ruff check test_integracion.py test_e2e.py`: sin errores.

Las 58 fallas quedan visibles: la consigna exige probar los módulos
recibidos y encontrar sus incumplimientos, sin corregirlos. No son 58 bugs
distintos: varias entradas parametrizadas demuestran la misma causa.
La salida completa y los asserts fallidos están en `resultados_parte4.txt`.

## Cobertura de los siete puntos de R10

| Punto de R10 | Tests o escenarios | Resultado observado |
| --- | --- | --- |
| Propagar CheckoutError sin guardar pedido ni ítems | Los ocho códigos de negocio; producto inválido después de uno válido | El código del error se propaga, pero queda un pedido confirmado: `(1, 0)` en vez de `(0, 0)` |
| Pedido definitivo, completo y visible desde otra conexión | Dos ítems; segunda conexión inmediatamente después de guardar, sin commit del test | La segunda conexión recupera una lista de ítems vacía |
| Importes Decimal idénticos a checkout | Subtotal, descuento, envío y total con cupón porcentual | Los tipos son Decimal, pero descuento y total pierden precisión |
| Precio unitario del catálogo | Precio malicioso, clave precio_unitario extra y compra sin extras | Se guarda el precio malicioso; en los demás casos hay pérdida de precisión |
| Normalización | Email, zona, talle, ambos cupones y cupón None/vacío/espacios | Los cinco casos pasan al leer en la misma conexión |
| Id inexistente devuelve None | Consulta en base vacía | Pasa |
| Consulta por email normalizado, orden descendente y seguridad | Dos variantes del email, otra persona, email sin pedidos, dos inyecciones y apóstrofe literal | Normalización, filtro y orden pasan; las inyecciones exponen otro pedido y el apóstrofe produce OperationalError |

Se prueba además que guardar no modifique el carrito del llamador,
incluyendo una clave extra con datos anidados. Este test pasa.

Las lecturas de precisión y normalización usan la misma conexión para no
confundir esas reglas con la falta de commit. El test de visibilidad usa
otra conexión y no confirma ni revierte la transacción por su cuenta.
Los esperados de precisión se comparan con `calcular_total`, como pide R10;
precios unitarios y ejemplo de pedido completo tienen esperados literales
de la especificación.

## Cobertura de R11

| Endpoint o error requerido | Escenarios | Resultado observado |
| --- | --- | --- |
| POST exitoso | Compra mínima sin opcionales; compra con cupón y fecha ISO; precio enviado por cliente; descuento por cantidad; retiro | Los importes de las compras sin cupón porcentual se devuelven como números JSON. La compra con fecha y EGRESADOS2026 devuelve 500 |
| GET exitoso | Crear por POST y recuperar el pedido completo, normalizado y con ítems | El pedido recuperado contiene importes cero como números JSON y no cumple el formato esperado |
| Cada CheckoutError: 422 y código de negocio | Los ocho códigos de la sección 4 | Todos devuelven 500 en lugar de 422 |
| JSON inválido: 400 JSON_INVALIDO | JSON malformado, cuerpo vacío y JSON truncado | Devuelven 500 |
| Datos obligatorios: 400 DATOS_INCOMPLETOS | Cada campo ausente y tres tipos inválidos para cada campo | Devuelven 500 |
| Fecha: 400 FECHA_INVALIDA | Separadores incorrectos, mes sin dos dígitos y texto vacío | Se aceptan con 201 |
| Pedido inexistente: 404 PEDIDO_INEXISTENTE | Ids numéricos 0 y 999 en base vacía | Devuelven 200 con null |
| Ruta inexistente: 404 RUTA_INEXISTENTE | GET y POST fuera de las rutas declaradas | Los cinco casos pasan, incluido el ejemplo inicial |
| Recuperación después de un error | POST inválido, otro válido y GET de la compra válida, en el mismo servidor | El primer POST devuelve 500 en lugar de 422 |

Todos los tests de error verifican el status exacto y, cuando ese status
es correcto, el formato `{"error": {"code": ..., "message": ...}}`, el
código correspondiente y un mensaje de texto no vacío. Los tests de montos
exigen texto JSON y valor Decimal exacto, sin imponer ceros finales que el
contrato no exige.

Como casos adicionales se prueban cuatro cuerpos JSON que no son objetos
(faltan los datos obligatorios), una fecha imposible y una fecha numérica
(no son fechas válidas AAAA-MM-DD). Corresponden a las interpretaciones I6
e I7 ya documentadas en `CASOS.md`; también fallan contra la API recibida.

## Relación con la auditoría

- P1: pedido confirmado antes de validar la compra.
- P2 / A8: falta el commit final; el GET no recupera la compra completa.
- P4: conversión REAL/float/Decimal con pérdida de precisión.
- P5: precio unitario tomado del cliente.
- P6: interpolación del email en SQL.
- A1–A3: errores de negocio, JSON y campos obligatorios responden 500.
- A4–A5: falta la conversión y validación de fechas.
- A6: montos serializados como números JSON.
- A7: pedido inexistente responde 200 con null.

## Reproducción

Desde `TP4 - Testing`:

```powershell
python -m pytest test_integracion.py test_e2e.py -p no:cacheprovider --tb=short -ra
python -m pytest test_checkout.py -q -p no:cacheprovider
python -m ruff check test_integracion.py test_e2e.py
```

La primera orden sale con código 1 por las fallas demostradas. Las otras
dos salen con código 0. No hace falta levantar `api.py` manualmente.
En esta ejecución se permitió HTTP local: los errores de sockets del sandbox
de una ejecución inicial fueron descartados y no forman parte del reporte final.
