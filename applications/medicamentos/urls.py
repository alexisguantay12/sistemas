from django.urls import path
from applications.medicamentos.views import *

urlpatterns = [
    path('', medicamentos, name='medicamentos'), 
 
    path('upload-excel/', upload_excel, name='upload_excel'),
  
    path('comparar-pacientes/', compare_patients, name='comparar_pacientes'),
 
    path('upload-txt/', upload_txt, name='upload_txt'),
]
