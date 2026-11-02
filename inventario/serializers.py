from decimal import Decimal
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from .models import DetalleVenta, Producto, Venta


class UserSerializer(serializers.ModelSerializer):
    """Serializer para datos del usuario autenticado."""
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "is_staff", "is_superuser")
        read_only_fields = fields


class ProductoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Producto con validaciones de negocio
    y campos calculados para la API REST.
    """
    precio_formateado = serializers.ReadOnlyField()
    estado_stock = serializers.ReadOnlyField()

    class Meta:
        model = Producto
        fields = (
            "id",
            "nombre",
            "descripcion",
            "precio",
            "stock",
            "activo",
            "precio_formateado",
            "estado_stock",
        )

    def validate_nombre(self, value):
        val = value.strip()
        if not val:
            raise serializers.ValidationError("El nombre del producto no puede estar vacío.")
        return val

    def validate_precio(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("El precio del producto debe ser mayor a 0.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("El stock no puede ser un valor negativo.")
        return value


class DetalleVentaSerializer(serializers.ModelSerializer):
    """Serializer para visualizar un detalle de venta con información del producto."""
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetalleVenta
        fields = (
            "id",
            "venta",
            "producto",
            "producto_nombre",
            "cantidad",
            "precio_unitario",
            "subtotal",
        )
        read_only_fields = ("id", "venta", "subtotal", "producto_nombre")


class DetalleVentaItemInputSerializer(serializers.Serializer):
    """Serializer para la entrada de items de detalle al crear una venta."""
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    cantidad = serializers.IntegerField(min_value=1)
    precio_unitario = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01"), required=False
    )


class VentaSerializer(serializers.ModelSerializer):
    """
    Serializer para lectura completa de ventas con detalles anidados y totales.
    """
    folio = serializers.ReadOnlyField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_formateado = serializers.ReadOnlyField()
    detalles = DetalleVentaSerializer(many=True, read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Venta
        fields = (
            "id",
            "folio",
            "cliente",
            "fecha",
            "estado",
            "estado_display",
            "observaciones",
            "total",
            "total_formateado",
            "detalles",
        )
        read_only_fields = ("id", "folio", "fecha", "total", "total_formateado", "detalles")


class VentaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para creación atómica de ventas.
    Gestiona la verificación y descuento automático de stock de los productos.
    """
    detalles = DetalleVentaItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = Venta
        fields = (
            "id",
            "cliente",
            "estado",
            "observaciones",
            "detalles",
        )

    def validate_detalles(self, items):
        if not items:
            raise serializers.ValidationError("Debe incluir al menos un producto en la venta.")

        producto_ids = [item["producto"].pk for item in items]
        if len(producto_ids) != len(set(producto_ids)):
            raise serializers.ValidationError("No se pueden repetir productos en las líneas de detalle. Agrupe la cantidad.")

        for item in items:
            prod = item["producto"]
            cant = item["cantidad"]
            if not prod.activo:
                raise serializers.ValidationError(
                    f'El producto "{prod.nombre}" no está activo para la venta.'
                )
            if prod.stock < cant:
                raise serializers.ValidationError(
                    f'Stock insuficiente para "{prod.nombre}". Stock actual: {prod.stock}, solicitado: {cant}.'
                )

        return items

    @transaction.atomic
    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles")
        venta = Venta.objects.create(**validated_data)

        # Bloquear productos para actualización concurrente segura
        producto_ids = [d["producto"].pk for d in detalles_data]
        productos_map = {
            p.pk: p
            for p in Producto.objects.select_for_update().filter(pk__in=producto_ids)
        }

        detalles_objs = []
        for d in detalles_data:
            producto = productos_map[d["producto"].pk]
            cantidad = d["cantidad"]

            if producto.stock < cantidad:
                raise serializers.ValidationError(
                    f'Stock insuficiente para "{producto.nombre}". Stock disponible: {producto.stock}.'
                )

            # Descontar stock
            producto.stock -= cantidad

            precio_unitario = d.get("precio_unitario") or producto.precio

            detalles_objs.append(
                DetalleVenta(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                )
            )

        Producto.objects.bulk_update(productos_map.values(), ["stock"])
        DetalleVenta.objects.bulk_create(detalles_objs)

        return venta

    def to_representation(self, instance):
        return VentaSerializer(instance, context=self.context).data