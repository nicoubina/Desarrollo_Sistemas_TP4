import json
import threading
import urllib.error
import urllib.request
from decimal import Decimal

import pytest

import api

RUTA = "/api/v1/pedidos"


@pytest.fixture
def url(tmp_path):
    servidor = api.crear_servidor(str(tmp_path / "tienda.db"), 0)
    hilo = threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    hilo.start()
    try:
        yield f"http://127.0.0.1:{servidor.server_address[1]}"
    finally:
        servidor.shutdown()
        servidor.server_close()
        hilo.join(timeout=5)


def pedir(url, metodo, ruta, cuerpo=None, crudo=None):
    datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req = urllib.request.Request(url + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    cliente = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with cliente.open(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        with e:
            return e.code, json.loads(e.read() or b"null")


def compra(**cambios):
    cuerpo = {"email": "ana@mail.com", "zona": "CABA",
              "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]}
    cuerpo.update(cambios)
    return cuerpo


def test_una_ruta_inexistente_devuelve_404(url):
    # Arrange
    ruta = "/api/v1/otra"

    # Act
    status, cuerpo = pedir(url, "GET", ruta)

    # Assert
    assert status == 404
    comprobar_error(cuerpo, "RUTA_INEXISTENTE")


def comprobar_error(cuerpo, codigo):
    assert set(cuerpo) == {"error"}
    assert isinstance(cuerpo["error"], dict)
    assert set(cuerpo["error"]) == {"code", "message"}
    assert cuerpo["error"]["code"] == codigo
    assert isinstance(cuerpo["error"]["message"], str)
    assert cuerpo["error"]["message"].strip() != ""


def comprobar_importes(cuerpo, esperados):
    # R11 exige texto y valor exacto; no agrega un requisito de ceros finales.
    for campo, esperado in esperados.items():
        assert type(cuerpo[campo]) is str, f"{campo} debe viajar como texto: {cuerpo[campo]!r}"
        assert Decimal(cuerpo[campo]) == Decimal(esperado), campo


def test_post_crea_un_pedido_y_devuelve_importes_exactos_como_texto(url):
    # Arrange: sin fecha ni cupón, que son opcionales.
    cuerpo = compra(carrito=[{"producto": "buzo", "talle": "M", "cantidad": 2}])

    # Act
    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    # Assert
    assert status == 201
    assert type(respuesta["id"]) is int
    assert set(respuesta) == {"id", "subtotal", "descuento", "envio", "total"}
    comprobar_importes(respuesta, {
        "subtotal": "49999.80", "descuento": "0.00",
        "envio": "2500.00", "total": "52499.80",
    })


def test_get_recupera_el_pedido_completo_despues_del_post(url):
    # Arrange: el GET usa otra conexión; no se toca SQLite desde el test.
    cuerpo = compra(
        email=" ANA@MAIL.COM ", zona=" caba ", cupon=" bienvenida ", fecha="2026-10-01",
        carrito=[{"producto": "buzo", "talle": " m ", "cantidad": 1, "precio": 1}],
    )
    status_post, creado = pedir(url, "POST", RUTA, cuerpo)
    assert status_post == 201
    pedido_id = creado["id"]

    # Act
    status, recuperado = pedir(url, "GET", f"{RUTA}/{pedido_id}")

    # Assert
    assert status == 200
    comprobar_importes(recuperado, {
        "subtotal": "24999.90", "descuento": "3000.00", "envio": "2500.00", "total": "24499.90",
    })
    assert {k: recuperado[k] for k in ("id", "email", "zona", "cupon")} == {
        "id": pedido_id, "email": "ana@mail.com", "zona": "CABA", "cupon": "BIENVENIDA",
    }
    assert len(recuperado["items"]) == 1
    recuperado_item = recuperado["items"][0]
    comprobar_importes(recuperado_item, {"precio_unitario": "24999.90"})
    assert {k: recuperado_item[k] for k in ("producto", "talle", "cantidad")} == {
        "producto": "buzo", "talle": "M", "cantidad": 1,
    }


def test_post_interpreta_la_fecha_iso_y_acepta_el_ultimo_dia_del_cupon(url):
    # Arrange
    cuerpo = compra(
        carrito=[{"producto": "remera", "talle": "M", "cantidad": 1}],
        cupon=" egresados2026 ", fecha="2026-11-30",
    )

    # Act
    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    # Assert
    assert status == 201
    assert type(respuesta["id"]) is int
    comprobar_importes(respuesta, {
        "subtotal": "11999.50", "descuento": "1799.93",
        "envio": "2500.00", "total": "12699.57",
    })


@pytest.mark.parametrize("cambios, codigo", [
    ({"carrito": []}, "CARRITO_VACIO"),
    ({"carrito": [{"producto": "pantalon", "talle": "M", "cantidad": 1}]}, "PRODUCTO_INEXISTENTE"),
    ({"carrito": [{"producto": "buzo", "talle": "XXXL", "cantidad": 1}]}, "TALLE_INVALIDO"),
    ({"carrito": [{"producto": "buzo", "talle": "M", "cantidad": 0}]}, "CANTIDAD_INVALIDA"),
    ({"cupon": "NOEXISTE"}, "CUPON_INVALIDO"),
    ({"cupon": "EGRESADOS2026", "fecha": "2026-12-01"}, "CUPON_VENCIDO"),
    ({"cupon": "BIENVENIDA", "carrito": [{"producto": "remera", "talle": "M", "cantidad": 1}]},
     "CUPON_MINIMO_NO_ALCANZADO"),
    ({"zona": "MARTE"}, "ZONA_INVALIDA"),
])
def test_cada_error_de_negocio_devuelve_422_con_su_codigo(url, cambios, codigo):
    # Arrange
    cuerpo = compra(**cambios)

    # Act
    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    # Assert
    assert status == 422
    comprobar_error(respuesta, codigo)


@pytest.mark.parametrize("crudo", [b"{no es json", b"", b'{"email":'])
def test_un_cuerpo_que_no_es_json_valido_devuelve_400(url, crudo):
    # Arrange: bytes inválidos enviados por HTTP, sin serializarlos como otro JSON.
    # Act
    status, respuesta = pedir(url, "POST", RUTA, crudo=crudo)

    # Assert
    assert status == 400
    comprobar_error(respuesta, "JSON_INVALIDO")


@pytest.mark.parametrize("campo", ["email", "zona", "carrito"])
def test_un_campo_obligatorio_ausente_devuelve_datos_incompletos(url, campo):
    # Arrange
    cuerpo = compra()
    del cuerpo[campo]

    # Act
    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    # Assert
    assert status == 400
    comprobar_error(respuesta, "DATOS_INCOMPLETOS")


@pytest.mark.parametrize("campo, valor", [
    ("email", None), ("email", 5), ("email", []),
    ("zona", None), ("zona", 5), ("zona", []),
    ("carrito", None), ("carrito", "buzo"), ("carrito", {}),
])
def test_un_campo_obligatorio_de_otro_tipo_devuelve_datos_incompletos(url, campo, valor):
    # Arrange
    cuerpo = compra(**{campo: valor})

    # Act
    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    # Assert
    assert status == 400
    comprobar_error(respuesta, "DATOS_INCOMPLETOS")


@pytest.mark.parametrize("crudo", [b"null", b"[]", b'"texto"', b"123"])
def test_un_json_que_no_es_objeto_devuelve_datos_incompletos(url, crudo):
    # Arrange: JSON válido, pero no contiene los campos obligatorios.
    # Act
    status, respuesta = pedir(url, "POST", RUTA, crudo=crudo)

    # Assert
    assert status == 400
    comprobar_error(respuesta, "DATOS_INCOMPLETOS")


@pytest.mark.parametrize("fecha", ["30/11/2026", "2026-11-31", "2026-1-01", "", 20261130])
def test_una_fecha_sin_formato_iso_o_imposible_devuelve_400(url, fecha):
    # Arrange: sin cupón para exigir que la API valide la fecha independientemente del descuento.
    cuerpo = compra(fecha=fecha)

    # Act
    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    # Assert
    assert status == 400
    comprobar_error(respuesta, "FECHA_INVALIDA")


@pytest.mark.parametrize("pedido_id", [0, 999])
def test_get_de_un_pedido_inexistente_devuelve_404(url, pedido_id):
    # Arrange: base vacía y un id numérico sin pedido.
    # Act
    status, respuesta = pedir(url, "GET", f"{RUTA}/{pedido_id}")

    # Assert
    assert status == 404
    comprobar_error(respuesta, "PEDIDO_INEXISTENTE")


@pytest.mark.parametrize("metodo, ruta", [
    ("GET", "/otra"), ("POST", "/otra"),
    ("GET", "/api/v1/no-existe"), ("POST", "/api/v1/pedidos/1"),
])
def test_una_ruta_fuera_del_contrato_devuelve_error_json_404(url, metodo, ruta):
    # Arrange
    cuerpo = compra() if metodo == "POST" else None

    # Act
    status, respuesta = pedir(url, metodo, ruta, cuerpo)

    # Assert
    assert status == 404
    comprobar_error(respuesta, "RUTA_INEXISTENTE")


@pytest.mark.parametrize("cambios, esperado", [
    ({"carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1, "precio": 1}]},
     {"subtotal": "24999.90", "descuento": "0.00", "envio": "2500.00", "total": "27499.90"}),
    ({"carrito": [{"producto": "remera", "talle": "M", "cantidad": 5}]},
     {"subtotal": "59997.50", "descuento": "5999.75", "envio": "2500.00", "total": "56497.75"}),
    ({"zona": "RETIRO"},
     {"subtotal": "24999.90", "descuento": "0.00", "envio": "0.00", "total": "24999.90"}),
])
def test_post_respeta_los_importes_de_checkout_sin_aceptar_el_precio_del_cliente(url, cambios, esperado):
    # Arrange
    cuerpo = compra(**cambios)

    # Act
    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    # Assert
    assert status == 201
    comprobar_importes(respuesta, esperado)


def test_un_error_no_impide_crear_y_recuperar_la_compra_siguiente(url):
    # Arrange
    invalida = compra(carrito=[{"producto": "buzo", "talle": "M", "cantidad": 0}])
    valida = compra()

    # Act: tres requests reales al mismo servidor y la misma base.
    status_error, error = pedir(url, "POST", RUTA, invalida)
    status_post, creado = pedir(url, "POST", RUTA, valida)
    status_get, recuperado = pedir(url, "GET", f"{RUTA}/{creado['id']}")

    # Assert
    assert status_error == 422
    comprobar_error(error, "CANTIDAD_INVALIDA")
    assert status_post == 201
    assert status_get == 200
    assert recuperado["id"] == creado["id"]
    comprobar_importes(recuperado, {
        "subtotal": "24999.90", "descuento": "0", "envio": "2500", "total": "27499.90",
    })
