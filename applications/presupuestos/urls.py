from django.urls import path
from . import views

app_name = "presupuestos_app"

urlpatterns = [
    path('', views.lista_presupuestos, name='presupuestos'), 
    path('agregar/', views.agregar_presupuesto, name='agregar_presupuesto'), 
    path("get_prestacion/<str:codigo>/", views.get_prestacion, name="get_prestacion"),

]
