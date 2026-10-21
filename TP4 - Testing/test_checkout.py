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
