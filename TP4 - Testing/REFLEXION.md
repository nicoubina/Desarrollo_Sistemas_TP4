# Parte 5 — Reflexión

## 1. ¿Cuántos tests unitarios, de integración y E2E tenés? ¿Por qué esa proporción?

La entrega tiene 125 casos unitarios, 29 de integración y 46 end-to-end, contando cada combinación parametrizada como un caso ejecutado por pytest.
La mayor cantidad corresponde a unitarios porque las reglas de `checkout.py` tienen muchas particiones y límites que se pueden verificar sin base de datos ni servidor, como las cantidades 1 y 10 y el descuento desde cinco prendas.
Los tests de integración se concentran en R10 y necesitan SQLite real para comprobar transacciones, precisión de importes y consultas por email.
Hay más casos E2E que de integración porque R11 exige verificar dos endpoints y varias categorías de error, incluyendo cada campo obligatorio ausente o de otro tipo y los ocho errores de negocio.
Por eso la proporción responde a los requisitos y a los riesgos de este TP, aunque la parte superior de la pirámide tenga más casos que el nivel intermedio.
En la ejecución final pasan los 125 unitarios, mientras que en integración pasan 12 y fallan 17, y en E2E pasan 5 y fallan 41 por incumplimientos de los módulos recibidos.

## 2. ¿Qué falla de `pedidos.py` no podía encontrarse con un test unitario de `checkout.py`? ¿Por qué?

La falta de un commit final en `guardar_pedido` no podía detectarse probando solamente `checkout.py`.
Ese módulo calcula importes, pero no abre conexiones a SQLite ni controla cuándo una transacción queda confirmada.
El test `test_un_pedido_es_definitivo_con_todos_sus_items_en_otra_conexion` guarda una compra de dos ítems y la consulta inmediatamente desde otra conexión al mismo archivo.
La segunda conexión recupera una lista de ítems vacía, aunque la función de guardado ya terminó.
Leer únicamente desde la conexión que escribió podía ocultar el problema, porque esa conexión ve sus propios cambios pendientes.
La prueba demuestra que calcular bien el total no garantiza que el pedido quede guardado completo y disponible para el resto del sistema.

## 3. ¿Qué falla de `api.py` estaba en el paso de información entre dos partes del sistema? ¿Qué parte tendría que haberla resuelto?

Una falla concreta es que `api.py` recibe la fecha como texto JSON y la entrega a `pedidos.py`, que la pasa a `checkout.py` sin convertirla en un objeto `date`.
El contrato HTTP usa texto con formato `AAAA-MM-DD`, mientras que el contrato Python de `calcular_descuento` espera `date` o `None`.
En `test_post_interpreta_la_fecha_iso_y_acepta_el_ultimo_dia_del_cupon`, la compra con `EGRESADOS2026` y fecha `2026-11-30` devuelve 500 en vez de 201.
La API tendría que validar el formato y la existencia de la fecha y convertirla antes de llamar a la capa de persistencia.
Si la fecha es inválida, esa misma capa HTTP debe responder 400 con `FECHA_INVALIDA`, sin delegar la interpretación del JSON a `checkout.py`.
Con una fecha válida, checkout debe decidir la vigencia del cupón y la API debe traducir un eventual `CUPON_VENCIDO` a 422.

## 4. ¿Cuál de las fallas que encontraste habría sido la más cara de descubrir en producción? ¿Por qué?

Considero que la inyección SQL en `pedidos_de` habría sido la más costosa de descubrir en producción por la exposición de datos de otras personas.
La función coloca el email dentro de una consulta mediante una f-string, de modo que ese dato puede cambiar el significado del SQL.
En `test_el_email_es_un_dato_y_no_puede_alterar_la_consulta_sql`, la entrada `x' OR '1'='1` devuelve un pedido ajeno cuando el resultado esperado es una lista vacía.
En producción habría que corregir la consulta, investigar qué información se consultó y determinar el alcance de la exposición.
Aunque los errores de cobro y los pedidos incompletos también son graves, una filtración no se revierte solamente reparando el código porque los datos ya pudieron salir del sistema.
La protección correspondiente es tratar el email como un parámetro de la consulta y mantener estos casos de prueba para detectar regresiones.

## 5. ¿Qué mide la cobertura, qué mide la mutación y qué mide la inyección de fallas? ¿En qué se diferencian?

La cobertura mide qué partes del código se ejecutan durante las pruebas, pero no demuestra por sí sola que los resultados se comprueben correctamente.
En la suite unitaria final se recorren 31 de 32 ramas de `checkout.py`, es decir, el 96,875 %, mientras que el 99 % de la consola combina líneas y ramas.
La mutación evalúa la capacidad de los tests para detectar cambios pequeños introducidos en el código: la suite final detectó los 37 mutantes generados por `mutar.py`, con un puntaje del 100 %.
La inyección de fallas introduce condiciones de fallo controladas y permite evaluar si el sistema las detecta, contiene sus efectos y se recupera según lo esperado.
Un experimento posible para este TP sería provocar un error de escritura en SQLite y verificar que no queden un pedido o sus ítems guardados parcialmente.
Ese experimento adicional no se ejecutó: el test actual de atomicidad provoca un error de negocio real y comprueba que no se persistan datos, sin simular una avería de SQLite.
Las tres técnicas aportan evidencias distintas: recorrer caminos, detectar modificaciones incorrectas y responder a condiciones de fallo, por lo que un porcentaje alto en una no reemplaza las otras ni garantiza ausencia de bugs.

## 6. Si una IA escribiera tus tests de integración y E2E, ¿qué le faltaría probar? ¿Cómo lo comprobarías?

No daría por completa una suite generada por una IA solo porque sus tests pasen, porque podría concentrarse en crear un pedido válido y comprobar un status sin revisar el contrato completo.
Buscaría especialmente la lectura desde otra conexión, la ausencia de datos después de un error, la precisión Decimal, el precio enviado por el cliente y las consultas con emails que contienen SQL o apóstrofes.
En E2E revisaría que se prueben los montos como texto, las fechas, los campos ausentes o de otro tipo y cada código de error con su status y estructura JSON.
Por ejemplo, comprobar únicamente que el POST devuelve 201 no descubre que el GET posterior recupera importes cero e ítems vacíos, falla que aparece al atravesar las tres capas.
Para comprobar la suficiencia de los tests, relacionaría cada punto de R10 y cada endpoint y error de R11 con un caso concreto, como se hizo en `VERIFICACION_PARTE4.md`.
También revisaría los asserts y ejecutaría los tests contra los módulos recibidos, manteniendo visibles los 58 casos que detectan incumplimientos en lugar de ajustar sus esperados para aceptar esas fallas.
El resultado se evaluaría por la especificación y por la evidencia obtenida, sin asumir que haber usado una IA garantiza ni invalida la calidad de las pruebas.
