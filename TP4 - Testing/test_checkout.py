from datetime import date
from decimal import Decimal

import pytest

import checkout
from checkout import (
    CheckoutError,
    calcular_descuento,
    calcular_envio,
    calcular_subtotal,
    calcular_total,
    validar_item,
)

HOY_VIGENTE = date(2026, 10, 1)


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def codigo_de_error(funcion, *args):
    with pytest.raises(CheckoutError) as error:
        funcion(*args)
    return error.value.code


def test_cantidad_cero_es_invalida():
    # Arrange
    invalido = item(cantidad=0)

    # Act
    codigo = codigo_de_error(validar_item, invalido)

    # Assert
    assert codigo == "CANTIDAD_INVALIDA"


def test_calcular_total_devuelve_importes_decimal_exactos():
    # Arrange
    carrito = [item("buzo", "M", 2)]

    # Act
    resultado = calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    # Assert
    assert {clave: type(valor) for clave, valor in resultado.items()} == {
        "subtotal": Decimal, "descuento": Decimal, "envio": Decimal, "total": Decimal,
    }
    assert resultado == {
        "subtotal": Decimal("49999.80"),
        "descuento": Decimal("0"),
        "envio": Decimal("2500"),
        "total": Decimal("52499.80"),
    }


def test_el_15_por_ciento_redondea_el_medio_centavo_hacia_arriba():
    # Arrange
    subtotal = Decimal("11999.50")  # 15% = 1799.925

    # Act
    descuento = calcular_descuento(subtotal, 1, "EGRESADOS2026", HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("1799.93")


def test_la_cantidad_maxima_10_es_valida():
    # Arrange
    carrito = [item("remera", "M", 10)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("119995.00")


def test_con_5_prendas_se_aplica_el_10_por_ciento():
    # Arrange
    subtotal = Decimal("59997.50")  # 5 remeras

    # Act
    descuento = calcular_descuento(subtotal, 5, None, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("5999.75")


def test_egresados2026_es_valido_el_30_de_noviembre_inclusive():
    # Arrange
    ultimo_dia = date(2026, 11, 30)

    # Act
    descuento = calcular_descuento(Decimal("11999.50"), 1, "EGRESADOS2026", ultimo_dia)

    # Assert
    assert descuento == Decimal("1799.93")


def test_el_precio_enviado_por_el_cliente_se_ignora():
    # Arrange
    carrito = [item("buzo", "M", 1, precio=Decimal("1"))]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("24999.90")


@pytest.mark.parametrize("producto", ["pantalon", "", "Buzo", " buzo ", None, 5, ["buzo"]])
def test_un_producto_fuera_del_catalogo_lanza_producto_inexistente(producto):
    # Arrange
    carrito = [item(producto, "M", 1)]

    # Act
    codigo = codigo_de_error(calcular_subtotal, carrito)

    # Assert
    assert codigo == "PRODUCTO_INEXISTENTE"


def test_el_producto_se_valida_antes_que_talle_y_cantidad():
    # Arrange
    invalido = item("pantalon", "XXXL", 0)

    # Act
    codigo = codigo_de_error(validar_item, invalido)

    # Assert
    assert codigo == "PRODUCTO_INEXISTENTE"


def test_validar_item_no_modifica_el_item_recibido():
    # Arrange
    recibido = item("buzo", "m", 1)
    copia = dict(recibido)

    # Act
    validar_item(recibido)

    # Assert
    assert recibido == copia


@pytest.mark.parametrize("talle", ["  M ", "xl\t", " xs"])
def test_un_talle_con_espacios_o_minusculas_es_valido(talle):
    # Arrange
    carrito = [item("remera", talle, 1)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("11999.50")


@pytest.mark.parametrize("talle", [None, 5])
def test_un_talle_de_otro_tipo_lanza_talle_invalido(talle):
    # Arrange
    invalido = item("buzo", talle, 1)

    # Act
    codigo = codigo_de_error(validar_item, invalido)

    # Assert
    assert codigo == "TALLE_INVALIDO"


@pytest.mark.parametrize("cantidad", [2.5, "2", None])
def test_una_cantidad_no_entera_lanza_cantidad_invalida(cantidad):
    # Arrange
    invalido = item("buzo", "M", cantidad)

    # Act
    codigo = codigo_de_error(validar_item, invalido)

    # Assert
    assert codigo == "CANTIDAD_INVALIDA"


def test_un_carrito_vacio_lanza_carrito_vacio():
    # Arrange
    carrito = []

    # Act
    codigo = codigo_de_error(calcular_total, carrito, "CABA")

    # Assert
    assert codigo == "CARRITO_VACIO"


@pytest.mark.parametrize("cupon, esperado", [
    ("EGRESADOS2026", Decimal("8999.63")),  # 15% > 10% (5999.75)
    ("BIENVENIDA", Decimal("5999.75")),     # 10% > 3000
])
def test_el_cupon_no_se_acumula_con_el_descuento_por_cantidad(cupon, esperado):
    # Arrange
    subtotal = Decimal("59997.50")  # 5 remeras

    # Act
    descuento = calcular_descuento(subtotal, 5, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == esperado


@pytest.mark.parametrize("cupon, subtotal, esperado", [
    ("  egresados2026 ", Decimal("11999.50"), Decimal("1799.93")),
    (" Bienvenida", Decimal("23999.00"), Decimal("3000")),
])
def test_el_cupon_ignora_mayusculas_y_espacios(cupon, subtotal, esperado):
    # Arrange
    prendas = 2

    # Act
    descuento = calcular_descuento(subtotal, prendas, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == esperado


@pytest.mark.parametrize("cupon", ["", "   "])
def test_un_cupon_vacio_equivale_a_no_usar_cupon(cupon):
    # Arrange
    subtotal = Decimal("11999.50")

    # Act
    descuento = calcular_descuento(subtotal, 1, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("0")


@pytest.mark.parametrize("cupon", ["DEBUG100", "DESCUENTO50", "EGRESADOS2025", "BIENVENIDA2"])
def test_solo_existen_dos_cupones(cupon):
    # Arrange
    subtotal = Decimal("24999.90")

    # Act
    codigo = codigo_de_error(calcular_descuento, subtotal, 1, cupon, HOY_VIGENTE)

    # Assert
    assert codigo == "CUPON_INVALIDO"


def fijar_hoy(monkeypatch, dia):
    monkeypatch.setattr(checkout, "date", type("HoyFijo", (date,), {"today": classmethod(lambda cls: dia)}))


@pytest.mark.parametrize("dia, esperado", [
    (date(2026, 11, 30), Decimal("1799.93")),
    (date(2026, 12, 1), "CUPON_VENCIDO"),
])
def test_sin_fecha_se_usa_el_dia_de_la_llamada(monkeypatch, dia, esperado):
    # Arrange
    fijar_hoy(monkeypatch, dia)
    carrito = [item("remera", "M", 1)]

    # Act
    try:
        resultado = calcular_total(carrito, "CABA", "EGRESADOS2026")["descuento"]
    except CheckoutError as error:
        resultado = error.code

    # Assert
    assert resultado == esperado


def test_fecha_none_explicita_equivale_a_omitirla(monkeypatch):
    # Arrange
    fijar_hoy(monkeypatch, date(2026, 11, 30))

    # Act
    descuento = calcular_descuento(Decimal("11999.50"), 1, "EGRESADOS2026", None)

    # Assert
    assert descuento == Decimal("1799.93")


@pytest.mark.parametrize("zona", ["MARTE", "C ABA", "", "   ", None])
def test_una_zona_inexistente_lanza_zona_invalida(zona):
    # Arrange
    subtotal = Decimal("11999.50")

    # Act
    codigo = codigo_de_error(calcular_envio, subtotal, zona)

    # Assert
    assert codigo == "ZONA_INVALIDA"


def test_el_envio_gratis_se_evalua_sobre_el_subtotal_ya_descontado():
    # Arrange
    carrito = [item("buzo", "M", 2), item("remera", "M", 1)]  # 61999.30 - 15% = 52699.40

    # Act
    resultado = calcular_total(carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)

    # Assert
    assert resultado["envio"] == Decimal("2500")
    assert resultado["total"] == Decimal("55199.40")


# --- Suite completa: particiones y bordes de CASOS.md ---


@pytest.mark.parametrize("producto, precio", [
    ("buzo", Decimal("24999.90")),
    ("remera", Decimal("11999.50")),
    ("campera", Decimal("47999.99")),
])
def test_cada_producto_cuesta_su_precio_de_catalogo(producto, precio):
    # Arrange
    carrito = [item(producto, "M", 1)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == precio


def test_el_subtotal_suma_precio_por_cantidad_de_cada_item_e_ignora_claves_extra():
    # Arrange
    carrito = [item("buzo", "M", 2, color="azul"), item("remera", "S", 1, precio_unitario="0.01")]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("61999.30")


@pytest.mark.parametrize("talle", ["XS", "S", "M", "L", "XL", "XXL"])
def test_los_seis_talles_validos_se_aceptan(talle):
    # Arrange
    carrito = [item("remera", talle, 1)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("11999.50")


@pytest.mark.parametrize("talle", ["XXS", "XXXL", "Medium", "", "   ", "X L"])
def test_un_talle_fuera_de_la_lista_lanza_talle_invalido(talle):
    # Arrange
    invalido = item("buzo", talle, 1)

    # Act
    codigo = codigo_de_error(validar_item, invalido)

    # Assert
    assert codigo == "TALLE_INVALIDO"


@pytest.mark.parametrize("cantidad", [-1, 0, 11])
def test_una_cantidad_fuera_de_1_a_10_lanza_cantidad_invalida(cantidad):
    # Arrange
    invalido = item("buzo", "M", cantidad)

    # Act
    codigo = codigo_de_error(validar_item, invalido)

    # Assert
    assert codigo == "CANTIDAD_INVALIDA"


@pytest.mark.parametrize("cantidad, subtotal", [
    (1, Decimal("11999.50")),
    (5, Decimal("59997.50")),
])
def test_las_cantidades_dentro_del_rango_son_validas(cantidad, subtotal):
    # Arrange
    carrito = [item("remera", "M", cantidad)]

    # Act
    resultado = calcular_subtotal(carrito)

    # Assert
    assert resultado == subtotal


def test_calcular_subtotal_con_carrito_vacio_lanza_carrito_vacio():
    # Arrange
    carrito = []

    # Act
    codigo = codigo_de_error(calcular_subtotal, carrito)

    # Assert
    assert codigo == "CARRITO_VACIO"


def test_calcular_total_no_modifica_el_carrito_ni_al_calcular_ni_al_fallar():
    # Arrange
    valido = [item("buzo", " m ", 1, color="azul")]
    invalido = [item("buzo", " m ", 1), item("pantalon", "M", 1)]
    copias = ([dict(i) for i in valido], [dict(i) for i in invalido])

    # Act
    calcular_total(valido, "CABA", " egresados2026 ", HOY_VIGENTE)
    codigo = codigo_de_error(calcular_total, invalido, "CABA")

    # Assert
    assert codigo == "PRODUCTO_INEXISTENTE"
    assert (valido, invalido) == copias


@pytest.mark.parametrize("prendas, subtotal, esperado", [
    (4, Decimal("47998.00"), Decimal("0")),
    (5, Decimal("59997.50"), Decimal("5999.75")),
    (6, Decimal("71997.00"), Decimal("7199.70")),
])
def test_el_descuento_por_cantidad_empieza_en_5_prendas(prendas, subtotal, esperado):
    # Arrange: subtotal y prendas provienen de los bordes parametrizados de R5.
    # Act
    descuento = calcular_descuento(subtotal, prendas, None, HOY_VIGENTE)

    # Assert
    assert descuento == esperado


def test_las_prendas_se_suman_entre_items():
    # Arrange
    carrito = [item("buzo", "M", 3), item("buzo", "L", 2)]

    # Act
    resultado = calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    # Assert
    assert resultado["descuento"] == Decimal("12499.95")


@pytest.mark.parametrize("dia", [date(2026, 1, 1), date(2026, 11, 29)])
def test_egresados2026_vigente_antes_del_vencimiento(dia):
    # Arrange
    subtotal = Decimal("11999.50")

    # Act
    descuento = calcular_descuento(subtotal, 1, "EGRESADOS2026", dia)

    # Assert
    assert descuento == Decimal("1799.93")


@pytest.mark.parametrize("dia", [date(2026, 12, 1), date(2027, 1, 1)])
def test_egresados2026_despues_del_30_de_noviembre_lanza_cupon_vencido(dia):
    # Arrange
    subtotal = Decimal("11999.50")

    # Act
    codigo = codigo_de_error(calcular_descuento, subtotal, 1, "EGRESADOS2026", dia)

    # Assert
    assert codigo == "CUPON_VENCIDO"


@pytest.mark.parametrize("subtotal", [Decimal("20000.00"), Decimal("20000.01")])
def test_bienvenida_descuenta_3000_desde_20000(subtotal):
    # Arrange
    cupon = "BIENVENIDA"

    # Act
    descuento = calcular_descuento(subtotal, 1, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("3000")


def test_bienvenida_debajo_de_20000_lanza_cupon_minimo_no_alcanzado():
    # Arrange
    subtotal = Decimal("19999.99")

    # Act
    codigo = codigo_de_error(calcular_descuento, subtotal, 1, "BIENVENIDA", HOY_VIGENTE)

    # Assert
    assert codigo == "CUPON_MINIMO_NO_ALCANZADO"


def test_bienvenida_no_tiene_vencimiento():
    # Arrange
    fecha_futura = date(2030, 1, 1)

    # Act
    descuento = calcular_descuento(Decimal("24999.90"), 1, "BIENVENIDA", fecha_futura)

    # Assert
    assert descuento == Decimal("3000")


def test_sin_cupon_no_hay_descuento():
    # Arrange
    subtotal = Decimal("11999.50")

    # Act
    descuento = calcular_descuento(subtotal, 1, None, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("0")


@pytest.mark.parametrize("subtotal, prendas, cupon, esperado", [
    (Decimal("24999.90"), 1, "EGRESADOS2026", Decimal("3749.99")),   # 3749.985
    (Decimal("61999.30"), 3, "EGRESADOS2026", Decimal("9299.90")),   # 9299.895
    (Decimal("47999.99"), 1, "EGRESADOS2026", Decimal("7200.00")),   # 7199.9985
    (Decimal("239999.95"), 5, None, Decimal("24000.00")),            # 23999.995
    (Decimal("10.04"), 5, None, Decimal("1.00")),                    # 1.004
    (Decimal("10.06"), 5, None, Decimal("1.01")),                    # 1.006
])
def test_los_descuentos_se_redondean_al_centavo_con_redondeo_comercial(subtotal, prendas, cupon, esperado):
    # Arrange: importes y esperados parametrizados calculados según R7.
    # Act
    descuento = calcular_descuento(subtotal, prendas, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == esperado


@pytest.mark.parametrize("zona, costo", [
    ("CABA", Decimal("2500")),
    ("GBA", Decimal("4000")),
    ("INTERIOR", Decimal("6500")),
    ("RETIRO", Decimal("0")),
    ("caba", Decimal("2500")),
    (" Gba ", Decimal("4000")),
    ("interior\n", Decimal("6500")),
])
def test_cada_zona_tiene_su_costo_de_envio(zona, costo):
    # Arrange
    subtotal = Decimal("11999.50")

    # Act
    envio = calcular_envio(subtotal, zona)

    # Assert
    assert envio == costo


@pytest.mark.parametrize("subtotal, envio", [
    (Decimal("59999.99"), Decimal("2500")),
    (Decimal("60000.00"), Decimal("0")),
    (Decimal("60000.01"), Decimal("0")),
])
def test_el_envio_es_gratis_desde_60000(subtotal, envio):
    # Arrange
    zona = "CABA"

    # Act
    resultado = calcular_envio(subtotal, zona)

    # Assert
    assert resultado == envio


@pytest.mark.parametrize("carrito, zona, cupon, esperado", [
    ([item("buzo", "M", 2)], "CABA", None, ("49999.80", "0", "2500", "52499.80")),
    ([item("remera", "M", 1)], "GBA", None, ("11999.50", "0", "4000", "15999.50")),
    ([item("remera", "M", 1)], "INTERIOR", None, ("11999.50", "0", "6500", "18499.50")),
    ([item("remera", "M", 1)], "RETIRO", None, ("11999.50", "0", "0", "11999.50")),
    ([item("remera", "M", 1)], "CABA", "EGRESADOS2026", ("11999.50", "1799.93", "2500", "12699.57")),
    ([item("campera", "M", 1)], "CABA", "EGRESADOS2026", ("47999.99", "7200.00", "2500", "43299.99")),
    ([item("buzo", "M", 1)], "CABA", "BIENVENIDA", ("24999.90", "3000", "2500", "24499.90")),
    ([item("remera", "M", 5)], "CABA", None, ("59997.50", "5999.75", "2500", "56497.75")),
    ([item("remera", "M", 5)], "CABA", "EGRESADOS2026", ("59997.50", "8999.63", "2500", "53497.87")),
    (
        [item("buzo", "M", 2), item("remera", "M", 3)],
        "RETIRO", None, ("85998.30", "8599.83", "0", "77398.47"),
    ),
    ([item("buzo", "M", 2), item("remera", "M", 1)], "CABA", None, ("61999.30", "0", "0", "61999.30")),
    ([item("buzo", "M", 5)], "CABA", "EGRESADOS2026", ("124999.50", "18749.93", "0", "106249.57")),
    ([item("campera", "M", 10)], "CABA", None, ("479999.90", "47999.99", "0", "431999.91")),
])
def test_el_total_es_subtotal_menos_descuento_mas_envio(carrito, zona, cupon, esperado):
    # Arrange
    claves = ("subtotal", "descuento", "envio", "total")
    importes_esperados = dict(zip(claves, map(Decimal, esperado), strict=True))

    # Act
    resultado = calcular_total(carrito, zona, cupon, HOY_VIGENTE)

    # Assert
    assert resultado == importes_esperados
    assert {clave: type(valor) for clave, valor in resultado.items()} == dict.fromkeys(claves, Decimal)


@pytest.mark.parametrize("carrito, zona, cupon, fecha, codigo", [
    ([], "MARTE", "NOEXISTE", HOY_VIGENTE, "CARRITO_VACIO"),
    ([item("pantalon", "XXXL", 0)], "MARTE", "NOEXISTE", HOY_VIGENTE, "PRODUCTO_INEXISTENTE"),
    ([item("buzo", "XXXL", 0)], "MARTE", "NOEXISTE", HOY_VIGENTE, "TALLE_INVALIDO"),
    ([item("buzo", "M", 0), item("pantalon", "M", 1)], "MARTE", None, HOY_VIGENTE, "CANTIDAD_INVALIDA"),
    ([item("remera", "M", 1)], "MARTE", "NOEXISTE", HOY_VIGENTE, "CUPON_INVALIDO"),
    ([item("remera", "M", 1)], "MARTE", "EGRESADOS2026", date(2026, 12, 1), "CUPON_VENCIDO"),
    ([item("remera", "M", 1)], "MARTE", "BIENVENIDA", HOY_VIGENTE, "CUPON_MINIMO_NO_ALCANZADO"),
    ([item("remera", "M", 1)], "MARTE", None, HOY_VIGENTE, "ZONA_INVALIDA"),
])
def test_calcular_total_informa_el_primer_error_segun_el_orden_de_validacion(
    carrito, zona, cupon, fecha, codigo,
):
    # Arrange: compra con errores simultáneos y primer código esperado según la sección 3.
    # Act
    resultado = codigo_de_error(calcular_total, carrito, zona, cupon, fecha)

    # Assert
    assert resultado == codigo


@pytest.mark.parametrize("campo, esperado", [
    ("producto", "PRODUCTO_INEXISTENTE"),
    ("talle", "TALLE_INVALIDO"),
    ("cantidad", "CANTIDAD_INVALIDA"),
])
def test_un_campo_faltante_informa_el_error_de_negocio(campo, esperado):
    # Arrange
    invalido = item()
    del invalido[campo]

    # Act
    codigo = codigo_de_error(validar_item, invalido)

    # Assert
    assert codigo == esperado


@pytest.mark.parametrize("cupon", [None, "", "   "])
def test_sin_cupon_se_conserva_el_descuento_por_cantidad(cupon):
    # Arrange
    subtotal = Decimal("59997.50")

    # Act
    descuento = calcular_descuento(subtotal, 5, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("5999.75")


@pytest.mark.parametrize("subtotal", [Decimal("11999.50"), Decimal("60000.00")])
def test_una_zona_invalida_se_rechaza_aunque_el_envio_pudiera_ser_gratis(subtotal):
    # Arrange
    zona = "MARTE"

    # Act
    codigo = codigo_de_error(calcular_envio, subtotal, zona)

    # Assert
    assert codigo == "ZONA_INVALIDA"
