# Verificación de la Parte 3

Fecha: 21/10/2026. Entorno: Windows, Python 3.12.10, pytest 9.1.1,
pytest-cov 7.1.0 y coverage 7.16.2.

## Suite y correcciones

Se conservaron los siete tests iniciales y se completó la suite hasta **125
casos ejecutados**, incluyendo las parametrizaciones. Los esperados se basan
en R1–R9 y en el orden de validación de la especificación.

Se verifican los precios de los tres productos, claves extra ignoradas,
validación de producto/talle/cantidad, campos faltantes, carrito vacío,
ausencia de modificaciones al carrito, suma de prendas entre ítems, ambos
cupones, normalización, vencimiento inclusive, mínimo de BIENVENIDA, fecha
del día de la llamada, selección del mayor descuento, redondeo comercial,
tarifas y umbral del envío, tipos Decimal, totales exactos y prioridad de errores.

La versión corregida valida sin modificar los ítems, rechaza productos y
cantidades inválidos, rechaza carritos vacíos, elimina DEBUG100, normaliza
cupones, evita acumular descuentos, obtiene la fecha al llamar y calcula el
envío sobre el subtotal descontado. Las zonas inválidas producen CheckoutError.

## Resultados reales

| Verificación | Resultado | Requisito |
| --- | --- | --- |
| Tests unitarios | 125 aprobados, ninguno omitido | Todos pasan |
| Líneas | 69/69 = 100 % | Informativo |
| Ramas | 31/32 = **96,875 %** | Al menos 85 % |
| Cobertura combinada | 100/101 = 99,0099 %; consola: 99 % | Informativo |
| Mutación | **37/37 detectados = 100 %**, 0 sobrevivientes | Al menos 85 % |
| Ruff | Sin errores en checkout.py y test_checkout.py | Verificación de estilo |

El 99 % de `cobertura.txt` combina líneas y ramas; no es el porcentaje de
ramas aisladas. La única rama sin recorrer (`85->93`) corresponde a un
tipo de cupón distinto de porcentaje o fijo. Los únicos dos cupones
permitidos tienen esos tipos; no se alteró el catálogo para forzar esa rama.
No se agregaron exclusiones de cobertura ni se modificó `mutar.py`.

Comandos ejecutados desde esta carpeta:

```powershell
python -m pytest test_checkout.py -p no:cacheprovider --cov=checkout --cov-branch --cov-report=term-missing
python mutar.py
python -m ruff check checkout.py test_checkout.py
```

Las salidas se guardaron en `cobertura.txt` y `mutacion.txt`.

## Historial TDD existente

Se reprodujeron los siguientes seis pares en carpetas temporales, usando
`checkout.py` y `test_checkout.py` de cada commit y ejecutando el test nuevo
de ese par. En los seis casos el test falló en el commit test (salida 1) y
pasó en el commit fix (salida 0). Esto supera el mínimo de cinco pares.

| Comportamiento | Commit test: falla | Commit fix: pasa |
| --- | --- | --- |
| Importes Decimal y total exacto | 40ebae5 | a384f51 |
| Medio centavo hacia arriba | f7b0d07 | 86d52cd |
| Cantidad máxima 10 inclusive | ddc33f5 | 3a593e5 |
| Descuento desde 5 prendas | 54c0935 | 3a5293f |
| Cupón vigente el 30/11 inclusive | d47f0ee | d8f9029 |
| Precio del cliente ignorado | f8f3f62 | b23720f |

Esta entrega reúne las ampliaciones y correcciones restantes en un único
commit por indicación del usuario y conserva esos pares anteriores.
