from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Terminal, Componente
from .forms import TerminalForm

@login_required
def listar_pcs(request):
    pcs = Terminal.objects.all()
    return render(request, 'inventario/terminales.html', {'pcs': pcs})


@login_required
def agregar_pc(request):
    if request.method == 'POST':
        import json
        form = TerminalForm(request.POST)
        if form.is_valid():
            componentes_json = request.POST.get('componentes_json', '[]')
            componentes = json.loads(componentes_json)

            try:
                with transaction.atomic():
                    terminal = form.save(commit=False)
                    terminal.user_made = request.user
                    terminal.save()

                    for comp in componentes:
                        Componente.objects.create(
                            tipo=comp['tipo'],
                            descripcion=comp['descripcion'],
                            marca=comp['marca'],  # corregido de 'morca'
                            nro_serie=comp['nro_serie'],
                            estado=comp['estado'],
                            terminal=terminal,
                            user_made=request.user
                        )
                return redirect('inventario:lista_pc')

            except Exception as e:
                form.add_error(None, f"Ocurrió un error al guardar: {e}")

    else:
        form = TerminalForm()
    return render(request, 'inventario/agregar_pc.html', {'form': form})

@login_required
def editar_pc(request, pk):
    pc = get_object_or_404(Terminal, pk=pk)
    if request.method == 'POST':
        form = TerminalForm(request.POST, instance=pc)
        if form.is_valid():
            form.save()
            return redirect('inventario:pc_listar')
    else:
        form = TerminalForm(instance=pc)
    return render(request, 'inventario/pc_form.html', {'form': form, 'modo': 'editar'})


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
