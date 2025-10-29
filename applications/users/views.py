# configuracion/views.py

from django.shortcuts import render, redirect
from applications.users.forms import CrearUsuarioForm
from applications.users.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.forms import AuthenticationForm

def crear_usuario(request):
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('users_app:lista_usuarios')
    else:
        form = CrearUsuarioForm()
    return render(request, 'users/crear_usuario.html', {'form': form})

def lista_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'users/lista_usuarios.html', {'usuarios': usuarios})



from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash


@login_required
def cambiar_contraseña(request):
    # Limpia mensajes antiguos
    storage = messages.get_messages(request)
    for _ in storage:
        pass

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, '✅ La contraseña fue actualizada correctamente.')
            return redirect('presupuestos_app:presupuestos')
        else:
            # Traducción manual de errores (modifica el form directamente)
            for field, errors in form.errors.items():
                errores_traducidos = []
                for error in errors:
                    error = str(error)
                    if "too similar" in error:
                        error = "La contraseña es demasiado similar al nombre de usuario."
                    elif "too short" in error or "at least 8 characters" in error:
                        error = "La contraseña debe tener al menos 8 caracteres."
                    elif "too common" in error:
                        error = "La contraseña es demasiado común."
                    elif "didn’t match" in error or "did not match" in error:
                        error = "Las contraseñas nuevas no coinciden."
                    elif "incorrect" in error:
                        error = "La contraseña actual es incorrecta."
                    errores_traducidos.append(error)
                form.errors[field] = errores_traducidos  # sobrescribimos los errores traducidos
            messages.error(request, '❌ Corrige los errores antes de continuar.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'users/cambiar_contraseña.html', {'form': form})


def login_view(request):
    storage = messages.get_messages(request)
    list(storage)  # consumir completamente los mensajes antiguos
    if request.user.is_authenticated:
        return redirect('core_app:home')

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'presupuestos_app:presupuestos')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('users_app:login')