from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Terminal, Componente, Servidor,Ubicacion
from .forms import TerminalForm

@login_required
def listar_pcs(request):
    pcs = Terminal.objects.all()
    return render(request, 'inventario/terminales.html', {'pcs': pcs})



from django.shortcuts import render, get_object_or_404, redirect
from .models import Terminal, Componente, Ubicacion
from django.contrib import messages

def editar_pc(request, pk):
    terminal = get_object_or_404(Terminal, pk=pk)
    componentes = terminal.componentes.all()  # related_name en modelo Componente
    ubicaciones = Ubicacion.objects.all()

    if request.method == 'POST':

        # 🟢 GUARDAR CAMBIOS GENERALES
        if 'guardar' in request.POST:
            terminal.ubicacion_id = request.POST.get('ubicacion')
            terminal.estado = request.POST.get('estado')
            terminal.descripcion = request.POST.get('descripcion')
            terminal.save()

            # Actualizar estado de componentes
            for componente in componentes:
                key = f'componente_estado_{componente.id}'
                if key in request.POST:
                    nuevo_estado = request.POST[key]
                    if nuevo_estado != componente.estado:
                        componente.estado = nuevo_estado
                        componente.save()
            messages.success(request, "Cambios guardados correctamente.")
            return redirect('inventario:editar_pc', pk=pk)

        # 🔄 TRANSFERIR COMPONENTE (desligar de la PC)
        elif 'transferir' in request.POST:
            componente_id = request.POST.get('transferir')
            componente = get_object_or_404(Componente, id=componente_id)
            componente.pc = None
            componente.save()
            messages.info(request, f"Componente '{componente.get_tipo_display()}' transferido.")
            return redirect('inventario:editar_pc', pk=pk)

        # ➕ AGREGAR NUEVO COMPONENTE
        elif 'agregar_componente' in request.POST:
            tipo = request.POST.get('nuevo_tipo')
            marca = request.POST.get('nuevo_marca')
            descripcion = request.POST.get('nuevo_descripcion')

            if tipo and marca:
                nuevo = Componente.objects.create(
                    tipo=tipo.upper(),
                    marca=marca,
                    descripcion=descripcion,
                    estado='OK',  # Estado inicial por defecto
                    pc=terminal
                )
                messages.success(request, f"Componente '{nuevo.tipo}' agregado a la PC.")
            else:
                messages.warning(request, "Tipo y marca son obligatorios para agregar un componente.")
            return redirect('inventario:editar_pc', pk=pk)

    return render(request, 'inventario/editar_pc.html', {
        'terminal': terminal,
        'componentes': componentes,
        'ubicaciones': ubicaciones,
    })

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
                'estados': Terminal.ESTADO_CHOICES
            })

    return render(request, 'inventario/agregar_pc.html', {
        'ubicaciones': Ubicacion.objects.all() 
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
            'responsable': sector.responsable,
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