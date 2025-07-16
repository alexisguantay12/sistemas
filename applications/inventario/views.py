from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Terminal, Componente, Servidor,Ubicacion,Sector
from .forms import TerminalForm

@login_required
def listar_pcs(request):
    pcs = Terminal.objects.all()
    return render(request, 'inventario/terminales.html', {'pcs': pcs})



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from .models import Terminal, Componente, ComponenteStock, Ubicacion

def editar_pc(request, pk):
    terminal = get_object_or_404(Terminal, id=pk)
    ubicaciones = Ubicacion.objects.all()
    componentes = terminal.componentes.all()

    if request.method == 'POST' and 'guardar' in request.POST:
        try:
            with transaction.atomic():
                # --- Actualización de la Terminal ---
                terminal.ubicacion_id = request.POST.get('ubicacion')
                terminal.estado = request.POST.get('estado')
                terminal.descripcion = request.POST.get('descripcion')
                terminal.save()

                # --- Actualización del estado de los componentes asociados ---
                for componente in componentes:
                    nuevo_estado = request.POST.get(f'componente_estado_{componente.id}')
                    if nuevo_estado and nuevo_estado != componente.estado:
                        componente.estado = nuevo_estado
                        componente.save()

                # --- Eliminar componentes removidos ---
                ids_eliminados = request.POST.getlist('componentes_eliminados')
                for cid in ids_eliminados:
                    Componente.objects.filter(id=cid, terminal=terminal).delete()

                # --- Transferir componentes al stock ---
                ids_transferidos = request.POST.getlist('componentes_transferidos')
                for cid in ids_transferidos:
                    componente = Componente.objects.filter(id=cid, terminal=terminal).first()
                    if componente:
                        stock_obj = ComponenteStock.objects.filter(
                            tipo=componente.tipo,
                            marca=componente.marca,
                            estado=componente.estado
                        ).first()

                        if stock_obj:
                            stock_obj.stock = (stock_obj.stock or 0) + 1
                            stock_obj.save()
                        else:
                            ComponenteStock.objects.create(
                                tipo=componente.tipo,
                                marca=componente.marca,
                                descripcion=componente.descripcion,
                                nro_serie=componente.nro_serie,
                                estado=componente.estado,
                                stock=1,
                                user_made=request.user
                            )

                        componente.delete()

                # --- Agregar nuevos componentes desde el stock ---
                ids_agregados = request.POST.getlist('componentes_agregados')
                for sid in ids_agregados:
                    stock_item = ComponenteStock.objects.filter(id=sid).first()
                    if stock_item and (stock_item.stock or 0) > 0:
                        stock_item.stock -= 1
                        stock_item.save()

                        Componente.objects.create(
                            tipo=stock_item.tipo,
                            marca=stock_item.marca,
                            descripcion=stock_item.descripcion,
                            nro_serie=stock_item.nro_serie,
                            estado=stock_item.estado,
                            terminal=terminal,
                            user_made=request.user
                        )

                messages.success(request, "Cambios guardados correctamente.")
                return redirect('inventario:lista_pc')

        except Exception as e:
            messages.error(request, f"Ocurrió un error al guardar los cambios: {str(e)}")

    return render(request, 'inventario/editar_pc.html', {
        'terminal': terminal,
        'ubicaciones': ubicaciones,
        'componentes': componentes,
    })



def obtener_ubicaciones(request):
    sector_id = request.GET.get("sector_id")
    ubicaciones = Ubicacion.objects.filter(sector_id=sector_id).values("id", "nombre").order_by('nombre') # Ajusta campos según tu modelo
    return JsonResponse(list(ubicaciones), safe=False)

@login_required
def agregar_pc(request):
    if request.method == 'POST':
        import json

        nombre = request.POST.get('nombre')
        mac = request.POST.get('mac')
        descripcion = request.POST.get('descripcion-pc')
        ubicacion_id = request.POST.get('ubicacion')
        estado = request.POST.get('estado-pc')
        componentes_json = request.POST.get('componentes_json', '[]')
        
        print(descripcion)
        print('Descripcion',estado)

        try:
            componentes = json.loads(componentes_json)
        except json.JSONDecodeError:
            componentes = []

        if Terminal.objects.filter(nombre__iexact=nombre).exists():
            return render(request, 'inventario/agregar_pc.html', {
                'error': 'Ya existe una PC con ese nombre.',
                'ubicaciones': Ubicacion.objects.all(),
                'sectores':Sector.objects.all().order_by('nombre'),
                'estados': Terminal.ESTADO_CHOICES
            })

        try:
            with transaction.atomic():
                terminal = Terminal.objects.create(
                    nombre=nombre,
                    mac=mac,
                    descripcion=descripcion,
                    ubicacion_id=ubicacion_id,
                    estado=estado,
                    user_made=request.user
                )

                for comp in componentes:
                    Componente.objects.create(
                        tipo=comp['tipo'],
                        descripcion=comp['descripcion'],
                        marca=comp['marca'],
                        estado=comp['estado'],
                        terminal=terminal,
                        user_made=request.user
                    )

            return redirect('inventario:lista_pc')
        
        except Exception as e:
            print('Error',{str(e)})
            return render(request, 'inventario/agregar_pc.html', {
                'error': f'Ocurrió un error: {str(e)}',
                'ubicaciones': Ubicacion.objects.all(),
                'sectores':Sector.objects.all().order_by('nombre'),
                'estados': Terminal.ESTADO_CHOICES
            })

    return render(request, 'inventario/agregar_pc.html', {
        'ubicaciones': Ubicacion.objects.all(),
        'sectores':Sector.objects.all().order_by('nombre')
    })


@login_required
def verificar_nombre_terminal(request):
    nombre = request.GET.get('nombre', '').strip()
    existe = Terminal.objects.filter(nombre__iexact=nombre).exists()
    return JsonResponse({'exists': existe})

 
@login_required
def detalle_pc(request, pk):
    terminal = get_object_or_404(Terminal, pk=pk)
    componentes = Componente.objects.filter(terminal=terminal)
    return render(request, 'inventario/detalles_pc.html', {
        'terminal': terminal,
        'componentes': componentes
    })

@csrf_exempt
@login_required
def eliminar_pc(request, pk):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                pc = Terminal.objects.get(pk=pk)
                pc.delete()
                return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

from django.contrib import messages
from django.utils import timezone


def agregar_servidor(request):
    if request.method == 'POST':
        hostname = request.POST.get('hostname')
        ip = request.POST.get('ip')
        mac = request.POST.get('mac')
        sistema_operativo = request.POST.get('sistema_operativo')
        version_so = request.POST.get('version_so')
        rol_principal = request.POST.get('rol_principal')
        estado = request.POST.get('estado')
        ubicacion_id = request.POST.get('ubicacion')
        ultima_revision = request.POST.get('ultima_revision')
        max_ram = request.POST.get('max_ram')
        max_disco = request.POST.get('max_disco')
        cantidad_puertos = request.POST.get('cantidad_puertos')

        # Validación mínima
        if not hostname or not sistema_operativo or not estado or not ubicacion_id:
            messages.error(request, 'Por favor, completá los campos obligatorios.')
            return redirect('inventario:agregar_servidor')

        # Crear instancia
        servidor = Servidor(
            hostname=hostname,
            ip=ip,
            mac=mac,
            sistema_operativo=sistema_operativo,
            version_so=version_so,
            rol_principal=rol_principal,
            estado=estado,
            ubicacion=Ubicacion.objects.get(id=ubicacion_id) if ubicacion_id else None,
            fecha_alta=timezone.now(),
            ultima_revision=ultima_revision if ultima_revision else None,
            max_ram=int(max_ram) if max_ram else None,
            max_disco=int(max_disco) if max_disco else None,
            cantidad_puertos=int(cantidad_puertos) if cantidad_puertos else None,
            user_made=request.user  # asumiendo BaseAbstractWithUser tiene 'usuario'
        )

        servidor.save()
        messages.success(request, 'Servidor registrado correctamente.')
        return redirect('inventario:lista_servidores')

    ubicaciones = Ubicacion.objects.all()
    return render(request, 'inventario/agregar_servidor.html', {'ubicaciones': ubicaciones})


from .models import ComponenteStock
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q
from .models import ComponenteStock
def buscar_componentes(request):
    query = request.GET.get("q", "").strip().lower()

    if not query:
        return JsonResponse([], safe=False)

    # Traemos todos los componentes (o podés limitar a los con stock > 0 si querés)
    todos_los_componentes = ComponenteStock.objects.all()

    # Filtramos en Python por cualquier campo relevante incluyendo el display del tipo
    componentes_filtrados = [
        c for c in todos_los_componentes
        if query in c.get_tipo_display().lower()
        or query in (c.tipo or '').lower()
        or query in (c.marca or '').lower()
        or query in (c.descripcion or '').lower()
    ]

    # Limitamos a 30 resultados
    componentes = componentes_filtrados[:30]

    # Serializamos
    data = [
        {
            "id": c.id,
            "tipo": c.get_tipo_display(),
            "marca": c.marca,
            "descripcion": c.descripcion,
            "stock": c.stock,
            "estado": c.estado,
        }
        for c in componentes
    ]

    return JsonResponse(data, safe=False)

@login_required
def agregar_componente(request):
    import json
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            componente = ComponenteStock.objects.create(
                user_made=request.user,
                tipo=data.get('tipo'),
                marca=data.get('marca', ''),
                nro_serie=data.get('nro_serie', ''),
                estado=data.get('estado'),
                stock=int(data.get('stock', 1)),
                descripcion=data.get('descripcion', '')
            )

            return JsonResponse({'success': True, 'id': componente.id})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return render(request, 'inventario/agregar_componente.html')


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import ComponenteStock

@login_required
def listar_componentes(request):
    componentes = ComponenteStock.objects.all().order_by('-id')
    return render(request, 'inventario/listar_componentes.html', {'componentes': componentes})



def lista_servidores(request):
    servidores = Servidor.objects.select_related('ubicacion').all().order_by('hostname')
    return render(request, 'inventario/servidores.html', {'servidores': servidores})



@login_required
def detalle_servidor(request, pk):
    servidor = get_object_or_404(Servidor, pk=pk)
    componentes = []
    return render(request, 'inventario/detalles_servidor.html', {
        'servidor': servidor,
        'componentes': componentes
    })



from django.shortcuts import render, redirect
from django.contrib import messages
from .models import DispositivoPeriferico, Ubicacion
from django.utils import timezone

def agregar_impresora(request):
    ubicaciones = Ubicacion.objects.all()

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        marca = request.POST.get('marca')
        modelo = request.POST.get('modelo')
        nro_serie = request.POST.get('nro_serie')
        conexion = request.POST.get('conexion')
        ip = request.POST.get('ip')
        estado = request.POST.get('estado')
        observaciones = request.POST.get('observaciones')
        ubicacion_id = request.POST.get('ubicacion_id')

        if not (tipo and marca and estado and ubicacion_id):
            messages.error(request, "Faltan datos obligatorios.")
            return redirect('inventario:agregar_impresora')

        periferico = DispositivoPeriferico.objects.create(
            tipo=tipo,
            marca=marca,
            modelo=modelo,
            nro_serie=nro_serie,
            conexion=conexion,
            ip=ip,
            estado=estado,
            observaciones=observaciones,
            ubicacion_id=ubicacion_id,
            user_made=request.user  # si usás BaseAbstractWithUser
        )

        messages.success(request, "Dispositivo registrado con éxito.")
        return redirect('inventario:lista_impresoras')

    return render(request, 'inventario/agregar_impresora.html', {
        'ubicaciones': ubicaciones
    })


def lista_impresoras(request):
    perifericos = DispositivoPeriferico.objects.select_related('ubicacion').all().order_by('created_at')
    return render(request, 'inventario/impresoras.html', {'perifericos': perifericos})



def detalle_impresora(request, pk):
    dispositivo = get_object_or_404(DispositivoPeriferico, id=pk)
    return render(request, 'inventario/detalles_impresora.html', {
        'dispositivo': dispositivo
    })


 

def dashboard_sectores(request):
    sectores = Ubicacion.objects.all()

    data = []
    for sector in sectores:
        data.append({
            'nombre': sector.nombre,
            'id': sector.id,
            #'responsable': sector.responsable,
            'pc_count': Terminal.objects.filter(ubicacion=sector).count(),
            'impresora_count': DispositivoPeriferico.objects.filter(ubicacion=sector, tipo='IMPRESORA').count(),
            'escaner_count': DispositivoPeriferico.objects.filter(ubicacion=sector, tipo='ESCANER').count(),
            'servidor_count': Servidor.objects.filter(ubicacion=sector).count(),
        })

    context = {
        'sectores': data,
        'total_pcs': Terminal.objects.count(),
        'total_impresoras': DispositivoPeriferico.objects.filter(tipo='IMPRESORA').count(),
        'total_escaneres': DispositivoPeriferico.objects.filter(tipo='ESCANER').count(),
        'total_servidores': Servidor.objects.count(), 
    }

    return render(request, 'inventario/panel.html', context)
