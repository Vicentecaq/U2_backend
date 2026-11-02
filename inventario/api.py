from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

from .models import DetalleVenta, Producto, Venta
from .serializers import (
    DetalleVentaSerializer,
    ProductoSerializer,
    UserSerializer,
    VentaCreateSerializer,
    VentaSerializer,
)


class ProductoViewSet(viewsets.ModelViewSet):
    """
    API REST ViewSet para el modelo Producto.
    Permite operaciones CRUD completas, búsqueda, ordenación y filtrado.
    """
    queryset = Producto.objects.all().order_by("nombre")
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["activo", "stock"]
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["nombre", "precio", "stock", "id"]

    @action(detail=False, methods=["get"], url_path="stock-critico")
    def stock_critico(self, request):
        """Devuelve productos cuyo stock es menor o igual a 5 unidades."""
        criticos = self.get_queryset().filter(stock__lte=5)
        page = self.paginate_queryset(criticos)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(criticos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="activos")
    def activos(self, request):
        """Devuelve únicamente productos activos con stock disponible."""
        activos = self.get_queryset().filter(activo=True, stock__gt=0)
        serializer = self.get_serializer(activos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="ajustar-stock")
    def ajustar_stock(self, request, pk=None):
        """
        Permite aumentar o disminuir el stock de un producto directamente.
        Payload esperado: {"cantidad": 5, "operacion": "sumar"|"restar"|"fijar"}
        """
        producto = self.get_object()
        cantidad = request.data.get("cantidad")
        operacion = request.data.get("operacion", "sumar")

        if cantidad is None:
            return Response(
                {"error": "Debe especificar el campo 'cantidad'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cant = int(cantidad)
        except (ValueError, TypeError):
            return Response(
                {"error": "El campo 'cantidad' debe ser un número entero válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if operacion == "sumar":
            producto.stock += max(0, cant)
        elif operacion == "restar":
            if producto.stock < cant:
                return Response(
                    {"error": f"Stock insuficiente para restar. Stock actual: {producto.stock}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            producto.stock -= cant
        elif operacion == "fijar":
            if cant < 0:
                return Response(
                    {"error": "El stock no puede ser negativo."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            producto.stock = cant
        else:
            return Response(
                {"error": "Operación inválida. Use 'sumar', 'restar' o 'fijar'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        producto.save(update_fields=["stock"])
        return Response(ProductoSerializer(producto).data)


class VentaViewSet(viewsets.ModelViewSet):
    """
    API REST ViewSet para el modelo Venta.
    Controla emisión, consulta, anulación y eliminación de ventas,
    garantizando la integridad del inventario.
    """
    queryset = Venta.objects.prefetch_related("detalles__producto").all().order_by("-fecha", "-id")
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["estado"]
    search_fields = ["cliente", "observaciones", "id"]
    ordering_fields = ["fecha", "id"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return VentaCreateSerializer
        return VentaSerializer

    @transaction.atomic
    def perform_destroy(self, instance):
        """
        Al eliminar una venta vía API REST, se restaura el stock
        de los productos afectados para mantener la consistencia de datos.
        """
        productos = {
            p.pk: p
            for p in Producto.objects.select_for_update().filter(
                pk__in=instance.detalles.values_list("producto_id", flat=True)
            )
        }
        for detalle in instance.detalles.all():
            if detalle.producto_id in productos:
                productos[detalle.producto_id].stock += detalle.cantidad

        Producto.objects.bulk_update(productos.values(), ["stock"])
        instance.delete()

    @action(detail=True, methods=["post"], url_path="anular")
    @transaction.atomic
    def anular(self, request, pk=None):
        """
        Anula una venta y devuelve las unidades al inventario si estaba pagada.
        """
        venta = self.get_object()
        if venta.estado == "anulada":
            return Response(
                {"mensaje": f"La venta #{venta.pk} ya se encuentra anulada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Restaurar stock
        productos = {
            p.pk: p
            for p in Producto.objects.select_for_update().filter(
                pk__in=venta.detalles.values_list("producto_id", flat=True)
            )
        }
        for detalle in venta.detalles.all():
            if detalle.producto_id in productos:
                productos[detalle.producto_id].stock += detalle.cantidad

        Producto.objects.bulk_update(productos.values(), ["stock"])
        venta.estado = "anulada"
        venta.save(update_fields=["estado"])

        return Response(
            {
                "mensaje": f"La venta #{venta.pk} fue anulada y el stock fue restaurado correctamente.",
                "venta": VentaSerializer(venta).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        """Métricas rápidas del módulo de ventas."""
        subtotal_expr = ExpressionWrapper(
            F("detalles__cantidad") * F("detalles__precio_unitario"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        hoy = timezone.localdate()
        inicio_mes = hoy.replace(day=1)

        total_recaudado = (
            Venta.objects.filter(estado="pagada").aggregate(total=Sum(subtotal_expr))["total"]
            or Decimal("0.00")
        )
        ventas_hoy = (
            Venta.objects.filter(fecha__date=hoy, estado="pagada").aggregate(total=Sum(subtotal_expr))["total"]
            or Decimal("0.00")
        )
        ventas_mes = (
            Venta.objects.filter(fecha__date__gte=inicio_mes, estado="pagada").aggregate(total=Sum(subtotal_expr))["total"]
            or Decimal("0.00")
        )
        total_count = Venta.objects.count()
        pagadas_count = Venta.objects.filter(estado="pagada").count()
        anuladas_count = Venta.objects.filter(estado="anulada").count()

        return Response({
            "total_recaudado": float(total_recaudado),
            "ventas_hoy": float(ventas_hoy),
            "ventas_mes": float(ventas_mes),
            "total_transacciones": total_count,
            "transacciones_pagadas": pagadas_count,
            "transacciones_anuladas": anuladas_count,
        })


class DetalleVentaViewSet(viewsets.ReadOnlyModelViewSet):
    """API REST ViewSet de sólo lectura para detalles individuales de ventas."""
    queryset = DetalleVenta.objects.select_related("venta", "producto").all()
    serializer_class = DetalleVentaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["venta", "producto"]


class DashboardStatsAPIView(APIView):
    """
    Endpoint de agregación estadística para dashboards externos y clientes web.
    Permite visualizar en tiempo real KPIs del inventario y ventas.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        hoy = timezone.localdate()
        inicio_mes = hoy.replace(day=1)

        subtotal_expr = ExpressionWrapper(
            F("detalles__cantidad") * F("detalles__precio_unitario"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )

        ventas_totales_monto = (
            Venta.objects.filter(estado="pagada").aggregate(total=Sum(subtotal_expr))["total"]
            or Decimal("0.00")
        )
        ventas_mes_monto = (
            Venta.objects.filter(fecha__date__gte=inicio_mes, estado="pagada").aggregate(
                total=Sum(subtotal_expr)
            )["total"]
            or Decimal("0.00")
        )
        ventas_hoy_monto = (
            Venta.objects.filter(fecha__date=hoy, estado="pagada").aggregate(
                total=Sum(subtotal_expr)
            )["total"]
            or Decimal("0.00")
        )

        total_ventas_count = Venta.objects.count()
        total_productos = Producto.objects.count()
        productos_activos = Producto.objects.filter(activo=True).count()
        stock_critico_count = Producto.objects.filter(stock__lte=5).count()

        valor_inventario = (
            Producto.objects.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F("precio") * F("stock"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                )
            )["total"]
            or Decimal("0.00")
        )

        # Gráfico últimos 7 días
        chart_labels = []
        chart_data = []
        for i in range(6, -1, -1):
            dia = hoy - timedelta(days=i)
            chart_labels.append(dia.strftime("%d/%m"))
            monto_dia = (
                Venta.objects.filter(fecha__date=dia, estado="pagada").aggregate(
                    total=Sum(subtotal_expr)
                )["total"]
                or 0
            )
            chart_data.append(float(monto_dia))

        return Response({
            "ventas_totales_monto": float(ventas_totales_monto),
            "ventas_mes_monto": float(ventas_mes_monto),
            "ventas_hoy_monto": float(ventas_hoy_monto),
            "total_ventas_count": total_ventas_count,
            "total_productos": total_productos,
            "productos_activos": productos_activos,
            "stock_critico_count": stock_critico_count,
            "valor_inventario": float(valor_inventario),
            "chart_labels": chart_labels,
            "chart_data": chart_data,
        })


class UserProfileAPIView(APIView):
    """
    Endpoint para que el cliente obtenga los datos del usuario autenticado vía JWT.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


# Configuración del Router de Django REST Framework
router = DefaultRouter()
router.register(r"productos", ProductoViewSet, basename="producto")
router.register(r"ventas", VentaViewSet, basename="venta")
router.register(r"detalles-venta", DetalleVentaViewSet, basename="detalleventa")