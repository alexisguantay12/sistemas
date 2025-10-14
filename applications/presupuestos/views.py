# presupuestos/views.py
# ============================================================
# 📦 Importaciones
# ============================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from decimal import Decimal, InvalidOperation
import json
import os
import locale
import io

from openpyxl import load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from django.contrib.auth.decorators import login_required

from .models import (
    Presupuesto, PresupuestoItem, Prestacion, PresupuestoHistorial, Pago
)
from .forms import NomencladorUploadForm
from django.db.models import Q

# ============================================================
# 🧾 Listado de Presupuestos
# ============================================================
@login_required
def lista_presupuestos(request):
    presupuestos = Presupuesto.objects.all().order_by('-fecha_creacion')
    return render(request, 'presupuestos/presupuestos.html', {'presupuestos': presupuestos})


# ============================================================
# 💰 Registro de Pagos
# ============================================================

from django.template.loader import render_to_string
from django.utils import timezone
from django.http import JsonResponse

def registrar_pago(request, pk):
    presupuesto = get_object_or_404(Presupuesto, id=pk)

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        monto = request.POST.get('monto')
        medio = request.POST.get('medio_pago')
        caja = request.POST.get('caja')

        if not monto:
            return JsonResponse({'success': False, 'error': 'Monto inválido'})

        Pago.objects.create(
            presupuesto=presupuesto,
            monto=monto,
            medio_pago=medio,
            caja=caja,
            user_made=request.user
        )

        pagos = presupuesto.pagos.all().order_by('-fecha')
        for p in pagos:
            p.puede_eliminar = (timezone.now() - p.fecha).total_seconds() < 900

        pagos_html = render_to_string('presupuestos/partials/_tabla_pagos.html', {'pagos': pagos})
        total_pagado = sum(pago.monto for pago in presupuesto.pagos.all())
        saldo = presupuesto.total - (total_pagado or 0)  # previene None
        return JsonResponse({'success': True, 'pagos_html': pagos_html,'total_pagado':total_pagado,'saldo':saldo})

    return JsonResponse({'success': False, 'error': 'Petición no válida'})
# ============================================================
# 📜 Detalle de Presupuesto + Historial + Pagos
# ============================================================

from django.views.decorators.http import require_POST

@require_POST
def eliminar_pago(request, pk):
    pago = get_object_or_404(Pago, id=pk)
 
    presupuesto = pago.presupuesto
    pago.delete()

    pagos = presupuesto.pagos.all().order_by('-fecha')
    for p in pagos:
        p.puede_eliminar = (timezone.now() - p.fecha).total_seconds() < 900
    total_pagado = sum(pago.monto for pago in presupuesto.pagos.all())
    saldo = presupuesto.total - (total_pagado or 0)  # previene None
    pagos_html = render_to_string('presupuestos/partials/_tabla_pagos.html', {'pagos': pagos})
    return JsonResponse({'success': True, 'pagos_html': pagos_html,'total_pagado':total_pagado,'saldo':saldo})



@login_required
def detalle_presupuesto(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    historial = presupuesto.historiales.all().order_by('fecha')
    pagos = presupuesto.pagos.all().order_by('-fecha')
    total_pagado = sum(pago.monto for pago in presupuesto.pagos.all())
    saldo = presupuesto.total - (total_pagado or 0)  # previene None
    for p in pagos:
        p.puede_eliminar = (timezone.now() - p.fecha).total_seconds() < 900
    historial_json = []
    for h in historial:
        datos = h.datos  # dict con todos los datos guardados
        historial_json.append({
            'id': h.id,
            'fecha': h.fecha.strftime('%d/%m/%Y %H:%M'),
            'user': f"{h.user_made.first_name} {h.user_made.last_name}" if h.user_made else "Desconocido",
            'paciente': {
                'nombre': datos['paciente'].get('nombre', ''),
                'dni': datos['paciente'].get('dni', ''),
                'edad': datos['paciente'].get('edad', ''),
                'telefono': datos['paciente'].get('telefono', ''),
                'email': datos['paciente'].get('email', ''),
                'obra_social': datos['paciente'].get('obra_social', ''),
            },
            'medico': datos.get('medico', ''),
            'diagnostico': datos.get('diagnostico', ''),
            'estado': datos.get('estado', ''),
            'motivo_no_concretado': datos.get('motivo_no_concretado', ''),
            'items': [
                {
                    'codigo': it.get('codigo', ''),
                    'tipo': it.get('tipo', ''),
                    'prestacion': it.get('prestacion', ''),
                    'cantidad': float(it.get('cantidad', 0)),
                    'precio': float(it.get('precio', 0)),
                    'importe': float(it.get('importe', 0)),
                    'iva': float(it.get('iva', 0)),
                    'subtotal': float(it.get('subtotal', 0)),
                } for it in datos.get('items', [])
            ],
            'total': float(datos.get('total', 0)),
        })

    context = {
        'presupuesto': presupuesto,
        'historial_json': json.dumps(historial_json),
        'pagos': pagos,
        'total_pagado':total_pagado,
        'saldo':saldo
    }
    return render(request, 'presupuestos/detalle_presupuesto.html', context)


# ============================================================
# 🕒 Guardar Historial (helper)
# ============================================================

def guardar_historial(presupuesto, usuario=None):
    """Guarda una copia completa del estado actual del presupuesto."""
    items = [{
        "codigo": item.codigo,
        "tipo": item.get_tipo_display(),
        "prestacion": item.prestacion,
        "cantidad": float(item.cantidad),
        "precio": float(item.precio),
        "importe": float(item.importe),
        "iva": float(item.iva),
        "subtotal": float(item.subtotal),
    } for item in presupuesto.items.all()]

    datos = {
        "paciente": {
            "nombre": presupuesto.paciente_nombre,
            "dni": presupuesto.paciente_dni,
            "edad": presupuesto.paciente_edad,
            "direccion": presupuesto.paciente_direccion,
            "telefono": presupuesto.paciente_telefono,
            "email": presupuesto.paciente_email,
            "obra_social": presupuesto.obra_social,
        },
        "medico": presupuesto.medico,
        "diagnostico": presupuesto.diagnostico,
        "estado": presupuesto.estado,
        "motivo_no_concretado": presupuesto.motivo_no_concretado,
        "items": items,
        "total": float(presupuesto.total),
    }

    PresupuestoHistorial.objects.create(
        presupuesto=presupuesto,
        user_made=usuario,
        datos=datos
    )


# ============================================================
# 📖 Detalle del Historial
# ============================================================

def detalle_historial(request, historial_id):
    historial = get_object_or_404(PresupuestoHistorial, id=historial_id)
    return render(request, "presupuestos/detalle_historial.html", {"historial": historial})


# ============================================================
# ✏️ Edición de Presupuesto
# ============================================================

@login_required
def editar_presupuesto(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    tiene_iva = presupuesto.items.filter(iva__gt=0).exists()

    if request.method == "POST":
        # Guardar historial antes de modificar
        guardar_historial(presupuesto, usuario=presupuesto.user_updated)

        # Actualizar campos principales
        presupuesto.paciente_nombre = request.POST.get("paciente_nombre")
        presupuesto.paciente_dni = request.POST.get("paciente_dni")
        presupuesto.paciente_edad = request.POST.get("paciente_edad") or None
        presupuesto.paciente_direccion = request.POST.get("paciente_direccion")
        presupuesto.paciente_telefono = request.POST.get("paciente_telefono")
        presupuesto.paciente_email = request.POST.get("paciente_email")
        presupuesto.obra_social = request.POST.get("obra_social")
        presupuesto.medico = request.POST.get("medico")
        presupuesto.diagnostico = request.POST.get("diagnostico")
        presupuesto.user_updated = request.user
        presupuesto.save()

        # Eliminar items anteriores
        presupuesto.items.all().delete()

        # Crear los nuevos desde el POST
        codigos = request.POST.getlist("codigo")
        tipos = request.POST.getlist("tipo")
        prestaciones = request.POST.getlist("prestacion")
        cantidades = request.POST.getlist("cantidad")
        precios = request.POST.getlist("precio")
        importes = request.POST.getlist("importe")
        ivas = request.POST.getlist("iva")
        subtotales = request.POST.getlist("subtotal")

        for i in range(len(codigos)):
            if codigos[i].strip() == "" and prestaciones[i].strip() == "":
                continue

            PresupuestoItem.objects.create(
                presupuesto=presupuesto,
                codigo=codigos[i],
                tipo=tipos[i],
                prestacion=prestaciones[i],
                cantidad=Decimal(cantidades[i]),
                precio=Decimal(precios[i]),
                importe=Decimal(importes[i]),
                iva=Decimal(ivas[i]),
                subtotal=Decimal(subtotales[i]),
            )

        messages.success(request, "Presupuesto actualizado correctamente")
        return redirect("presupuestos_app:detalle_presupuesto", pk=presupuesto.pk)

    return render(request, "presupuestos/editar_presupuesto.html", {
        "presupuesto": presupuesto,
        "tiene_iva": tiene_iva
    })


# ============================================================
# ➕ Agregar Presupuesto Nuevo
# ============================================================
@login_required
def agregar_presupuesto(request):
    if request.method == "POST":
        presupuesto = Presupuesto.objects.create(
            paciente_nombre=request.POST.get("paciente_nombre"),
            paciente_dni=request.POST.get("paciente_dni"),
            paciente_edad=request.POST.get("paciente_edad") or None,
            paciente_direccion=request.POST.get("paciente_direccion"),
            paciente_telefono=request.POST.get("paciente_telefono"),
            paciente_email=request.POST.get("paciente_email"),
            obra_social=request.POST.get("obra_social"),
            medico=request.POST.get("medico"),
            diagnostico=request.POST.get("diagnostico"),
            user_made=request.user,
            user_updated=request.user
        )

        # Carga de items
        codigos = request.POST.getlist("codigo")
        tipos = request.POST.getlist("tipo")
        prestaciones = request.POST.getlist("prestacion")
        cantidades = request.POST.getlist("cantidad")
        precios = request.POST.getlist("precio")
        importes = request.POST.getlist("importe")
        ivas = request.POST.getlist("iva")
        subtotales = request.POST.getlist("subtotal")

        with transaction.atomic():
            for i in range(len(prestaciones)):
                if not prestaciones[i].strip():
                    continue
                PresupuestoItem.objects.create(
                    presupuesto=presupuesto,
                    codigo=codigos[i] or "",
                    tipo=tipos[i] or "",
                    prestacion=prestaciones[i],
                    cantidad=int(cantidades[i]) if cantidades[i] else 1,
                    precio=float(precios[i]) if precios[i] else 0,
                    importe=float(importes[i]) if importes[i] else 0,
                    iva=float(ivas[i]) if ivas[i] else 0,
                    subtotal=float(subtotales[i]) if subtotales[i] else 0,
                )
        return redirect("presupuestos_app:presupuestos")

    prestaciones = Prestacion.objects.all()
    return render(request, "presupuestos/agregar_presupuesto.html", {"prestaciones": prestaciones})


# ============================================================
# 🔎 Buscar prestación por código
# ============================================================

def get_prestacion(request, codigo):
    """Devuelve los datos de una prestación según código."""
    prestacion = get_object_or_404(Prestacion, codigo=codigo)

    # Casos especiales
    if codigo == '430101':
        p_desc = get_object_or_404(Prestacion, codigo='431001')
        precio_u = (prestacion.gastos + prestacion.especialista) + (p_desc.gastos + p_desc.especialista)
    elif codigo == '400101':
        p_desc = get_object_or_404(Prestacion, codigo='431002')
        precio_u = (prestacion.gastos + prestacion.especialista) + (p_desc.gastos + p_desc.especialista)
    elif codigo == '340907':
        precio_u = (prestacion.gastos + prestacion.especialista) * 3
    else:
        precio_u = prestacion.gastos

    data = {
        "prestacion": prestacion.codigo,
        "nombre": prestacion.nombre,
        "precio": float(precio_u),
    }
    return JsonResponse(data)


# ============================================================
# 💡 Obtener precio según tipo (gastos, especialista, total)
# ============================================================

def get_tipo(request, codigo):
    tipo = request.GET.get("tipo")
    try:
        prestacion = Prestacion.objects.get(codigo=codigo)
        if tipo == "gastos":
            precio = prestacion.gastos
        elif tipo == "especialista":
            precio = prestacion.especialista
        else:
            precio = prestacion.total()

        # Casos especiales
        if codigo == '430101':
            p_desc = get_object_or_404(Prestacion, codigo='431001')
            precio = (prestacion.gastos + prestacion.especialista) + (p_desc.gastos + p_desc.especialista)
        elif codigo == '400101':
            p_desc = get_object_or_404(Prestacion, codigo='431002')
            precio = (prestacion.gastos + prestacion.especialista) + (p_desc.gastos + p_desc.especialista)
        elif codigo == '340907':
            precio = (prestacion.gastos + prestacion.especialista) * 3
        else:
            precio = prestacion.gastos

    except Prestacion.DoesNotExist:
        return JsonResponse({"error": "Código no encontrado"}, status=404)

    return JsonResponse({"precio": precio})


# ============================================================
# 📤 Carga del Nomenclador desde Excel
# ============================================================

def parse_price(value):
    """Convierte distintos formatos numéricos en Decimal con 2 decimales."""
    if value is None:
        return Decimal("0.00")

    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return Decimal("0.00")

    s = str(value).strip()
    if s in ("", "-"):
        return Decimal("0.00")

    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    s = s.replace(' ', '').replace('$', '').replace('ARS', '')

    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")

@login_required
def cargar_nomenclador(request):
    """Carga o actualiza prestaciones desde un archivo Excel."""
    resumen = {'creadas': 0, 'actualizadas': 0, 'errores': []}

    if request.method == "POST":
        form = NomencladorUploadForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.cleaned_data['archivo']

            def procesar_fila(row_index, cells):
                try:
                    if all((c is None or (isinstance(c, str) and c.strip() == "")) for c in cells):
                        return
                    codigo = str(cells[0]).strip() if len(cells) >= 1 and cells[0] else None
                    nombre = str(cells[1]).strip() if len(cells) >= 2 and cells[1] else None
                    especialista = parse_price(cells[2]) if len(cells) >= 3 else None
                    gastos = parse_price(cells[5]) if len(cells) >= 6 else None
                    if not codigo or not nombre:
                        raise ValueError(f"Fila {row_index}: falta código o nombre")
                    if especialista is None or gastos is None:
                        raise ValueError(f"Fila {row_index}: faltan valores de especialista o gastos")

                    prest = Prestacion.objects.filter(codigo__iexact=codigo).first()
                    if not prest and not codigo:
                        prest = Prestacion.objects.filter(nombre__iexact=nombre).first()

                    if prest:
                        prest.nombre = nombre
                        prest.codigo = codigo
                        prest.especialista = especialista
                        prest.gastos = gastos
                        prest.save()
                        resumen['actualizadas'] += 1
                    else:
                        Prestacion.objects.create(
                            nombre=nombre,
                            codigo=codigo,
                            especialista=especialista,
                            gastos=gastos
                        )
                        resumen['creadas'] += 1

                except Exception as ex:
                    resumen['errores'].append(f"Fila {row_index}: {str(ex)}")

            try:
                with transaction.atomic():
                    wb = load_workbook(filename=archivo, read_only=True, data_only=True)
                    ws = wb.active
                    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
                        if i < 4:
                            continue
                        procesar_fila(i, list(row))
            except Exception as ex:
                resumen['errores'].append(f"Error general: {str(ex)}")

            messages.success(
                request,
                f"Nomenclador procesado. Creadas: {resumen['creadas']}, Actualizadas: {resumen['actualizadas']}."
            )
            return render(request, 'presupuestos/cargar_nomenclador.html', {
                'form': NomencladorUploadForm(),
                'resumen': resumen
            })

    else:
        form = NomencladorUploadForm()

    return render(request, 'presupuestos/cargar_nomenclador.html', {
        'form': form,
        'resumen': resumen
    })


# ============================================================
# 🔍 Buscar Nomenclador (para autocompletar)
# ============================================================
@login_required
def buscar_nomenclador(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse([], safe=False)
    resultados = (
        Prestacion.objects.filter(
            Q(nombre__icontains=q) | Q(codigo__icontains=q))[:20]
        .values('codigo', 'nombre','gastos','especialista')
    )
    return JsonResponse(list(resultados), safe=False)


 
def format_num(n):
    """Formatea número con punto de miles y coma decimal: 12345.67 → 12.345,67"""
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
@login_required
def imprimir_presupuesto(request, pk):
    presupuesto = Presupuesto.objects.get(pk=pk)
    items = presupuesto.items.all()

    # --- Locale argentino para números --- 

    # --- Crear PDF ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="presupuesto_{pk}.pdf"'
    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # --- Márgenes ---
    margen_izq = 20*mm
    margen_der = 20*mm
    margen_sup = height - 20*mm
    y_actual = margen_sup

    styles = getSampleStyleSheet()
    
    # --- Encabezado ---
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margen_izq, y_actual, "Hospital Privado Santa Clara de Asís S.A.")
    c.setFont("Helvetica", 9)
    y_actual -= 6*mm
    c.drawString(margen_izq, y_actual, "Urquiza 964 - 4400 Salta")
    y_actual -= 10*mm  # Separación antes de datos generales


            # Dibuja el logo a la derecha, alineado con el título
    import os
    from django.conf import settings
    logo_path = os.path.join(settings.BASE_DIR, "static", "fotos", "hpsca_logo.jpg")

    logo_width = 25 * mm   # ancho del logo
    logo_height = 25 * mm  # alto del logo
    try:
        logo = ImageReader(logo_path)
        c.drawImage(
            logo,
            width - logo_width - margen_der,  # 👈 margen derecho real
            A4[1] - logo_height - 10 * mm,  # posición Y: ajustá este valor fino
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask='auto'
        )
    except Exception as e:
        print("No se pudo cargar el logo:", e)

    c.setFont("Helvetica-Bold", 11) 
    texto = "PRESUPUESTO"
    ancho_pagina = A4[0]

    # Calcular ancho del texto para centrarlo
    ancho_texto = c.stringWidth(texto, "Helvetica-Bold", 11)
    x_centrado = (ancho_pagina - ancho_texto) / 2

    
    # Dibujar texto centrado
    c.drawString(x_centrado, y_actual, texto)

    # Dibujar línea subrayada debajo del texto
    y_linea = y_actual - 2  # 2 puntos por debajo del texto
    c.setLineWidth(0.6)
    c.line(x_centrado, y_linea, x_centrado + ancho_texto, y_linea)

    # Actualizar posición para lo siguiente
    y_actual -= 10 * mm


    # --- Datos generales ---
    c.setFont("Helvetica", 10)
    c.drawString(margen_izq, y_actual, f"Fecha: {presupuesto.fecha_creacion.strftime('%d/%m/%Y')}")
    c.drawString(width/2, y_actual, f"Obra Social: {presupuesto.obra_social}")
    y_actual -= 6*mm
    c.drawString(margen_izq, y_actual, f"Paciente: {presupuesto.paciente_nombre}")
    c.drawString(width/2, y_actual, f"Edad: {presupuesto.paciente_edad or ''}   DNI: {presupuesto.paciente_dni or ''}")
    y_actual -= 6*mm
    c.drawString(margen_izq, y_actual, f"Dirección: {presupuesto.paciente_direccion or ''}")
    c.drawString(width/2, y_actual, f"Teléfono: {presupuesto.paciente_telefono or ''}")
    y_actual -= 6*mm
    c.drawString(margen_izq, y_actual, f"Médico: {presupuesto.medico or ''}")
    c.drawString(width/2, y_actual, f"Diagnóstico: {presupuesto.diagnostico or ''}")
    
    y_actual -= 10 * mm

    # --- Tabla de items ---
    data = [["Código", "Prestación", "Cant.", "P. Unitario", "Importe", "IVA", "Subtotal"]]
    for item in items:
        data.append([
            item.codigo or "",
            item.prestacion or "",
            item.cantidad,
            format_num(item.precio),
            format_num(item.importe),
            format_num(item.iva),
            format_num(item.subtotal),
        ])

    colWidths = [15*mm, 77*mm, 10*mm, 17*mm, 17*mm, 17*mm, 17*mm]
    table = Table(data, colWidths=colWidths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold',8),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 7),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # ✅ Calcular la altura exacta de la tabla
    table_width, table_height = table.wrap(width - margen_izq - margen_der, y_actual)

    # Dibujar la tabla justo debajo del texto anterior
    table.drawOn(c, margen_izq, y_actual - table_height)

    # Actualizar y_actual después de dibujar la tabla
    y_actual -= table_height + 10*mm
        # --- Totales ---
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - margen_der, y_actual, f"Subtotal: $ {format_num(presupuesto.total)}")
    y_actual -= 6*mm
    c.drawRightString(width - margen_der, y_actual, f"IVA (21%): ${format_num(presupuesto.iva)}")
    y_actual -= 6*mm
    c.drawRightString(width - margen_der, y_actual, f"Total Presupuesto: ${format_num(presupuesto.total)} ")
    y_actual -= 10*mm

    # --- Observaciones ---
    texto_obs = """\
El presente presupuesto tiene una validez de 7 días.
NO INCLUYE Honorarios Médicos.
NO INCLUYE Honorarios Anestesistas (Dirigirse a Sra. Viviana Baigorria 152-259689)
NO INCLUYE Honorarios por Transfusiones de Sangre. En caso de necesitar, dirigirse a BANCO DE SANGRE.
El monto presupuestado es ESTIMATIVO, el valor final dependerá de la medicación indicada y de los días de internación adicionales.
EXCLUYE prácticas no detalladas."""
    text_obj = c.beginText(margen_izq, y_actual)
    text_obj.setFont("Helvetica", 8)
    for line in texto_obs.split("\n"):
        text_obj.textLine(line)
        y_actual -= 4*mm  # Ajuste vertical por línea
    c.drawText(text_obj)
    y_actual -= 10*mm

    # --- Formas de pago ---
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margen_izq, y_actual, "FORMAS DE PAGO:")
    y_actual -= 6*mm
    c.setFont("Helvetica", 9)
    c.drawString(margen_izq, y_actual, "Efectivo, tarjeta de crédito, débito o cheque a la orden de Hospital Privado Santa Clara de Asís S.A.")
    y_actual -= 25*mm

    # --- Firma ---
    c.drawString(margen_izq, y_actual, f"Confecciono: {presupuesto.user_updated.first_name},{presupuesto.user_updated.last_name}")
    c.drawString(width-margen_der-50*mm, y_actual, "_________________________")
    c.drawString(width-margen_der-40*mm, y_actual-6*mm, "Firma Autorizado")

    c.showPage()
    c.save()
    return response