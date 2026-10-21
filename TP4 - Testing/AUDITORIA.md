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

*(Se completa en la etapa siguiente.)*
