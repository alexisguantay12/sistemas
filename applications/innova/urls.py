from django.urls import path

from . import views

app_name = "innova_app"

urlpatterns = [
    path("", views.dashboard_llamadores, name="dashboard_llamadores"),
    path("dashboard/resumen/", views.dashboard_resumen_ajax, name="dashboard_resumen_ajax"),
    path("dashboard/en-espera/", views.llamadores_en_espera_ajax, name="llamadores_en_espera_ajax"),
    path("dashboard/frecuencia-por-letra/", views.frecuencia_llamadores_por_letra_ajax, name="frecuencia_llamadores_por_letra_ajax"),
    path("dashboard/atenciones-por-usuario/", views.atenciones_por_usuario_ajax, name="atenciones_por_usuario_ajax"),
    path("dashboard/evolucion-tiempo-promedio/", views.evolucion_tiempo_promedio_ajax, name="evolucion_tiempo_promedio_ajax"),
    path("llamadores/estadisticas/", views.estadisticas_llamadores, name="estadisticas_llamadores"),
    path("llamadores/estadisticas/resumen/", views.estadisticas_resumen_ajax, name="estadisticas_resumen_ajax"),
    path("llamadores/estadisticas/frecuencia-letras/", views.estadisticas_frecuencia_por_letra_ajax, name="estadisticas_frecuencia_por_letra_ajax"),
    path("llamadores/estadisticas/promedio-letra/", views.estadisticas_promedio_por_letra_ajax, name="estadisticas_promedio_por_letra_ajax"),
    path("llamadores/estadisticas/atenciones-usuario/", views.estadisticas_atenciones_por_usuario_ajax, name="estadisticas_atenciones_por_usuario_ajax"),
    path("llamadores/estadisticas/evolucion/", views.estadisticas_evolucion_ajax, name="estadisticas_evolucion_ajax"),
    path("llamadores/estadisticas/detalle-diario/", views.estadisticas_detalle_diario_ajax, name="estadisticas_detalle_diario_ajax"),
    path(
        "dashboard/altas-medicas-pendientes/",
        views.altas_medicas_pendientes_ajax,
        name="altas_medicas_pendientes_ajax",
    ),
]
