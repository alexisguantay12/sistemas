from django.urls import path

from . import views


app_name = "innova_app"


urlpatterns = [
    path(
        "",
        views.dashboard_llamadores,
        name="dashboard_llamadores",
    ),
    path(
        "dashboard/en-espera/",
        views.llamadores_en_espera_ajax,
        name="llamadores_en_espera_ajax",
    ),
    path(
    "dashboard/frecuencia-por-letra/",
    views.frecuencia_llamadores_por_letra_ajax,
    name="frecuencia_llamadores_por_letra_ajax",
    ),path(
    "dashboard/atenciones-por-usuario/",
    views.atenciones_por_usuario_ajax,
    name="atenciones_por_usuario_ajax",
    ),
    path(
        "dashboard/evolucion-tiempo-promedio/",
        views.evolucion_tiempo_promedio_ajax,
        name="evolucion_tiempo_promedio_ajax",
    ),
]