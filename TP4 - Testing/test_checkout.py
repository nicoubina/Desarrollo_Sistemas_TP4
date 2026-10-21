from datetime import date
from decimal import Decimal

import pytest

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
    assert codigo_de_error(validar_item, item(cantidad=0)) == "CANTIDAD_INVALIDA"


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
