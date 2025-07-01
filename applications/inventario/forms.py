from django import forms
from .models import Terminal

class TerminalForm(forms.ModelForm):
    class Meta:
        model = Terminal
        fields = ['nombre', 'mac', 'descripcion', 'ubicacion', 'estado']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 1, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['autocomplete'] = 'off'
