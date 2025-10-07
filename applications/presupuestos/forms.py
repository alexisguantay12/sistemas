# presupuestos/forms.py
from django import forms

class NomencladorUploadForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo (xlsx, xlsm o csv)",
        help_text="Subí un archivo Excel (.xlsx/.xlsm) o CSV con columnas: código, nombre, precio"
    )
