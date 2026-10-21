# AUDITORIA.md — Auditoría de la suite de la IA y hallazgos

## Sección 1: los tests de la IA

Todas las mediciones se hicieron sobre el **`checkout.py` original**, sin cambios
desde el commit `Estado inicial` (`65a88d5`), con el repositorio en `d59aae5`.
Entorno: Python 3.12.10, pytest 9.1.1, pytest-cov 7.1.0, en Windows. Para no
generar archivos en la entrega, se corrió sobre una copia de `checkout.py`,
`test_checkout_ia.py` y `mutar.py` en una carpeta temporal.

Resultado de `pytest test_checkout_ia.py -v`: **8 passed**.

### 1. Clasificación de los ocho tests

Criterio: un test **útil** compara contra un valor sacado de la especificación;
uno **débil** verifica algo real pero tan poco que deja pasar errores evidentes;
uno **tautológico** calcula el esperado con la misma fórmula o constante del
código, así que acompaña su error; uno **inútil** no verifica ningún requisito.

| # | Test | Clasificación | Por qué |
|---|---|---|---|
| 1 | `test_subtotal` | Tautológico | El esperado es `CATALOGO["buzo"] * 2`, la misma constante `float` del código: si el precio o el tipo están mal, el test también. |
| 2 | `test_total_funciona` | Inútil | `assert resultado is not None` no puede fallar con un dict; solo falla si se lanza una excepción, y no comprueba ningún importe. |
| 3 | `test_total_positivo` | Débil | `total > 0` acepta cualquier total positivo; sigue pasando si el envío se resta en vez de sumarse. |
| 4 | `test_cupon_egresados` | Débil | El 15% sale de la especificación y detectaría otro porcentaje, pero es un caso simple: no verifica `Decimal`, redondeo, el vencimiento del 30/11 ni la combinación con el descuento por cantidad. |
| 5 | `test_envio_caba` | Útil | Compara con el valor exacto de la tabla R8 (`2500`), aunque solo prueba CABA y lejos del umbral de $ 60.000. |
| 6 | `test_descuento_por_cantidad` | Útil | El esperado (`10000`, el 10% de R5) sale de la especificación, pero usa 6 prendas y no el borde de 5. |
| 7 | `test_talle_valido` | Débil | No tiene assert: solo comprueba que `"M"` no lance excepción; no prueba talles inválidos, minúsculas ni espacios. |
| 8 | `test_no_explota_con_varios_productos` | Inútil | El `try/except Exception: pass` traga cualquier error: **este test nunca puede fallar**, ni siquiera si `calcular_total` explota. |

Resumen: 2 útiles, 3 débiles, 1 tautológico y 2 inútiles. La diferencia entre
el 2 y el 8 es que el 2 todavía falla si el código lanza una excepción; el 8 no
puede fallar de ninguna manera.

### 2. Puntaje de mutación

```
python mutar.py --tests test_checkout_ia.py
Mutantes generados : 29
Muertos            : 17
Sobrevivientes     : 12
Puntaje de mutación: 58.6%
```

Los doce sobrevivientes y el caso de `CASOS.md` que ejercita ese punto:

| Línea | Mutación | Qué no ve la suite de la IA | Caso de `CASOS.md` |
|---:|---|---|---|
| 40 | `<` → `<=` | Nadie prueba la cantidad 10 ni la 11 | R3: cantidad `10` válida, `11` inválida (*) |
| 40 | `10` → `11` | Ídem, el límite superior | R3: cantidad `10` válida, `11` inválida (*) |
| 60 | `>` → `>=` | El test 6 usa 6 prendas, no el borde 5 | R5: 4 / 5 / 6 prendas (*) |
| 72 | `<` → `<=` | La fecha del test 4 es el 01/10, lejos del 30/11 | R6: 30/11/2026 válido, 01/12/2026 vencido (*) |
| 76 | `==` → `!=` | No hay ningún test con `BIENVENIDA` | R6: `BIENVENIDA` con subtotal `20000.00` → `3000.00` |
| 77 | `<` → `<=` | Ídem, el mínimo de `BIENVENIDA` | R6: subtotal `20000.00` aplica, `19999.99` no |
| 82 | `+` → `-` | Ídem, el importe del cupón fijo | R6: descuento `3000.00` exacto |
| 96 | `>=` → `>` | Ningún test llega a $ 60.000 | R8: `60000.00` → envío `0` |
| 96 | `60000` → `60001` | Ídem | R8: `60000.00` → envío `0` |
| 107 | `+` → `-` | Ningún test de `calcular_total` llega al descuento por cantidad | R5/R9: 5 remeras → descuento `5999.75` |
| 111 | `+` → `-` | El test 3 solo pide `total > 0` | R9: 2 buzos CABA → total `52499.80` |
| 111 | `-` → `+` | Ningún test de `calcular_total` tiene descuento | R9: 5 remeras CABA → total `56497.75` |

Ninguno de los doce es un mutante equivalente: cada uno cambia un resultado que
la especificación define.

(*) Estos cuatro mutantes corrigen el borde indicado (cantidad 10, 5 prendas,
30/11), sin arreglar el resto de las fallas de esas funciones: el código original
tiene ese borde mal y el mutante lo deja como pide la especificación.
Un test de ese borde no "mata" al mutante, sino que **falla contra el código
original**, y así deja a la vista la falla. Que sobrevivan muestra lo mismo:
ningún test de la IA mira esos bordes. Los otros ocho sí morirían con un test de
la especificación, porque el original los tiene bien y el mutante los rompe.

### 3. Por qué casi 80% de cobertura no detecta ninguna falla

Cobertura medida sobre el `checkout.py` original:

```
pytest test_checkout_ia.py --cov=checkout --cov-report=term-missing
checkout.py   62 stmts   14 miss   77%   (líneas)
pytest test_checkout_ia.py --cov=checkout --cov-branch --cov-report=term-missing
checkout.py   62 stmts   14 miss   26 branch   6 brpart   73%   Missing: 7-9, 38, 41, 50-51, 67, 73, 76-82, 91
```

El "casi 80%" del enunciado es la cobertura de líneas: 48/62 = 77,42%. El 73% que
muestra `--cov-branch` no es solo de ramas, sino la combinada de líneas y ramas:
(48 + 16) / (62 + 26) = 64/88 = 72,73%. Las ramas solas dan 16/26 = 61,54%. La
cobertura solo dice qué se ejecutó, no si alguien verificó el resultado:

- **Los asserts no verifican el valor correcto.** El test 2 acepta cualquier
  dict, el 3 cualquier positivo y el 8 nada. La línea 111 se ejecuta, pero
  cambiar `+ envio` por `- envio` no rompe ningún test.
- **Los esperados copian el código o son demasiado simples.** El test 1 importa
  `CATALOGO`, la misma constante `float` de la implementación, así que no puede
  detectar un precio o un tipo equivocado. El test 4 usa el 15% de la
  especificación, pero con un subtotal redondo en `float`, sin mirar el redondeo
  ni el tipo `Decimal`.
- **Se ejecutan las líneas, pero no los bordes.** Las comparaciones de las
  líneas 40, 60, 72 y 96 se recorren con valores lejos del límite (cantidad 1 y
  2, 6 prendas, 01/10/2026, $ 10.000). Por eso `>` por `>=` sobrevive aunque la
  línea esté "cubierta".
- **Solo el camino feliz.** Ningún test usa un dato inválido. Las líneas de
  error (38, 41, 67, 73, 91), `BIENVENIDA` (76-82) y el `except` de la 50-51
  nunca corren: justo ahí están las ramas que la especificación más detalla.
- **Las reglas que no son de un número no se miran.** Ningún test revisa que el
  carrito no cambie (R4), la normalización de cupón y talle (R2, R6), el orden
  de validación ni el tipo `Decimal` (R7).

La mutación lo confirma: con 77% de líneas cubiertas, el 41% de los mutantes
(12 de 29) sobrevive.

## Sección 2: hallazgos

Los números de línea son los de la **versión original** (commit `Estado inicial`,
`65a88d5`). "Cómo": **ruff** = lo marcó el linter; **lectura** = revisión línea
por línea; **prueba** = lo confirmé ejecutando el código con esa entrada sobre
una copia temporal. Severidad: **alta** = cobra mal, pierde o expone datos, o
rompe el flujo normal; **media** = rechaza datos válidos, acepta inválidos o da
otra excepción en un caso de error; **baja** = code smell sin efecto observable.

### `ruff check checkout.py`

5 errores: `F401` `json` sin usar (l. 1), `E722` `except` desnudo (l. 50),
`B008` `date.today()` como valor por defecto (l. 57 y 102), `E711` `!= None`
(l. 63). El linter solo encontró dos fallas reales por sí mismo (C4 y C18); el
resto de las fallas necesitó lectura y pruebas.

### `checkout.py`

| ID | Línea | Categoría | Regla | Entrada → resultado actual (esperado) | Cómo | Sev. |
|---|---|---|---|---|---|---|
| C1 | 13-15, 21-22, 27-30 | Numéricos | R7 | Todos los importes son `float`/`int`: `total([item("buzo","M",1)], "CABA")` → `float`, `int`, `int`, `float` (`Decimal`) | lectura, prueba | alta |
| C2 | 54, 84, 117 | Numéricos | R7 | `round()` sobre `float`: 15% de `11999.50` → `1799.92` (`1799.93`) | prueba | alta |
| C3 | 49 | Seguridad | R1 | `item("buzo","M",1)` + `"precio": 1` → subtotal `1` (`24999.90`) | lectura, prueba | alta |
| C4 | 48-51 | Manejo de errores | R1 | `item("pantalon","M",1)` → el ítem se saltea, total `2500` (`PRODUCTO_INEXISTENTE`) | ruff (E722), prueba | alta |
| C5 | 34-41 | Lógica | R1, sección 3 | `validar_item` no valida el producto: `item("pantalon","XXXL",1)` → `TALLE_INVALIDO` (`PRODUCTO_INEXISTENTE`) | lectura, prueba | media |
| C6 | 35 | Efectos laterales | R4 | `item("buzo","m",1)` queda con `"talle": "M"` después de `validar_item` (carrito sin cambios) | lectura, prueba | alta |
| C7 | 35 | Strings | R2 | `" M "` → `TALLE_INVALIDO` (válido) | prueba | media |
| C8 | 35 | Tipos | R2, sección 1 | talle `None` → `AttributeError`; sin clave → `KeyError` (`TALLE_INVALIDO`) | prueba | media |
| C9 | 40 | Lógica y límites | R3 | cantidad `10` → `CANTIDAD_INVALIDA` (válida) | lectura, prueba | alta |
| C10 | 40 | Tipos | R3 | `2.5` → aceptada, subtotal `62499.75`; `"2"` → `TypeError` (`CANTIDAD_INVALIDA`) | prueba | alta |
| C11 | 44-54 | Lógica | R4 | `total([], "CABA")` → total `2500` (`CARRITO_VACIO`) | prueba | media |
| C12 | 60 | Lógica y límites | R5 | 5 prendas → descuento `0` (10%) | lectura, prueba | alta |
| C13 | 61, 74 | Lógica | R6 | Cupón y cantidad se suman: 6 prendas + `EGRESADOS2026` sobre `59997.50` → `14999.38` (el mayor, `8999.63`) | lectura, prueba | alta |
| C14 | 64 | Strings | R6 | `"egresados2026"` → `CUPON_INVALIDO` (15%) | prueba | media |
| C15 | 63-67 | Lógica | R6 | `""` y `"   "` → `CUPON_INVALIDO` (sin cupón) | prueba | media |
| C16 | 23 | Seguridad | R6 | Cupón oculto `DEBUG100` (100%, vence en 2099): 6 buzos CABA → total `-14999.94` (`CUPON_INVALIDO`) | lectura, prueba | alta |
| C17 | 84 | Lógica | R6 | No se limita el descuento al subtotal: con C13 y C16 el total queda negativo. **Consecuencia** de C13 y C16, no una causa aparte | prueba | alta |
| C18 | 57, 102 | Fechas | R6 | `date.today()` se evalúa al importar el módulo: un servidor que sigue corriendo el 01/12/2026 sigue usando la fecha de arranque (día de la llamada) | ruff (B008) | media |
| C19 | 72 | Fechas / límites | R6 | `EGRESADOS2026` el 30/11/2026 → `CUPON_VENCIDO` (vigente, inclusive) | lectura, prueba | alta |
| C20 | 72 | Tipos / contrato entre capas | R6, sección 6 | `fecha=None` explícito, como lo manda `pedidos.py` → `TypeError` (usar el día de la llamada) | prueba | alta |
| C21 | 93 | Alucinación | R8 | `dict_keys` no tiene `.join`: zona `"MARTE"` → `AttributeError` (`ZONA_INVALIDA`) | lectura, prueba | alta |
| C22 | 88 | Tipos | R8, sección 1 | zona `None` → `AttributeError` (`ZONA_INVALIDA`) | lectura | baja |
| C23 | 110 | Lógica | R8 | El envío usa el subtotal sin descuento: 2 buzos + 1 remera con `EGRESADOS2026`, base `52699.40` → envío `0` (`2500`) | lectura, prueba | alta |
| C24 | 1, 63 | Code smell | — | `import json` sin usar, `!= None` | ruff (F401, E711) | baja |
| C25 | 60, 96, 21-30 | Code smell | — | Números mágicos (`5`, `0.10`, `60000`) mezclados con la lógica | lectura | baja |

### `pedidos.py`

| ID | Línea | Categoría | Regla | Entrada → resultado actual (esperado) | Cómo | Sev. |
|---|---|---|---|---|---|---|
| P1 | 39-50 | Manejo de errores / transacciones | R10 | Inserta y hace `commit` del pedido **antes** de `calcular_total`: con `item("buzo","M",0)` lanza el error pero queda 1 pedido visible desde otra conexión (nada guardado) | lectura, prueba | alta |
| P2 | 52-71 | Transacciones | R10 | Falta el `commit` final: tras guardar, otra conexión ve el pedido con importes `0.0` y sin ítems (definitivo y completo). El siguiente `commit` de la línea 48 confirma lo que quedó pendiente | lectura, prueba | alta |
| P3 | 63-69 | Manejo de errores | R10 | Con un producto inexistente (que C4 deja pasar), `CATALOGO[...]` lanza `KeyError` y queda el pedido y el primer ítem (`CheckoutError` y nada guardado). Agrava a P1 | prueba | alta |
| P4 | 12-15, 23, 55-58, 68, 88-97 | Numéricos | R10 | Columnas `REAL` y `float()`, luego `Decimal(float)`: un descuento `1799.92` se lee como `1799.920000000000072759576141834259033203125` (idéntico a `checkout`) | lectura, prueba | alta |
| P5 | 64 | Seguridad | R10 | `precio_unitario` sale de `item.get("precio", ...)`: guarda el precio del cliente (catálogo) | lectura | alta |
| P6 | 107 | Seguridad | R10 | SQL armado con f-string: `pedidos_de(con, "x' OR '1'='1")` → devuelve los 3 pedidos de otros (`[]`) | lectura, prueba | alta |
| P7 | 50 | Contrato entre capas | R10 | Pasa `fecha=None` a `calcular_total`; con `EGRESADOS2026` dispara C20. **Consecuencia** de C20 | prueba | alta |

### `api.py`

| ID | Línea | Categoría | Regla | Entrada → resultado actual (esperado) | Cómo | Sev. |
|---|---|---|---|---|---|---|
| A1 | 53-54, 67-68 | Manejo de errores | R11 | `except Exception` responde todo con 500 y `{"error": "texto"}`: cantidad `0` → 500 (422 `CANTIDAD_INVALIDA` con `{"error": {"code", "message"}}`) | lectura, prueba | alta |
| A2 | 32 | Manejo de errores | R11 | Cuerpo `{no` → 500 (400 `JSON_INVALIDO`) | prueba | alta |
| A3 | 37-39 | Manejo de errores / tipos | R11 | Sin `email` → 500 con `"'email'"`; no valida tipos (400 `DATOS_INCOMPLETOS`) | prueba | alta |
| A4 | 41 | Contrato entre capas | R11 | Pasa la fecha como texto a `checkout`: `EGRESADOS2026` + `"2026-11-01"` → 500 `TypeError` (201 con 15%) | lectura, prueba | alta |
| A5 | 41 | Fechas | R11 | `"fecha": "30/11/2026"` sin cupón → 201 (400 `FECHA_INVALIDA`); nunca valida el formato | prueba | media |
| A6 | 18 | Tipos / contrato | R11 | `json.dumps(default=float)`: montos como número JSON (`"total": 14499.5`) (texto `"14499.50"`) | lectura, prueba | alta |
| A7 | 64-66 | Manejo de errores | R11 | `GET /api/v1/pedidos/999` → 200 `null` (404 `PEDIDO_INEXISTENTE`) | lectura, prueba | alta |
| A8 | 34-44, 63-65 | Efectos laterales | R10, R11 | Por P2, `con.close()` descarta lo no confirmado: el `POST` responde los importes, pero el `GET` del mismo id devuelve `0.0` y `"items": []`. **Consecuencia** de P2 vista por HTTP | prueba | alta |
| A9 | 34, 44, 63-65 | Code smell | — | La conexión no se cierra en un `finally`; ante un error queda abierta | lectura | baja |

### Tabla de fallas, de la más grave a la menos grave

Dentro de cada severidad, primero las que afectan dinero o datos y después las
demás. Las marcadas **(consec.)** derivan de otra falla y no se cuentan como
causa aparte.

| # | ID | Archivo:línea | Falla | Sev. |
|---:|---|---|---|---|
| 1 | P6 | pedidos.py:107 | Inyección SQL en `pedidos_de` | alta |
| 2 | C16 | checkout.py:23 | Cupón oculto `DEBUG100` de 100% | alta |
| 3 | C3 | checkout.py:49 | Usa el precio que manda el cliente | alta |
| 4 | P5 | pedidos.py:64 | Guarda el precio del cliente | alta |
| 5 | C13 | checkout.py:61, 74 | Cupón y descuento por cantidad se acumulan | alta |
| 6 | C17 | checkout.py:84 | Descuento mayor que el subtotal, total negativo (consec. de C13 y C16) | alta |
| 7 | P1 | pedidos.py:39-50 | Pedido guardado aunque `checkout` falle | alta |
| 8 | P2 | pedidos.py:52-71 | Pedido no definitivo: sin `commit` final | alta |
| 9 | A8 | api.py:34-44 | El `GET` devuelve importes en 0 y sin ítems (consec. de P2) | alta |
| 10 | P3 | pedidos.py:63-69 | `KeyError` y pedido parcial con producto inexistente | alta |
| 11 | C4 | checkout.py:48-51 | Producto inexistente salteado en silencio | alta |
| 12 | C1 | checkout.py:13-30 | Dinero en `float`, nunca `Decimal` | alta |
| 13 | C2 | checkout.py:54, 84, 117 | Redondeo no comercial (`1799.92`) | alta |
| 14 | P4 | pedidos.py:12-97 | Montos guardados como `REAL`, leídos con pérdida | alta |
| 15 | A6 | api.py:18 | Montos como número JSON | alta |
| 16 | C23 | checkout.py:110 | Envío gratis calculado sin el descuento | alta |
| 17 | C12 | checkout.py:60 | 5 prendas no tienen el 10% | alta |
| 18 | C19 | checkout.py:72 | `EGRESADOS2026` rechazado el 30/11 | alta |
| 19 | C9 | checkout.py:40 | Cantidad 10 rechazada | alta |
| 20 | C10 | checkout.py:40 | Cantidad no entera aceptada o `TypeError` | alta |
| 21 | C6 | checkout.py:35 | `validar_item` modifica el carrito | alta |
| 22 | A4 | api.py:41 | Fecha como texto: 500 con cualquier cupón porcentual | alta |
| 23 | C20 | checkout.py:72 | `fecha=None` explícito da `TypeError` | alta |
| 24 | P7 | pedidos.py:50 | `fecha=None` hacia `checkout` (consec. de C20) | alta |
| 25 | C21 | checkout.py:93 | Método alucinado `dict_keys.join` | alta |
| 26 | A1 | api.py:53-54, 67-68 | Todo error responde 500 sin el formato del contrato | alta |
| 27 | A2 | api.py:32 | JSON inválido da 500 | alta |
| 28 | A3 | api.py:37-39 | Datos incompletos dan 500 | alta |
| 29 | A7 | api.py:64-66 | Pedido inexistente da 200 `null` | alta |
| 30 | C11 | checkout.py:44-54 | Carrito vacío aceptado | media |
| 31 | C5 | checkout.py:34-41 | Orden de validación: producto no validado primero | media |
| 32 | C18 | checkout.py:57, 102 | Fecha por defecto fijada al importar | media |
| 33 | C14 | checkout.py:64 | Cupón distingue mayúsculas | media |
| 34 | C15 | checkout.py:63-67 | Cupón vacío da `CUPON_INVALIDO` | media |
| 35 | C7 | checkout.py:35 | Talle con espacios rechazado | media |
| 36 | C8 | checkout.py:35 | Talle de otro tipo da `AttributeError` | media |
| 37 | A5 | api.py:41 | Fecha con formato inválido aceptada | media |
| 38 | C22 | checkout.py:88 | Zona de otro tipo da `AttributeError` | baja |
| 39 | C24 | checkout.py:1, 63 | Import sin usar y `!= None` | baja |
| 40 | C25 | checkout.py:60, 96 | Números mágicos | baja |
| 41 | A9 | api.py:34-65 | Conexión sin `finally` | baja |

Resumen: **41 hallazgos** (25 en `checkout.py`, 7 en `pedidos.py`, 9 en
`api.py`): 29 altos, 8 medios y 4 bajos. De ellos, 3 son consecuencias de otra
falla (C17, P7 y A8) y 3 son code smells (C24, C25 y A9), así que quedan **35
fallas con causa propia**.
Ruff por sí solo detectó 2 (C4 y C18).

Fuera de la tabla, por ser una interpretación y no una falla demostrada:
`PUT` o `DELETE` devuelven 501 con una página HTML, no un JSON de error. La
especificación no define esos métodos.
