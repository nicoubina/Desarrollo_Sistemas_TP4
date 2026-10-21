from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest

import pedidos
from checkout import CheckoutError, calcular_total

HOY_VIGENTE = date(2026, 10, 1)


@pytest.fixture
def ruta(tmp_path):
    return str(tmp_path / "tienda.db")


@pytest.fixture
def con(ruta):
    conexion = pedidos.conectar(ruta)
    pedidos.crear_esquema(conexion)
    yield conexion
    conexion.close()


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def contar(ruta, tabla):
    assert tabla in ("pedidos", "items")
    otra = pedidos.conectar(ruta)
    try:
        return otra.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        otra.close()


def test_un_id_inexistente_devuelve_none(con):
    # Arrange
    pedido_id = 999

    # Act
    resultado = pedidos.obtener_pedido(con, pedido_id)

    # Assert
    assert resultado is None


@pytest.mark.parametrize("carrito, zona, cupon, fecha, codigo", [
    ([], "CABA", None, HOY_VIGENTE, "CARRITO_VACIO"),
    ([item(), item("pantalon")], "CABA", None, HOY_VIGENTE, "PRODUCTO_INEXISTENTE"),
    ([item(talle="XXXL")], "CABA", None, HOY_VIGENTE, "TALLE_INVALIDO"),
    ([item(cantidad=0)], "CABA", None, HOY_VIGENTE, "CANTIDAD_INVALIDA"),
    ([item()], "CABA", "NOEXISTE", HOY_VIGENTE, "CUPON_INVALIDO"),
    ([item()], "CABA", "EGRESADOS2026", date(2026, 12, 1), "CUPON_VENCIDO"),
    ([item("remera")], "CABA", "BIENVENIDA", HOY_VIGENTE, "CUPON_MINIMO_NO_ALCANZADO"),
    ([item()], "MARTE", None, HOY_VIGENTE, "ZONA_INVALIDA"),
])
def test_un_error_de_checkout_se_propaga_y_no_guarda_pedido_ni_items(
    con, ruta, carrito, zona, cupon, fecha, codigo,
):
    # Arrange: base nueva y compra inválida según R1-R8.
    # Act
    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, zona, cupon, fecha)

    # Assert: revisar también desde otra conexión, sin confirmar ni revertir a mano.
    assert error.value.code == codigo
    assert (contar(ruta, "pedidos"), contar(ruta, "items")) == (0, 0)
    assert con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0


def test_un_pedido_es_definitivo_con_todos_sus_items_en_otra_conexion(con, ruta):
    # Arrange
    carrito = [item("buzo", "M", 2), item("remera", "S", 1)]

    # Act: guardar_pedido debe confirmar por sí mismo; el test no llama commit.
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA", None, HOY_VIGENTE)
    otra = pedidos.conectar(ruta)
    try:
        recuperado = pedidos.obtener_pedido(otra, pedido_id)
    finally:
        otra.close()

    # Assert: comprobación estructural previa a la de importes para aislar la transacción.
    assert sorted(recuperado["items"], key=lambda i: i["producto"]) == [
        {"producto": "buzo", "talle": "M", "cantidad": 2, "precio_unitario": Decimal("24999.90")},
        {"producto": "remera", "talle": "S", "cantidad": 1, "precio_unitario": Decimal("11999.50")},
    ]
    assert {k: recuperado[k] for k in ("subtotal", "descuento", "envio", "total")} == {
        "subtotal": Decimal("61999.30"), "descuento": Decimal("0"),
        "envio": Decimal("0"), "total": Decimal("61999.30"),
    }


@pytest.mark.parametrize("campo", ["subtotal", "descuento", "envio", "total"])
def test_los_importes_recuperados_son_decimal_identicos_a_checkout(con, campo):
    # Arrange: cupón porcentual e importes no enteros para detectar pérdida en REAL.
    carrito = [item("remera")]
    esperado = calcular_total(carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)

    # Act: se lee en la misma conexión para aislar precisión de falta de commit.
    pedido_id = pedidos.guardar_pedido(
        con, "ana@mail.com", carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE,
    )
    recuperado = pedidos.obtener_pedido(con, pedido_id)

    # Assert
    assert type(recuperado[campo]) is Decimal
    assert recuperado[campo] == esperado[campo]


@pytest.mark.parametrize("extra", [{"precio": Decimal("1")}, {"precio_unitario": "0.01"}, {}])
def test_el_precio_unitario_guardado_es_el_del_catalogo(con, extra):
    # Arrange
    carrito = [item(**extra)]

    # Act
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "RETIRO", None, HOY_VIGENTE)
    precio = pedidos.obtener_pedido(con, pedido_id)["items"][0]["precio_unitario"]

    # Assert
    assert type(precio) is Decimal
    assert precio == Decimal("24999.90")


@pytest.mark.parametrize("cupon, normalizado", [
    ("  egresados2026 ", "EGRESADOS2026"),
    (" bienvenida ", "BIENVENIDA"),
    (None, None), ("", None), ("   ", None),
])
def test_los_datos_del_pedido_se_guardan_normalizados(con, cupon, normalizado):
    # Arrange
    carrito = [item(talle=" m ")]

    # Act
    pedido_id = pedidos.guardar_pedido(
        con, "  ANA@Mail.COM ", carrito, " caba ", cupon, HOY_VIGENTE,
    )
    recuperado = pedidos.obtener_pedido(con, pedido_id)

    # Assert
    assert (recuperado["email"], recuperado["zona"], recuperado["cupon"]) == (
        "ana@mail.com", "CABA", normalizado,
    )
    assert recuperado["items"][0]["talle"] == "M"


def test_guardar_pedido_no_modifica_el_carrito_del_llamador(con):
    # Arrange
    carrito = [item(talle=" m ", color={"opciones": ["azul"]})]
    copia = deepcopy(carrito)

    # Act
    pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA", None, HOY_VIGENTE)

    # Assert
    assert carrito == copia


@pytest.mark.parametrize("email", ["ana@mail.com", " ANA@MAIL.COM "])
def test_pedidos_de_filtra_el_email_normalizado_y_ordena_del_mas_reciente(con, email):
    # Arrange: tres pedidos reales; la consulta no debe incluir a otra persona.
    primero = pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA", None, HOY_VIGENTE)
    pedidos.guardar_pedido(con, "otra@mail.com", [item()], "CABA", None, HOY_VIGENTE)
    ultimo = pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA", None, HOY_VIGENTE)

    # Act
    resultados = pedidos.pedidos_de(con, email)

    # Assert
    assert [p["id"] for p in resultados] == [ultimo, primero]
    assert [p["email"] for p in resultados] == ["ana@mail.com", "ana@mail.com"]


@pytest.mark.parametrize("email", ["nadie@mail.com", "x' OR '1'='1", "x' OR 1=1 --"])
def test_el_email_es_un_dato_y_no_puede_alterar_la_consulta_sql(con, email):
    # Arrange
    pedidos.guardar_pedido(con, "privado@mail.com", [item()], "CABA", None, HOY_VIGENTE)

    # Act
    resultados = pedidos.pedidos_de(con, email)

    # Assert
    assert resultados == []


def test_un_email_con_apostrofe_se_consulta_como_dato_literal(con):
    # Arrange
    email = "o'connor@mail.com"
    pedido_id = pedidos.guardar_pedido(con, email, [item()], "CABA", None, HOY_VIGENTE)

    # Act
    resultados = pedidos.pedidos_de(con, email)

    # Assert
    assert [p["id"] for p in resultados] == [pedido_id]
