from django.urls import path
from . import views

from .models import Producto
from rest_framework import routers, serializers, viewsets

class ProductoSeralizers(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSeralizers

router = routers.DefaultRouter()
router.register(r'productos', ProductoViewSet)

app_name = "inventario"

urlpatterns = [
    # Dashboard principal de control de ventas
    path("", views.dashboard, name="dashboard"),

    # Catálogo de Productos e Inventario
    path("productos/", views.lista_productos, name="lista_productos"),
    path("productos/nuevo/", views.crear_producto, name="crear_producto"),
    path("productos/<int:pk>/editar/", views.editar_producto, name="editar_producto"),
    path("productos/<int:pk>/eliminar/", views.eliminar_producto, name="eliminar_producto"),

    # Compatibilidad de rutas anteriores de productos
    path("nuevo/", views.crear_producto, name="crear_producto_alias"),
    path("<int:pk>/editar/", views.editar_producto, name="editar_producto_alias"),
    path("<int:pk>/eliminar/", views.eliminar_producto, name="eliminar_producto_alias"),

    # Control de Ventas
    path("ventas/", views.lista_ventas, name="lista_ventas"),
    path("ventas/nueva/", views.crear_venta, name="crear_venta"),
    path("ventas/reporte/", views.reporte_ventas, name="reporte_ventas"),
    path("ventas/<int:pk>/", views.detalle_venta, name="detalle_venta"),
    path("ventas/<int:pk>/editar/", views.editar_venta, name="editar_venta"),
    path("ventas/<int:pk>/eliminar/", views.eliminar_venta, name="eliminar_venta"),
]