# CASOS.md — Casos de prueba de caja negra

Diseñados solo a partir de `ESPECIFICACION.md`, antes de abrir el código. Los
esperados numéricos salen de la tabla de precios y de los porcentajes de la
especificación, calculados a mano.

**Convenciones**

- `D("x")` es `Decimal("x")`. Un importe esperado se verifica por **tipo
  `Decimal` y valor** (`D("0") == D("0.00")`); la especificación no exige una
  cantidad de decimales en `checkout`.
- `item(p, t, c)` es `{"producto": p, "talle": t, "cantidad": c}`, siempre con
  los tres campos. Si una fila solo cambia uno, los otros valen `"buzo"`, `"M"`
  y `1`, y se escribe completo: `item("buzo", "M", 0)`.
- `total(carrito, zona, cupon, fecha)` es `calcular_total`; `f` es una fecha
  vigente cualquiera (por ejemplo `date(2026, 10, 1)`).
- "→ `CODIGO`" = `CheckoutError` con ese `code`, nunca otra excepción (sección 1).
- Precios: buzo 24.999,90 · remera 11.999,50 · campera 47.999,99.
- Nivel: **U** unitario · **I** integración (SQLite real) · **E** end-to-end (HTTP real).
- Las tablas por regla contienen solo **requisitos explícitos**. Las lecturas
  propias de puntos que la especificación no define están aparte, en la última
  sección, y no son tests obligatorios.

---

## R1 — Catálogo y precios

| Partición | Entrada | Esperado | Nivel |
|---|---|---|---|
| Cada producto del catálogo | `calcular_subtotal([item(p, "M", 1)])` con `buzo`, `remera`, `campera` | `D("24999.90")`, `D("11999.50")`, `D("47999.99")` | U |
| Varios ítems: Σ precio × cantidad | `[item("buzo","M",2), item("remera","S",1)]` | `D("61999.30")` | U |
| Precio del cliente ignorado | `item("buzo","M",1)` más `"precio": 1` o `"precio_unitario": "0.01"` | `D("24999.90")` | U |
| Otras claves ignoradas | `item("remera","M",1)` más `"color": "azul"` | `D("11999.50")` | U |
| Fuera del catálogo | `"pantalon"`, `""` | → `PRODUCTO_INEXISTENTE` | U |
| No es el nombre exacto | `"Buzo"`, `"BUZO"`, `" buzo "` | → `PRODUCTO_INEXISTENTE` | U |
| Valor de otro tipo (no está en el catálogo) | `None`, `5`, `["buzo"]` | → `PRODUCTO_INEXISTENTE` | U |
| Precio del catálogo al guardar | `guardar_pedido` con `"precio": 1` en el ítem | `precio_unitario == D("24999.90")` | I |
| Precio del catálogo por HTTP | `POST` con `"precio": 1` en el ítem | `subtotal == "24999.90"` | E |

## R2 — Talles

| Partición | Entrada `talle` en `validar_item(item("buzo", t, 1))` | Esperado | Nivel |
|---|---|---|---|
| Los seis válidos | `XS`, `S`, `M`, `L`, `XL`, `XXL` | no lanza | U |
| Válido en minúscula o mixto | `"m"`, `"Xs"`, `"xxl"` | no lanza | U |
| Válido con espacios alrededor | `"  M "`, `"XL\t"` | no lanza | U |
| Inválido al lado de un válido (límites de la lista) | `"XXS"`, `"XXXL"` | → `TALLE_INVALIDO` | U |
| Otro texto, vacío o espacio interno | `"Medium"`, `""`, `"   "`, `"X L"` | → `TALLE_INVALIDO` | U |
| Valor de otro tipo | `None`, `5` | → `TALLE_INVALIDO` | U |

## R3 — Cantidad

| Partición | Entrada `cantidad` en `validar_item(item("buzo", "M", n))` | Esperado | Nivel |
|---|---|---|---|
| Debajo del rango | `-1`, `0` | → `CANTIDAD_INVALIDA` | U |
| Bordes válidos e interior | `1`, `5`, `10` | no lanza | U |
| Encima del rango | `11` | → `CANTIDAD_INVALIDA` | U |
| No entero | `2.5`, `"2"`, `None` | → `CANTIDAD_INVALIDA` | U |
| La cantidad máxima se multiplica bien | `calcular_subtotal([item("remera","M",10)])` | `D("119995.00")` | U |

## R4 — Carrito

| Partición | Entrada | Esperado | Nivel |
|---|---|---|---|
| Vacío | `calcular_subtotal([])`, `total([], "CABA")` | → `CARRITO_VACIO` | U |
| Uno o varios ítems | `[item("buzo","M",1)]`; `[item("buzo","M",1), item("buzo","L",2)]` | válidos; el segundo, subtotal `D("74999.70")` | U |
| No se modifica (éxito) | carrito con `item("buzo"," m ",1)` más una clave extra; `validar_item`, `calcular_subtotal` y `total(..., " egresados2026 ", f)` | el carrito queda igual a una copia profunda tomada antes | U |
| No se modifica (error) | carrito `[item("buzo"," m ",1), item("pantalon","M",1)]` en `total` | lanza y el carrito queda igual a la copia | U |
| No se modifica al guardar | `guardar_pedido` con `item("buzo"," m ",1)` | el carrito del llamador no cambia | I |

## R5 — Descuento por cantidad

| Partición | Entrada | Esperado | Nivel |
|---|---|---|---|
| Debajo del umbral (4) | `calcular_descuento(D("47998.00"), 4)` | `D("0")` | U |
| Borde (5) | `calcular_descuento(D("59997.50"), 5)` | `D("5999.75")` | U |
| Encima (6) | `calcular_descuento(D("71997.00"), 6)` | `D("7199.70")` | U |
| La cantidad se suma entre ítems (3 + 2) | `total([item("buzo","M",3), item("buzo","L",2)], "CABA")` | descuento `D("12499.95")` | U |

## R6 — Cupones

`r` = subtotal de una remera, `D("11999.50")`.

| Partición | Entrada | Esperado | Nivel |
|---|---|---|---|
| Sin cupón | `calcular_descuento(r, 1, c, f)` con `None`, `""`, `"   "` | `D("0")`, no es error | U |
| `EGRESADOS2026` vigente | `calcular_descuento(r, 1, "EGRESADOS2026", d)` con `d` = 01/01/2026 y 29/11/2026 | `D("1799.93")` | U |
| **Borde de vigencia** | ídem con `d` = 30/11/2026 | `D("1799.93")` | U |
| Vencido | ídem con `d` = 01/12/2026 | → `CUPON_VENCIDO` | U |
| `BIENVENIDA` con subtotal ≥ mínimo | `calcular_descuento(s, 1, "BIENVENIDA", f)` con `s` = `20000.00` (borde) y `20000.01` | `D("3000.00")` | U |
| `BIENVENIDA` con subtotal < mínimo | ídem con `s` = `19999.99`; y `total([item("remera","M",1)], "CABA", "BIENVENIDA", f)` | → `CUPON_MINIMO_NO_ALCANZADO` | U |
| `BIENVENIDA` no tiene vencimiento | `calcular_descuento(D("24999.90"), 1, "BIENVENIDA", date(2030,1,1))` | `D("3000.00")` | U |
| Código inexistente (solo hay dos) | `"DESCUENTO50"`, `"EGRESADOS2025"`, `"BIENVENIDA2"`, `"ADMIN"` | → `CUPON_INVALIDO` | U |
| Mayúsculas y espacios | `"egresados2026"`, `"  Bienvenida "` | igual que el código original | U |
| No acumula: gana el cupón % | 5 remeras + `EGRESADOS2026`: 15% `8999.63` > 10% `5999.75` | descuento `D("8999.63")` | U |
| No acumula: gana la cantidad | 5 remeras + `BIENVENIDA`: `5999.75` > `3000.00` | descuento `D("5999.75")` | U |
| Sin R5, solo cupón fijo | 4 remeras + `BIENVENIDA` | descuento `D("3000.00")` | U |
| Descuento ≤ subtotal | invariante en todos los casos válidos | `descuento <= subtotal` | U |
| **Fecha omitida = día de la llamada** | `total([item("remera","M",1)], "CABA", "EGRESADOS2026")` sin `fecha`, con el día de la llamada controlado en el test | llamada el 30/11/2026 → descuento `D("1799.93")`; llamada el 01/12/2026 → `CUPON_VENCIDO` | U |
| Cupón por HTTP | `POST` con `"cupon": "EGRESADOS2026"` y `"fecha": "2026-11-30"` / `"2026-12-01"` | 201 / 422 `CUPON_VENCIDO` | E |

El mecanismo para controlar el día de la llamada se decide al implementar el test.

## R7 — Dinero y redondeo

| Partición | Entrada | Esperado | Nivel |
|---|---|---|---|
| Todos los importes son `Decimal` | los cuatro valores de cualquier `total(...)` válido | `type(v) is Decimal` | U |
| Sin error de `float` | `calcular_subtotal([item("buzo","M",3)])`; `[item("remera","M",7)]` | `D("74999.70")`; `D("83996.50")` | U |
| Medio centavo hacia arriba (ejemplo de la spec) | 15% de `11999.50` = `1799.925` | `D("1799.93")` | U |
| Medio centavo con otros precios | 15% de `24999.90` = `3749.985`; 15% de `61999.30` = `9299.895`; 10% de `239999.95` (5 camperas) = `23999.995` | `D("3749.99")`; `D("9299.90")`; `D("24000.00")` | U |
| Debajo y encima de la mitad | `calcular_descuento(D("10.04"), 5)` = `1.004`; `calcular_descuento(D("10.06"), 5)` = `1.006` | `D("1.00")`; `D("1.01")` | U |
| Redondeo que llega al entero | 15% de `47999.99` = `7199.9985` | `D("7200.00")` | U |

## R8 — Envío

| Partición | Entrada | Esperado | Nivel |
|---|---|---|---|
| Cada zona | `calcular_envio(D("11999.50"), z)` con `CABA`, `GBA`, `INTERIOR`, `RETIRO` | `2500`, `4000`, `6500`, `0` (`Decimal`) | U |
| Mayúsculas y espacios | `"caba"`, `" Gba "`, `"interior\n"` | igual que la zona original | U |
| Zona inexistente o vacía | `"MARTE"`, `"C ABA"`, `""`, `"   "` | → `ZONA_INVALIDA` | U |
| Zona de otro tipo | `None`, `5` | → `ZONA_INVALIDA` | U |
| **Borde del envío gratis** | `calcular_envio(s, "CABA")` con `s` = `59999.99` / `60000.00` / `60000.01` | `D("2500")` / `D("0")` / `D("0")` | U |
| El umbral usa el subtotal **ya descontado** | 2 buzos + 1 remera (`61999.30`) con `EGRESADOS2026`, CABA: base `52699.40` | envío `D("2500")`, total `D("55199.40")` | U |
| Mismo carrito sin descuento | ídem sin cupón (3 prendas): base `61999.30` | envío `D("0")`, total `D("61999.30")` | U |

## R9 — Total

`total = subtotal − descuento + envío`; el resultado tiene exactamente las claves
`subtotal`, `descuento`, `envio`, `total`.

| Escenario (zona CABA salvo que se diga) | subtotal | descuento | envío | total | Nivel |
|---|---:|---:|---:|---:|---|
| Ejemplo de la spec: 2 buzos, sin cupón | 49999.80 | 0 | 2500 | **52499.80** | U |
| 1 remera en GBA / INTERIOR / RETIRO | 11999.50 | 0 | 4000 / 6500 / 0 | 15999.50 / 18499.50 / 11999.50 | U |
| 1 remera, `EGRESADOS2026`, 30/11/2026 | 11999.50 | 1799.93 | 2500 | **12699.57** | U |
| 1 campera, `EGRESADOS2026` | 47999.99 | 7200.00 | 2500 | 43299.99 | U |
| 1 buzo, `BIENVENIDA` | 24999.90 | 3000.00 | 2500 | 24499.90 | U |
| 5 remeras, sin cupón | 59997.50 | 5999.75 | 2500 | 56497.75 | U |
| 5 remeras, `EGRESADOS2026` | 59997.50 | 8999.63 | 2500 | 53497.87 | U |
| 2 buzos + 3 remeras, RETIRO | 85998.30 | 8599.83 | 0 | 77398.47 | U |
| 5 buzos, `EGRESADOS2026` (gana 15% a 10%, envío gratis) | 124999.50 | 18749.93 | 0 | 106249.57 | U |
| 10 camperas (máximo) | 479999.90 | 47999.99 | 0 | 431999.91 | U |
| Claves del resultado | — | — | — | `{"subtotal","descuento","envio","total"}` | U |

## R10 — Persistencia (`pedidos.py`)

Base SQLite real en un archivo temporal, nueva para cada test, sin mocks.
"Otra conexión" es una segunda `pedidos.conectar(ruta)` a la misma base. Los ids
siempre se toman de lo que devuelve `guardar_pedido`; no se asume su valor ni
que sean consecutivos.

| Oración de la regla | Entrada | Esperado | Nivel |
|---|---|---|---|
| **El `CheckoutError` se propaga** | `guardar_pedido` con `item("buzo","M",0)`; también con zona `"MARTE"` y con cupón `"NOEXISTE"` | `CheckoutError` con `CANTIDAD_INVALIDA` / `ZONA_INVALIDA` / `CUPON_INVALIDO` | I |
| **No queda nada guardado** | tras el error, contar filas desde la misma conexión y desde otra | 0 pedidos y 0 ítems en ambas | I |
| Ídem si el error está en un ítem posterior | `[item("buzo","M",1), item("pantalon","M",1)]` | `PRODUCTO_INEXISTENTE` y 0 ítems (no queda el primero) | I |
| Un guardado válido posterior no arrastra el intento fallido | error y luego un pedido válido con la misma conexión | desde otra conexión: un solo pedido, con los ítems del válido | I |
| Un error no altera pedidos anteriores | guardar A, fallar B | `obtener_pedido(A)` igual que antes y un solo pedido en la base | I |
| **Definitivo al terminar** | guardar un pedido de 2 ítems y, sin cerrar la conexión, leer desde otra | lo ve completo con sus 2 ítems | I |
| `guardar_pedido` devuelve el id | el valor devuelto | es `int`, `obtener_pedido(con, id)["id"] == id`; dos pedidos dan ids distintos | I |
| **Montos idénticos, `Decimal`** | pedido de la spec (1 remera M, `EGRESADOS2026`, CABA, 30/11/2026) | igual al dict de la sección 6 salvo `id`: `subtotal 11999.50`, `descuento 1799.93`, `envio 2500.00`, `total 12699.57`, `precio_unitario 11999.50`, todos `Decimal` | I |
| Montos iguales a `checkout` | 5 camperas, CABA | los cuatro montos `==` a `calcular_total` con el mismo carrito | I |
| **`precio_unitario` del catálogo** | ítem con `"precio": 1` | `D("24999.90")` | I |
| **Normalización** | email `"  Ana@Mail.COM "`, zona `" caba "`, talle `" m "`, cupón `" egresados2026 "` | `"ana@mail.com"`, `"CABA"`, `"M"`, `"EGRESADOS2026"` | I |
| Cupón vacío → `None` | cupón `""`, `"   "` o `None` | `pedido["cupon"] is None` | I |
| **Id inexistente** | `obtener_pedido(con, id_guardado + 1000)` en una base con un pedido; y en una base vacía | `None` | I |
| **`pedidos_de` ignora mayúsculas y espacios** | guardar con `"ana@mail.com"`, consultar `"  ANA@Mail.com "` | contiene ese pedido | I |
| Solo los del email consultado | pedidos de dos emails | cada consulta trae solo los suyos | I |
| Sin pedidos | email que nunca compró | `[]` | I |
| **Más reciente primero** | guardar A, B y C del mismo email | ids en el orden `[id_C, id_B, id_A]` | I |
| **El email no altera la consulta** | `pedidos_de(con, "x' OR '1'='1")` con pedidos de otros | `[]` | I |
| Ídem con una sentencia | `pedidos_de(con, "x'; DROP TABLE pedidos; --")` | `[]` y después se puede guardar y leer normalmente | I |
| Email con comilla | guardar y consultar `"o'brien@mail.com"` | lo encuentra | I |

## R11 — API HTTP (`api.py`)

Servidor real con `crear_servidor(ruta_archivo, 0)`, requests HTTP reales y base en
archivo temporal; se apaga y cierra al terminar cada test. Los ids se toman de la
respuesta del `POST`.

| Endpoint / flujo | Entrada | Esperado | Nivel |
|---|---|---|---|
| `POST` mínimo (sin `cupon` ni `fecha`) | `email`, `zona`, `carrito` | 201; `id` entero; `subtotal`, `descuento`, `envio`, `total` como texto | E |
| `POST` completo | compra de la spec (`cupon` y `fecha`) | 201 con `"subtotal":"11999.50"`, `"descuento":"1799.93"`, `"envio":"2500.00"`, `"total":"12699.57"` | E |
| `GET /api/v1/pedidos/{id}` tras el `POST` | id devuelto | 200 con el formato de la sección 6: email normalizado, zona en mayúscula, `items` con `precio_unitario` del catálogo; **todo monto como texto, nunca número JSON** | E |
| Error y recuperación | `POST` con 422, luego `POST` válido y `GET` de su id | el válido da 201 y el `GET` devuelve esa compra | E |

| Situación (tabla de errores) | Entrada | Status | `code` |
|---|---|:---:|---|
| Cada `CheckoutError` | `POST` con: producto `"pantalon"` · talle `"XXXL"` · cantidad `0` · carrito `[]` · cupón `"NOEXISTE"` · `EGRESADOS2026` + `"2026-12-01"` · `BIENVENIDA` con 1 remera · zona `"MARTE"` | 422 | el del `CheckoutError` (los ocho de la sección 4) |
| Cuerpo no es JSON | `{no es json`; cuerpo vacío | 400 | `JSON_INVALIDO` |
| Falta un campo obligatorio | sin `email`; sin `zona`; sin `carrito` | 400 | `DATOS_INCOMPLETOS` |
| Campo con otro tipo | `"email": 123`; `"zona": null`; `"carrito": "buzo"` o `{}` | 400 | `DATOS_INCOMPLETOS` |
| Fecha sin formato `AAAA-MM-DD` | `"30/11/2026"`, `"2026-1-5"`, `"hoy"`, `""` | 400 | `FECHA_INVALIDA` |
| Pedido inexistente | `GET /api/v1/pedidos/{id_creado + 1000}` | 404 | `PEDIDO_INEXISTENTE` |
| Ruta inexistente | `GET /api/v1/otra`; `POST /api/v1/otra` | 404 | `RUTA_INEXISTENTE` |
| Formato de todo error | cualquiera de los anteriores | — | cuerpo `{"error": {"code": ..., "message": ...}}` |
| Nunca 500 | todas las entradas inválidas de esta tabla | distinto de 500 | — |

---

## Orden de validación en `calcular_total` (sección 3)

Primero carrito vacío, luego cada ítem en orden (producto → talle → cantidad),
luego cupón y por último zona.

| Combinación | Entrada | Esperado |
|---|---|---|
| Carrito vacío antes que todo | `total([], "MARTE", "NOEXISTE", f)` | `CARRITO_VACIO` |
| Ítem antes que cupón y zona | `total([item("pantalon","XXXL",0)], "MARTE", "NOEXISTE", f)` | `PRODUCTO_INEXISTENTE` |
| Dentro del ítem: talle antes que cantidad | `item("buzo","XXXL",0)` | `TALLE_INVALIDO` |
| Entre ítems: gana el primero | `[item("buzo","M",0), item("pantalon","M",1)]` | `CANTIDAD_INVALIDA` |
| Cupón antes que zona (los tres errores de cupón) | `item("remera","M",1)` + zona `"MARTE"` con `"NOEXISTE"` / `EGRESADOS2026` el 01/12/2026 / `BIENVENIDA` | `CUPON_INVALIDO` / `CUPON_VENCIDO` / `CUPON_MINIMO_NO_ALCANZADO` |

Los ocho códigos de la sección 4 están cubiertos: `PRODUCTO_INEXISTENTE` (R1),
`TALLE_INVALIDO` (R2), `CANTIDAD_INVALIDA` (R3), `CARRITO_VACIO` (R4),
`CUPON_INVALIDO`, `CUPON_VENCIDO` y `CUPON_MINIMO_NO_ALCANZADO` (R6),
`ZONA_INVALIDA` (R8).

---

## Interpretaciones (la especificación no lo define; no son tests obligatorios)

| # | Punto abierto | Lectura elegida | Caso posible |
|---|---|---|---|
| I1 | Ítem al que le falta una clave | El `code` de la regla de esa clave, porque la sección 1 prohíbe otra excepción | `{"talle":"M","cantidad":1}` → `PRODUCTO_INEXISTENTE` |
| I2 | `True` y `2.0` como cantidad | Inválidos: un booleano o un float no es una cantidad entera | → `CANTIDAD_INVALIDA` (para preguntarle al profesor) |
| I3 | `carrito=None` | Equivale a carrito sin ítems | → `CARRITO_VACIO` |
| I4 | Orden de `items` en `obtener_pedido` | El del carrito recibido | 3 ítems salen en el mismo orden |
| I5 | Formato de cada elemento de `pedidos_de` | El mismo de `obtener_pedido` | `pedidos_de(...)[0] == obtener_pedido(id)` |
| I6 | JSON válido que no es un objeto | Faltan los datos obligatorios | `[]`, `5`, `null` → 400 `DATOS_INCOMPLETOS` |
| I7 | Fecha con formato correcto pero imposible, o que no es texto | No es una fecha `AAAA-MM-DD` válida | `"2026-02-30"`, `"2026-13-01"`, `20261130` → 400 `FECHA_INVALIDA` |
| I8 | `GET /api/v1/pedidos/abc` | Es 404; el `code` puede ser cualquiera de los dos | 404 y nunca 500 |
| I9 | Métodos no definidos (`PUT`, `DELETE`) y precedencia entre errores 400 y 422 | Sin valor exacto exigible | solo comprobar que no sea 500 |
