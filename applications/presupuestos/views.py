from django.shortcuts import render,redirect
from .models import Presupuesto, PresupuestoItem, Prestacion, PresupuestoHistorial,Pago
from django.db import transaction 
from django.http import JsonResponse
from django.shortcuts import get_object_or_404


def lista_presupuestos(request):
    presupuestos = Presupuesto.objects.all().order_by('-fecha_creacion')
    return render(request, 'presupuestos/presupuestos.html', {'presupuestos': presupuestos})


import json
from django.shortcuts import get_object_or_404, render
from .models import Presupuesto, PresupuestoHistorial


def registrar_pago(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)

    if request.method == "POST":
        monto = request.POST.get("monto")
        medio_pago = request.POST.get("medio_pago")
        caja = request.POST.get("caja")
        if monto and medio_pago:
            Pago.objects.create(
                presupuesto=presupuesto,
                monto=monto,
                medio_pago=medio_pago,
                caja = caja,
                user_made = request.user 
            )
            messages.success(request, "Pago registrado correctamente.")
        else:
            messages.error(request, "Faltan datos para registrar el pago.")

    return redirect("presupuestos_app:detalle_presupuesto", pk=presupuesto.id)


def detalle_presupuesto(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    historial = presupuesto.historiales.all().order_by('fecha')
    pagos = presupuesto.pagos.all().order_by('-fecha')
    historial_json = []
    for h in historial:
        datos = h.datos  # esto ya es un dict
        historial_json.append({
            'id': h.id,
            'fecha': h.fecha.strftime('%d/%m/%Y %H:%M'),
            'user':f"{h.user_made.first_name} {h.user_made.last_name}" if h.user_made else "Desconocido",
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
                }
                for it in datos.get('items', [])
            ],
            'total': float(datos.get('total', 0)),
        })

    context = {
        'presupuesto': presupuesto,
        'historial_json': json.dumps(historial_json),
        'pagos':pagos
    }
    return render(request, 'presupuestos/detalle_presupuesto.html', context)

import json

def guardar_historial(presupuesto, usuario=None):
    items = []
    for item in presupuesto.items.all():
        items.append({
            "codigo": item.codigo,
            "tipo": item.get_tipo_display(),
            "prestacion": item.prestacion,
            "cantidad": float(item.cantidad),
            "precio": float(item.precio),
            "importe": float(item.importe),
            "iva": float(item.iva),
            "subtotal": float(item.subtotal),
        })

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
        user_made = usuario,
        datos=datos
    )



def detalle_historial(request, historial_id):
    historial = get_object_or_404(PresupuestoHistorial, id=historial_id)
    return render(request, "presupuestos/detalle_historial.html", {
        "historial": historial
    })



def editar_presupuesto(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    tiene_iva = presupuesto.items.filter(iva__gt=0).exists()

    if request.method == "POST":
        # 1️⃣ Guardamos historial antes de actualizar
        guardar_historial(presupuesto, usuario=presupuesto.user_updated)

        # 2️⃣ Actualizamos datos del paciente y médico
        presupuesto.paciente_nombre = request.POST.get("paciente_nombre")
        presupuesto.paciente_dni = request.POST.get("paciente_dni")
        presupuesto.paciente_edad = request.POST.get("paciente_edad") or None
        presupuesto.paciente_direccion = request.POST.get("paciente_direccion")
        presupuesto.paciente_telefono = request.POST.get("paciente_telefono")
        presupuesto.paciente_email = request.POST.get("paciente_email")
        presupuesto.obra_social = request.POST.get("obra_social")
        presupuesto.medico = request.POST.get("medico")
        presupuesto.diagnostico = request.POST.get("diagnostico")
        presupuesto.user_updated= request.user
        presupuesto.save()

        # 3️⃣ Borramos items anteriores y creamos los nuevos desde POST
        presupuesto.items.all().delete()

        # Los items llegan en arrays por nombre
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
                continue  # ignorar filas vacías

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

    # GET -> renderizamos el form con valores precargados
    return render(request, "presupuestos/editar_presupuesto.html", {
        "presupuesto": presupuesto,
        "tiene_iva":tiene_iva
    })


def agregar_presupuesto(request):
    if request.method == "POST":
        # Crear el presupuesto principal
        presupuesto = Presupuesto.objects.create(
            paciente_nombre=request.POST.get("paciente_nombre"),
            paciente_dni=request.POST.get("paciente_dni"),
            paciente_edad=request.POST.get("paciente_edad") or None,
            paciente_direccion=request.POST.get("paciente_direccion"),
            paciente_telefono=request.POST.get("paciente_telefono"),
            obra_social=request.POST.get("obra_social"),
            medico=request.POST.get("medico"),
            diagnostico=request.POST.get("diagnostico"),
            paciente_email = request.POST.get("paciente_email"),
            user_made = request.user,
            user_updated = request.user
        )

        # Guardar items (prestaciones)
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
                # valores "limpios", si están vacíos quedan como None o string vacío
                codigo = codigos[i] if i < len(codigos) and codigos[i] else ""
                tipo = tipos[i] if i < len(tipos) and tipos[i] else ""
                nombre_prestacion = prestaciones[i] if i < len(prestaciones) and prestaciones[i] else ""
                cantidad = int(cantidades[i]) if i < len(cantidades) and cantidades[i] else 1
                precio = float(precios[i]) if i < len(precios) and precios[i] else 0
                importe = float(importes[i]) if i < len(importes) and importes[i] else 0
                iva = float(ivas[i]) if i < len(ivas) and ivas[i] else 0
                subtotal = float(subtotales[i]) if i < len(subtotales) and subtotales[i] else 0

                # Crear el item
                PresupuestoItem.objects.create(
                    presupuesto=presupuesto,
                    codigo=codigo,
                    tipo = tipo,
                    prestacion=nombre_prestacion,
                    cantidad=cantidad,
                    precio=precio,
                    importe=importe,
                    iva=iva,
                    subtotal=subtotal
                )
        return redirect("presupuestos_app:presupuestos")

    prestaciones = Prestacion.objects.all()
    return render(request, "presupuestos/agregar_presupuesto.html", {
        "prestaciones": prestaciones
    })


def get_prestacion(request, codigo):
    prestacion = get_object_or_404(Prestacion, codigo=codigo)

    if codigo=='430101':
        prestacion_desc = get_object_or_404(Prestacion, codigo='431001')
        precio_u= (prestacion.gastos+prestacion.especialista) + (prestacion_desc.gastos+prestacion_desc.especialista)
    elif codigo =='400101':
        prestacion_desc = get_object_or_404(Prestacion, codigo='431002')
        precio_u= (prestacion.gastos+prestacion.especialista) + (prestacion_desc.gastos+prestacion_desc.especialista)
    elif codigo =='340907': 
        precio_u= (prestacion.gastos+prestacion.especialista)*3
    else:
        precio_u=prestacion.gastos
    data = {
        "prestacion": prestacion.codigo,
        "nombre": prestacion.nombre,
        "precio": float(precio_u), 
    }
    return JsonResponse(data)

# views.py
def get_tipo(request, codigo):
    tipo = request.GET.get("tipo")
    
    # Lógica según código + tipo
    # Ejemplo: buscar en la BD
    try:
        prestacion = Prestacion.objects.get(codigo=codigo)
        if tipo == "gastos":
            precio = prestacion.gastos
        elif tipo == "especialista":
            precio = prestacion.especialista
        else:
            precio = prestacion.total()
        
        #logica para detectar si son codigos raros
        if codigo=='430101':
            prestacion_desc = get_object_or_404(Prestacion, codigo='431001')
            precio= (prestacion.gastos+prestacion.especialista) + (prestacion_desc.gastos+prestacion_desc.especialista)
        elif codigo =='400101':
            prestacion_desc = get_object_or_404(Prestacion, codigo='431002')
            precio= (prestacion.gastos+prestacion.especialista) + (prestacion_desc.gastos+prestacion_desc.especialista)
        elif codigo =='340907': 
            precio= (prestacion.gastos+prestacion.especialista)*3
        else:
            precio=prestacion.gastos
        
    except Prestacion.DoesNotExist:
        return JsonResponse({"error": "Código no encontrado"}, status=404)

    return JsonResponse({
        "precio": precio, 
    })

# presupuestos/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from decimal import Decimal, InvalidOperation
import csv
import io

from openpyxl import load_workbook

from .forms import NomencladorUploadForm
from .models import Prestacion

# Helper para parsear precios con formato "1.234,56" o "1234.56" o 1234.56
from decimal import Decimal, InvalidOperation

def parse_price(value):
    """
    Convierte valores a Decimal con 2 decimales.
    Acepta:
      - número (int/float/Decimal)
      - string con formato "1.234,56" (-> Decimal('1234.56'))
      - string con "1234.56"
      - "-", "", None  -> Decimal("0.00")
    Siempre devuelve un Decimal.
    """
    if value is None:
        return Decimal("0.00")

    # Si ya viene como número
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return Decimal("0.00")

    s = str(value).strip()

    if s in ("", "-"):
        return Decimal("0.00")

    # limpiar separadores y formato
    if ',' in s and '.' in s:
        # Caso "1.234.567,89" -> "1234567.89"
        s = s.replace('.', '')
        s = s.replace(',', '.')
    elif ',' in s and '.' not in s:
        # Caso "1234,56" -> "1234.56"
        s = s.replace(',', '.')
    # eliminar espacios y símbolos de moneda
    s = s.replace(' ', '').replace('$', '').replace('ARS', '')

    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")

def cargar_nomenclador(request):
    """
    Vista para subir un Excel y actualizar/crear prestaciones con la nueva estructura.
    Columnas esperadas:
    1: Código
    2: Nombre (prestación)
    3: Especialista
    4: Ayudante (ignorar)
    5: Anestesista (ignorar)
    6: Gastos
    7: Total (ignorar)
    Empieza en fila 4.
    """
    resumen = {
        'creadas': 0,
        'actualizadas': 0,
        'errores': []
    }

    if request.method == "POST":
        form = NomencladorUploadForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.cleaned_data['archivo']
            name = archivo.name.lower()

            def procesar_fila(row_index, cells):
                try:
                    # ignoramos filas en blanco
                    if all((c is None or (isinstance(c, str) and c.strip() == "")) for c in cells):
                        return

                    # columnas fijas
                    codigo = str(cells[0]).strip() if len(cells) >= 1 and cells[0] else None
                    nombre = str(cells[1]).strip() if len(cells) >= 2 and cells[1] else None
                    especialista = parse_price(cells[2]) if len(cells) >= 3 else None
                    gastos = parse_price(cells[5]) if len(cells) >= 6 else None

                    if not codigo or not nombre:
                        raise ValueError(f"Fila {row_index}: falta código o nombre")

                    if especialista is None or gastos is None:
                        raise ValueError(f"Fila {row_index}: faltan valores de especialista o gastos")

                    # Buscar prestación por código o nombre
                    prest = None
                    if codigo:  
                        prest = Prestacion.objects.filter(codigo__iexact=codigo).first()

                    if not prest and not codigo:  
                        # Solo si no hay código en la fila, buscamos por nombre
                        prest = Prestacion.objects.filter(nombre__iexact=nombre).first()

                    if prest:
                        # actualizar
                        print('Actualizado:',codigo)
                        prest.nombre = nombre
                        prest.codigo = codigo
                        prest.especialista = especialista
                        prest.gastos = gastos
                        prest.save()
                        resumen['actualizadas'] += 1
                    else:
                        # crear
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
                        if i < 4:  # saltar primeras 3 filas
                            continue
                        procesar_fila(i, list(row))

            except Exception as ex:
                resumen['errores'].append(f"Error general: {str(ex)}")

            messages.success(
                request,
                f"Nomenclador procesado. Creadas: {resumen['creadas']}, "
                f"Actualizadas: {resumen['actualizadas']}."
            )
            return render(request, 'presupuestos/cargar_nomenclador.html', {
                'form': NomencladorUploadForm(),
                'resumen': resumen
            })

    else:
        form = NomencladorUploadForm()

    return render(request, 'presupuestos/cargar_nomenclador.html', {
        'form': form,
        'resumen': resumen if 'resumen' in locals() else None
    })




    from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from .models import Presupuesto
import locale
from django.http import HttpResponse


def format_num(n):
    """Formatea número con punto de miles y coma decimal: 12345.67 → 12.345,67"""
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_presupuesto(request, pk):
    presupuesto = Presupuesto.objects.get(pk=pk)
    items = presupuesto.items.all()

    # --- Locale argentino para números ---
    locale.setlocale(locale.LC_ALL, 'es_AR.UTF-8')

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
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margen_izq, y_actual, "Hospital Privado Santa Clara de Asís S.A.")
    c.setFont("Helvetica", 10)
    y_actual -= 6*mm
    c.drawString(margen_izq, y_actual, "Urquiza 964 - 4400 Salta")
    y_actual -= 10*mm  # Separación antes de datos generales

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
    y_actual -= 10*mm

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

    colWidths = [25*mm, 75*mm, 10*mm, 15*mm, 15*mm, 15*mm, 15*mm]
    table = Table(data, colWidths=colWidths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold',8),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 7),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # Ajuste automático de altura
    table.wrapOn(c, width - margen_izq - margen_der, y_actual - 20*mm)
    table.drawOn(c, margen_izq, y_actual - (len(data)*8*mm))
    y_actual -= (len(data)*8*mm + 10*mm)  # 8mm aprox por fila

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
    y_actual -= 20*mm

    # --- Firma ---
    c.drawString(margen_izq, y_actual, f"Confecciono: {presupuesto.user_updated.first_name},{presupuesto.user_updated.last_name}")
    c.drawString(width/2, y_actual-6*mm, "_________________________")
    c.drawString(width/2, y_actual-12*mm, "Firma Autorizado")

    c.showPage()
    c.save()
    return response