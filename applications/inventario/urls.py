from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.listar_pcs, name='lista_pc'),
    path('pc/agregar/', views.agregar_pc, name='pc_agregar'),
    path('pc/editar/<int:pk>/', views.editar_pc, name='editar_pc'),
    path('pc/eliminar/<int:pk>/', views.eliminar_pc, name='pc_eliminar'),
    path('pc/<int:pk>/', views.detalle_pc, name='pc_detalle'),
    path('pc/verificar_nombre/',views.verificar_nombre_terminal, name='verificar_nombre_terminal'),
    path('servidores/', views.lista_servidores, name='lista_servidores'),
    path('servidores/agregar_servidor/', views.agregar_servidor, name='agregar_servidor'),
    path('servidor/<int:pk>/', views.detalle_servidor, name='detalle_servidor'),
    path('perifericos/', views.lista_impresoras, name='lista_impresoras'),
    path('perifericos/agregar_periferico/', views.agregar_impresora, name='agregar_impresora'),
    path('periferico/<int:pk>/', views.detalle_impresora, name='detalle_impresora'),
    path('dashboard/',views.dashboard_sectores,name = 'dashboard')
]
