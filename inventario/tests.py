from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import DetalleVenta, Producto, Venta


class VentasFlowTests(TestCase):
    """Tests de flujo tradicional Django (ES01 / ES02)."""
    def setUp(self):
        self.producto = Producto.objects.create(nombre="Café", precio=Decimal("2500.00"), stock=10)

    def datos_venta(self, cantidad=2):
        return {
            "cliente": "Ana",
            "estado": "pagada",
            "observaciones": "",
            "detalles-TOTAL_FORMS": "1",
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
            "detalles-0-producto": str(self.producto.pk),
            "detalles-0-cantidad": str(cantidad),
        }

    def test_crear_venta_calcula_total_y_descuenta_stock(self):
        response = self.client.post("/ventas/nueva/", self.datos_venta())
        self.assertRedirects(response, "/ventas/1/")
        venta = Venta.objects.get()
        self.assertEqual(venta.total, Decimal("5000.00"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)

    def test_no_permite_vender_mas_stock_disponible(self):
        response = self.client.post("/ventas/nueva/", self.datos_venta(11))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Venta.objects.count(), 0)

    def test_eliminar_venta_restaura_stock(self):
        self.client.post("/ventas/nueva/", self.datos_venta())
        response = self.client.post("/ventas/1/eliminar/")
        self.assertRedirects(response, "/ventas/")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_reporte_filtra_por_fecha(self):
        self.client.post("/ventas/nueva/", self.datos_venta())
        response = self.client.get("/ventas/reporte/", {"desde": date.today().isoformat(), "hasta": date.today().isoformat()})
        self.assertContains(response, "$5.000")


class APIRestJwtCorsTests(APITestCase):
    """
    Tests automatizados para Evaluación Sumativa 3 (ES03):
    - Autenticación JWT (Obtención, Refresh y Protección de endpoints).
    - Permisos y Políticas de Acceso (IsAuthenticated).
    - Operaciones CRUD y lógica de negocio de Producto y Venta.
    - Manejo de stock transaccional en la API REST.
    - CORS headers.
    """

    def setUp(self):
        self.username = "testuser"
        self.password = "Secr3tP@ssw0rd!"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email="test@inacap.cl"
        )
        self.producto1 = Producto.objects.create(
            nombre="Teclado Mecánico",
            descripcion="Switches Blue RGB",
            precio=Decimal("45000.00"),
            stock=10,
            activo=True,
        )
        self.producto2 = Producto.objects.create(
            nombre="Mouse Gamer",
            descripcion="16000 DPI Óptico",
            precio=Decimal("25000.00"),
            stock=4,  # Stock crítico (<= 5)
            activo=True,
        )

    def _obtener_token(self):
        resp = self.client.post(
            "/api/token/",
            {"username": self.username, "password": self.password},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return resp.data["access"], resp.data["refresh"]

    # 1. Tests de Autenticación SimpleJWT (3.1.2)
    def test_obtener_token_jwt_valido(self):
        access, refresh = self._obtener_token()
        self.assertTrue(bool(access))
        self.assertTrue(bool(refresh))

    def test_obtener_token_jwt_credenciales_invalidas(self):
        resp = self.client.post(
            "/api/token/",
            {"username": self.username, "password": "WrongPassword"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refrescar_token_jwt(self):
        _, refresh = self._obtener_token()
        resp = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

    # 2. Tests de Permisos y Protección de Endpoints (3.1.1, 3.1.2)
    def test_endpoint_sin_token_retorna_401(self):
        resp = self.client.get("/api/productos/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_endpoint_con_token_bearer_retorna_200(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.get("/api/productos/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # 3. Tests CRUD Producto (3.1.3, 3.1.4)
    def test_crear_producto_via_api(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        payload = {
            "nombre": "Monitor 144Hz",
            "descripcion": "Panel IPS 24 pulgadas",
            "precio": "150000.00",
            "stock": 8,
            "activo": True,
        }
        resp = self.client.post("/api/productos/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["nombre"], "Monitor 144Hz")
        self.assertEqual(Producto.objects.filter(nombre="Monitor 144Hz").count(), 1)

    def test_crear_producto_validacion_precio_invalido(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        payload = {
            "nombre": "Producto Inválido",
            "precio": "-1000.00",
            "stock": 5,
        }
        resp = self.client.post("/api/productos/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accion_stock_critico(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.get("/api/productos/stock-critico/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Mouse Gamer tiene stock 4 <= 5
        results = resp.data.get("results", resp.data)
        nombres = [p["nombre"] for p in results]
        self.assertIn("Mouse Gamer", nombres)
        self.assertNotIn("Teclado Mecánico", nombres)

    # 4. Tests CRUD Venta y Lógica de Negocio de Stock (3.1.3)
    def test_crear_venta_descuenta_stock_atomicamente(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        payload = {
            "cliente": "Carlos Perez",
            "estado": "pagada",
            "observaciones": "Compra web vía API",
            "detalles": [
                {"producto": self.producto1.pk, "cantidad": 2},
                {"producto": self.producto2.pk, "cantidad": 1},
            ],
        }
        resp = self.client.post("/api/ventas/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Verificar descuento de stock
        self.producto1.refresh_from_db()
        self.producto2.refresh_from_db()
        self.assertEqual(self.producto1.stock, 8)  # 10 - 2
        self.assertEqual(self.producto2.stock, 3)  # 4 - 1

        # Verificar total calculado
        total_esperado = Decimal("45000.00") * 2 + Decimal("25000.00") * 1
        self.assertEqual(Decimal(str(resp.data["total"])), total_esperado)

    def test_crear_venta_rechaza_por_stock_insuficiente(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        payload = {
            "cliente": "Cliente Excedido",
            "detalles": [
                {"producto": self.producto2.pk, "cantidad": 10},  # Hay solo 4
            ],
        }
        resp = self.client.post("/api/ventas/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.producto2.refresh_from_db()
        self.assertEqual(self.producto2.stock, 4)  # No se descuenta nada

    def test_anular_venta_restaura_stock(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        # Crear venta
        payload = {
            "cliente": "Cliente Para Anular",
            "detalles": [{"producto": self.producto1.pk, "cantidad": 3}],
        }
        resp = self.client.post("/api/ventas/", payload, format="json")
        venta_id = resp.data["id"]
        self.producto1.refresh_from_db()
        self.assertEqual(self.producto1.stock, 7)

        # Anular venta vía POST /api/ventas/{id}/anular/
        resp_anular = self.client.post(f"/api/ventas/{venta_id}/anular/")
        self.assertEqual(resp_anular.status_code, status.HTTP_200_OK)

        # Verificar stock restaurado
        self.producto1.refresh_from_db()
        self.assertEqual(self.producto1.stock, 10)

    def test_eliminar_venta_restaura_stock(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        payload = {
            "cliente": "Cliente Eliminar",
            "detalles": [{"producto": self.producto1.pk, "cantidad": 4}],
        }
        resp = self.client.post("/api/ventas/", payload, format="json")
        venta_id = resp.data["id"]
        self.producto1.refresh_from_db()
        self.assertEqual(self.producto1.stock, 6)

        # DELETE /api/ventas/{id}/
        resp_del = self.client.delete(f"/api/ventas/{venta_id}/")
        self.assertEqual(resp_del.status_code, status.HTTP_204_NO_CONTENT)

        self.producto1.refresh_from_db()
        self.assertEqual(self.producto1.stock, 10)

    # 5. Endpoint de Estadísticas y Perfil
    def test_dashboard_stats_endpoint(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.get("/api/dashboard-stats/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("ventas_totales_monto", resp.data)
        self.assertIn("stock_critico_count", resp.data)
        self.assertIn("chart_labels", resp.data)

    def test_perfil_endpoint(self):
        access, _ = self._obtener_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.get("/api/perfil/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], self.username)

    # 6. Test CORS Headers (3.1.4 / CORS)
    def test_cors_headers_permitidos(self):
        origin = "http://localhost:3000"
        resp = self.client.options(
            "/api/productos/",
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
        )
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), origin)
