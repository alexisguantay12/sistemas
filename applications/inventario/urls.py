from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.listar_pcs, name='lista_pc'),
    path('pc/agregar/', views.agregar_pc, name='pc_agregar'),
    path('pc/editar/<int:pk>/', views.editar_pc, name='pc_editar'),
    path('pc/eliminar/<int:pk>/', views.eliminar_pc, name='pc_eliminar'),
    path('pc/<int:pk>/', views.detalle_pc, name='pc_detalle'),
]
