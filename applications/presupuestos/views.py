from django.shortcuts import render,redirect
from .models import Presupuesto, PresupuestoItem, Prestacion
from django.db import transaction 
from django.http import JsonResponse
from django.shortcuts import get_object_or_404


def lista_presupuestos(request):
    presupuestos = Presupuesto.objects.all().order_by('-fecha_creacion')
    return render(request, 'presupuestos/presupuestos.html', {'presupuestos': presupuestos})

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
        )

        # Guardar items (prestaciones)
        codigos = request.POST.getlist("codigo")
        prestaciones = request.POST.getlist("prestacion")
        cantidades = request.POST.getlist("cantidad")

        with transaction.atomic():
            for i in range(len(prestaciones)):
                if prestaciones[i]:
                    prestacion = Prestacion.objects.get(pk=prestaciones[i])
                    PresupuestoItem.objects.create(
                        presupuesto=presupuesto,
                        prestacion=prestacion,
                        cantidad=int(cantidades[i]) if cantidades[i] else 1
                    )

        return redirect("presupuestos:presupuestos")

    prestaciones = Prestacion.objects.all()
    return render(request, "presupuestos/agregar_presupuesto.html", {
        "prestaciones": prestaciones
    })


def get_prestacion(request, codigo):
    prestacion = get_object_or_404(Prestacion, codigo=codigo)

    data = {
        "prestacion": prestacion.codigo,
        "nombre": prestacion.nombre,
        "precio": float(prestacion.precio), 
    }
    return JsonResponse(data)