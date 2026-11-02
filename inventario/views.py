import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, ProtectedError, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.forms.utils import ErrorList
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import DetalleVentaFormSet, ProductoForm, VentaForm
from .models import DetalleVenta, Producto, Venta


def _formato_clp(monto):
    try:
        val = int(round(float(monto or 0)))
        return f"${val:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "$0"


def dashboard(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    subtotal_expr = ExpressionWrapper(
        F("detalles__cantidad") * F("detalles__precio_unitario"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )

    # Métricas principales
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
    ventas_hoy_count = Venta.objects.filter(fecha__date=hoy).count()
    ventas_mes_count = Venta.objects.filter(fecha__date__gte=inicio_mes).count()

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
    valor_inventario_formateado = _formato_clp(valor_inventario)

    ultimas_ventas = Venta.objects.prefetch_related("detalles__producto").order_by("-fecha", "-id")[:6]
    productos_bajo_stock = Producto.objects.filter(activo=True, stock__lte=10).order_by("stock")[:6]

    # Datos para gráfico interactivo de los últimos 7 días
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

    context = {
        "ventas_totales_monto": ventas_totales_monto,
        "ventas_mes_monto": ventas_mes_monto,
        "ventas_hoy_monto": ventas_hoy_monto,
        "total_ventas_count": total_ventas_count,
        "ventas_hoy_count": ventas_hoy_count,
        "ventas_mes_count": ventas_mes_count,
        "total_productos": total_productos,
        "productos_activos": productos_activos,
        "stock_critico_count": stock_critico_count,
        "valor_inventario": valor_inventario,
        "valor_inventario_formateado": valor_inventario_formateado,
        "ultimas_ventas": ultimas_ventas,
        "productos_bajo_stock": productos_bajo_stock,
        "chart_labels_json": json.dumps(chart_labels),
        "chart_data_json": json.dumps(chart_data),
    }
    return render(request, "inventario/dashboard.html", context)


def lista_productos(request):
    consulta = request.GET.get("q", "").strip()
    filtro = request.GET.get("filtro", "todos")

    productos_qs = Producto.objects.all()

    if consulta:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=consulta) | Q(descripcion__icontains=consulta)
        )

    if filtro == "activos":
        productos_qs = productos_qs.filter(activo=True)
    elif filtro == "inactivos":
        productos_qs = productos_qs.filter(activo=False)
    elif filtro == "bajo_stock":
        productos_qs = productos_qs.filter(stock__lte=5)

    productos_qs = productos_qs.order_by("nombre")

    # Métricas del catálogo
    total_productos = Producto.objects.count()
    total_stock = Producto.objects.aggregate(total=Sum("stock"))["total"] or 0
    productos_criticos = Producto.objects.filter(stock__lte=5).count()
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

    valor_inventario_formateado = _formato_clp(valor_inventario)

    page_obj = Paginator(productos_qs, 10).get_page(request.GET.get("page"))

    context = {
        "productos": page_obj,
        "consulta": consulta,
        "filtro": filtro,
        "total_productos": total_productos,
        "total_stock": total_stock,
        "productos_criticos": productos_criticos,
        "valor_inventario": valor_inventario,
        "valor_inventario_formateado": valor_inventario_formateado,
    }
    return render(request, "inventario/lista_productos.html", context)


def crear_producto(request):
    form = ProductoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        producto = form.save()
        messages.success(request, f'El producto "{producto.nombre}" fue agregado con éxito.')
        return redirect("inventario:lista_productos")

    return render(
        request,
        "inventario/formulario_producto.html",
        {"form": form, "titulo": "Nuevo Producto", "boton": "Guardar Producto"},
    )


def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'El producto "{producto.nombre}" fue actualizado correctamente.')
        return redirect("inventario:lista_productos")

    return render(
        request,
        "inventario/formulario_producto.html",
        {
            "form": form,
            "producto": producto,
            "titulo": f"Editar: {producto.nombre}",
            "boton": "Actualizar Cambios",
        },
    )


def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        nombre = producto.nombre
        try:
            producto.delete()
            messages.success(request, f'El producto "{nombre}" fue eliminado del catálogo.')
        except ProtectedError:
            messages.error(
                request,
                f'No se puede eliminar "{nombre}" porque tiene ventas asociadas en el historial.',
            )
        return redirect("inventario:lista_productos")

    return render(request, "inventario/confirmar_eliminacion.html", {"producto": producto})


def _guardar_detalles(venta, formset, venta_anterior=None):
    producto_ids = {
        form.cleaned_data["producto"].pk
        for form in formset.forms
        if form.cleaned_data and not form.cleaned_data.get("DELETE")
    }
    if venta_anterior:
        producto_ids.update(venta_anterior.detalles.values_list("producto_id", flat=True))
    productos = {
        producto.pk: producto
        for producto in Producto.objects.select_for_update().filter(pk__in=producto_ids)
    }

    if venta_anterior:
        for detalle in venta_anterior.detalles.all():
            productos[detalle.producto_id].stock += detalle.cantidad
        Producto.objects.bulk_update(productos.values(), ["stock"])

    detalles = []
    for form in formset.forms:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        producto = productos[form.cleaned_data["producto"].pk]
        cantidad = form.cleaned_data["cantidad"]
        if not producto.activo:
            raise ValueError(f'El producto "{producto.nombre}" se encuentra inactivo para la venta.')
        if producto.stock < cantidad:
            raise ValueError(
                f'Stock insuficiente para "{producto.nombre}". Stock disponible: {producto.stock} uds.'
            )
        producto.stock -= cantidad
        detalles.append(
            DetalleVenta(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=producto.precio,
            )
        )

    Producto.objects.bulk_update(productos.values(), ["stock"])
    if venta_anterior:
        venta_anterior.detalles.all().delete()
    DetalleVenta.objects.bulk_create(detalles)


def lista_ventas(request):
    consulta = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()

    ventas_qs = Venta.objects.prefetch_related("detalles__producto").all()

    if consulta:
        ventas_qs = ventas_qs.filter(
            Q(cliente__icontains=consulta) | Q(id__icontains=consulta)
        )

    if estado in ("pagada", "pendiente", "anulada"):
        ventas_qs = ventas_qs.filter(estado=estado)

    # Conteo por estados
    count_todas = Venta.objects.count()
    count_pagadas = Venta.objects.filter(estado="pagada").count()
    count_pendientes = Venta.objects.filter(estado="pendiente").count()
    count_anuladas = Venta.objects.filter(estado="anulada").count()

    total_monto_filtrado = sum((v.total for v in ventas_qs), Decimal("0.00"))

    page_obj = Paginator(ventas_qs, 10).get_page(request.GET.get("page"))

    context = {
        "ventas": page_obj,
        "consulta": consulta,
        "estado": estado,
        "count_todas": count_todas,
        "count_pagadas": count_pagadas,
        "count_pendientes": count_pendientes,
        "count_anuladas": count_anuladas,
        "total_monto_filtrado": total_monto_filtrado,
    }
    return render(request, "inventario/lista_ventas.html", context)


def _obtener_productos_para_pos():
    productos = Producto.objects.all().order_by("nombre")
    data = {}
    for p in productos:
        data[str(p.id)] = {
            "id": p.id,
            "nombre": p.nombre,
            "precio": float(p.precio),
            "precio_formateado": p.precio_formateado,
            "stock": p.stock,
            "activo": p.activo,
        }
    return json.dumps(data)


def crear_venta(request):
    venta = Venta()
    form = VentaForm(request.POST or None, instance=venta)
    formset = DetalleVentaFormSet(request.POST or None, instance=venta)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                venta = form.save()
                _guardar_detalles(venta, formset)
        except ValueError as error:
            formset._non_form_errors = ErrorList([str(error)])
        else:
            messages.success(request, f"Venta #{venta.pk} emitida correctamente.")
            return redirect("inventario:detalle_venta", pk=venta.pk)

    context = {
        "form": form,
        "formset": formset,
        "titulo": "Registrar Nueva Venta",
        "productos_json": _obtener_productos_para_pos(),
    }
    return render(request, "inventario/formulario_venta.html", context)


def editar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    form = VentaForm(request.POST or None, instance=venta)
    formset = DetalleVentaFormSet(request.POST or None, instance=venta)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                venta = form.save()
                _guardar_detalles(venta, formset, venta_anterior=venta)
        except ValueError as error:
            formset._non_form_errors = ErrorList([str(error)])
        else:
            messages.success(request, f"La venta #{venta.pk} fue actualizada con éxito.")
            return redirect("inventario:detalle_venta", pk=venta.pk)

    context = {
        "form": form,
        "formset": formset,
        "titulo": f"Editar Venta #{venta.pk}",
        "venta": venta,
        "productos_json": _obtener_productos_para_pos(),
    }
    return render(request, "inventario/formulario_venta.html", context)


def detalle_venta(request, pk):
    venta = get_object_or_404(
        Venta.objects.prefetch_related("detalles__producto"), pk=pk
    )
    # Desglose referencial neto e IVA (19%)
    total = venta.total
    neto = (total / Decimal("1.19")).quantize(Decimal("0.01")) if total else Decimal("0.00")
    iva = total - neto

    context = {
        "venta": venta,
        "neto": neto,
        "iva": iva,
    }
    return render(request, "inventario/detalle_venta.html", context)


@transaction.atomic
def eliminar_venta(request, pk):
    venta = get_object_or_404(Venta.objects.prefetch_related("detalles"), pk=pk)
    if request.method == "POST":
        productos = {
            p.pk: p
            for p in Producto.objects.select_for_update().filter(
                pk__in=venta.detalles.values_list("producto_id", flat=True)
            )
        }
        for detalle in venta.detalles.all():
            productos[detalle.producto_id].stock += detalle.cantidad
        Producto.objects.bulk_update(productos.values(), ["stock"])
        venta.delete()
        messages.success(
            request,
            f"La venta #{pk} fue anulada/eliminada y las unidades fueron restauradas al inventario.",
        )
        return redirect("inventario:lista_ventas")

    return render(request, "inventario/confirmar_eliminacion.html", {"venta": venta})


def reporte_ventas(request):
    hoy = timezone.localdate()
    periodo = request.GET.get("periodo", "")

    if periodo == "hoy":
        desde = hasta = hoy.isoformat()
    elif periodo == "7dias":
        desde = (hoy - timedelta(days=7)).isoformat()
        hasta = hoy.isoformat()
    elif periodo == "mes":
        desde = hoy.replace(day=1).isoformat()
        hasta = hoy.isoformat()
    elif periodo == "mes_pasado":
        primer_dia_mes_actual = hoy.replace(day=1)
        ultimo_dia_mes_pasado = primer_dia_mes_actual - timedelta(days=1)
        desde = ultimo_dia_mes_pasado.replace(day=1).isoformat()
        hasta = ultimo_dia_mes_pasado.isoformat()
    elif periodo == "anio":
        desde = hoy.replace(month=1, day=1).isoformat()
        hasta = hoy.isoformat()
    else:
        desde = request.GET.get("desde", hoy.replace(day=1).isoformat())
        hasta = request.GET.get("hasta", hoy.isoformat())

    try:
        fecha_desde = datetime.fromisoformat(desde).date()
        fecha_hasta = datetime.fromisoformat(hasta).date()
    except ValueError:
        fecha_desde, fecha_hasta = hoy.replace(day=1), hoy
        desde, hasta = fecha_desde.isoformat(), fecha_hasta.isoformat()

    estado_filtro = request.GET.get("estado", "")
    ventas = Venta.objects.filter(fecha__date__range=(fecha_desde, fecha_hasta)).prefetch_related(
        "detalles__producto"
    )

    if estado_filtro in ("pagada", "pendiente", "anulada"):
        ventas = ventas.filter(estado=estado_filtro)

    ventas = ventas.order_by("-fecha", "-id")

    # Métricas y acumuladores
    total = sum((venta.total for venta in ventas), Decimal("0.00"))
    total_transacciones = ventas.count()
    ticket_promedio = (
        (total / Decimal(total_transacciones)).quantize(Decimal("0.01"))
        if total_transacciones > 0
        else Decimal("0.00")
    )
    total_articulos = sum(
        (sum((d.cantidad for d in v.detalles.all()), 0) for v in ventas), 0
    )

    # Conteo por estado
    ventas_pagadas = sum(1 for v in ventas if v.estado == "pagada")
    ventas_pendientes = sum(1 for v in ventas if v.estado == "pendiente")
    ventas_anuladas = sum(1 for v in ventas if v.estado == "anulada")

    if request.GET.get("formato") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="reporte-ventas-{desde}-al-{hasta}.csv"'
        )
        response.write("\ufeffFolio,Fecha,Cliente,Estado,Artículos,Total\n")
        for venta in ventas:
            arts = sum((d.cantidad for d in venta.detalles.all()), 0)
            response.write(
                f"{venta.folio},{venta.fecha:%Y-%m-%d %H:%M},{venta.cliente or 'Consumidor Final'},{venta.get_estado_display()},{arts},{venta.total}\n"
            )
        return response

    context = {
        "ventas": ventas,
        "total": total,
        "total_transacciones": total_transacciones,
        "ticket_promedio": ticket_promedio,
        "total_articulos": total_articulos,
        "ventas_pagadas": ventas_pagadas,
        "ventas_pendientes": ventas_pendientes,
        "ventas_anuladas": ventas_anuladas,
        "desde": desde,
        "hasta": hasta,
        "periodo": periodo,
        "estado_filtro": estado_filtro,
    }
    return render(request, "inventario/reporte_ventas.html", context)


def cliente_app(request):
    """
    Vista que sirve el Cliente Web SPA consumidor de la API REST (ES03).
    Permite autenticarse mediante JWT, realizar operaciones CRUD completas,
    visualizar modelos 3D con Three.js y persistir datos offline.
    """
    return render(request, "inventario/cliente_app.html")