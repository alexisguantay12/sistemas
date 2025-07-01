# configuracion/forms.py

from django import forms
from .models import User
from django.contrib.auth.models import Group
from applications.inventario.models import Ubicacion
 
class CrearUsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Contraseña'
    )
    rol = forms.ChoiceField(
        choices=[
            ('administrador', 'Administrador'),
            ('vendedor', 'Vendedor'),
            ('cargador', 'Cargador')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Rol'
    )
    ubicacion = forms.ModelChoiceField(
        queryset=Ubicacion.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Local'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'rol', 'ubicacion']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
        }
        labels = {
            'username': 'Usuario',
            'email': 'Correo electrónico',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()

            # Asignar grupo
            group_name = self.cleaned_data['rol']
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

            # Asociar local si es vendedor
            if group_name == 'vendedor' and self.cleaned_data['ubicacion']:
                user.ubicacion = self.cleaned_data['ubicacion']
                user.save()
        return user
