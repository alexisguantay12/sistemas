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
    path("codigos-particulares/", views.codigos_particulares, name="codigos_particulares"),
    path("codigos-particulares/eliminar/<int:pk>/", views.eliminar_codigo_particular, name="eliminar_codigo_particular"),
    path("autorizar/<int:pk>/", views.autorizar_presupuesto, name="autorizar_presupuesto"),
    path('cerrar/<int:pk>/', views.cerrar_presupuesto, name='cerrar_presupuesto'),
    path("clausulas/",views.gestion_clausulas,name="gestion_clausulas"),
    path(
        "reporte/presupuestos-fecha/",
        views.reporte_presupuestos_fecha,
        name="reporte_presupuestos_fecha"
    ),
    path("reporte-pagos-fecha/", views.reporte_pagos_fecha, name="reporte_pagos_fecha"),
    path("presupuesto/<int:pk>/registrar-reintegro/", views.registrar_reintegro, name="registrar_reintegro"),
    path('detalle/eliminar-reintegro/<int:pk>/',views.eliminar_reintegro, name = 'eliminar_reintegro'),
    path('detalle/guardar-datos-internacion/<int:pk>/',views.guardar_datos_internacion, name = 'guardar_datos_internacion'),
    
    ##REPORTES
    path("reportes/resumen-general/",views.reporte_resumen_general,name="reporte_resumen_general"),
    path("reportes/presupuestos/",views.reporte_presupuestos,name="reporte_presupuestos"),
    path('reportes/pagos/', views.reporte_pagos, name='reporte_pagos'),
    path('reportes/reintegros/', views.reporte_reintegros, name='reporte_reintegros'),
]
