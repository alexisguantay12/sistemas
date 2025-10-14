from django.urls import path
from . import views

app_name = "presupuestos_app"

urlpatterns = [
    path('', views.lista_presupuestos, name='presupuestos'), 
    path('agregar/', views.agregar_presupuesto, name='agregar_presupuesto'), 
    path("get_prestacion/<str:codigo>/", views.get_prestacion, name="get_prestacion"),
    path('cargar-nomenclador/', views.cargar_nomenclador, name='cargar_nomenclador'),
    # urls.py
    path("get_tipo/<str:codigo>/", views.get_tipo, name="get_tipo"),
    path('presupuesto/<int:pk>/', views.detalle_presupuesto, name='detalle_presupuesto'),
    path('editar-presupuesto/<int:pk>/', views.editar_presupuesto, name='editar_presupuesto'),    
    path('datalle/registrar-pago/<int:pk>/',views.registrar_pago, name= 'registrar_pago'),
    path('imprimir/<int:pk>/', views.imprimir_presupuesto, name='imprimir_presupuesto'),
    path('buscar_nomenclador/', views.buscar_nomenclador, name='buscar_nomenclador'),
    path('detalle/eliminar-pago/<int:pk>/',views.eliminar_pago, name = 'eliminar_pago'),
]
