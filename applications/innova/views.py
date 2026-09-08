from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


def formatear_segundos(segundos):
    segundos = int(segundos or 0)
    minutos = segundos // 60
    segundos_restantes = segundos % 60
    return f"{minutos} min {segundos_restantes:02d} seg"


def obtener_rango_fechas(request):
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")
    if not fecha_desde or not fecha_hasta:
        raise ValueError("Debe indicar fecha_desde y fecha_hasta.")
    try:
        fecha_desde = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
        fecha_hasta = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Las fechas deben tener formato YYYY-MM-DD.")
    if fecha_desde > fecha_hasta:
        raise ValueError("La fecha desde no puede ser mayor que la fecha hasta.")
    return fecha_desde, fecha_hasta


def respuesta_error(error, status=500):
    return JsonResponse({"success": False, "error": str(error)}, status=status)


@login_required
def dashboard_llamadores(request):
    return render(request, "innova/llamadores/llamadores_totem.html")


@login_required
def estadisticas_llamadores(request):
    return render(request, "innova/llamadores/estadisticas.html")


@login_required
@require_GET
def llamadores_en_espera_ajax(request):
    """
    Tickets abiertos de hoy que todavia no poseen un llamado valido finalizado.
    Un llamado valido es:
      - Solicitud IdEstadoActual = 5 (Finalizado)
      - Llamado IdEstadoActual = 4 (Finalizado)
    """
    consulta = """
        ;WITH LlamablesDia AS (
            SELECT Id, Sujeto, FechaAlta, FechaBaja
            FROM Llamadores.Llamadores_Llamables
            WHERE IdTipoLlamable = 3
            AND FechaAlta >= CONVERT(date, GETDATE())
            AND FechaAlta < DATEADD(DAY, 1, CONVERT(date, GETDATE()))
            AND FechaBaja IS NULL
        ),
        Solicitudes AS (
            SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
            FROM Llamadores.Llamadores_SolicitudesDeLlamado s
            INNER JOIN LlamablesDia ll ON ll.Id = s.Id_Llamable
            UNION ALL
            SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
            FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
            INNER JOIN LlamablesDia ll ON ll.Id = s.Id_Llamable
        ),
        Llamados AS (
            SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
            FROM Llamadores.Llamadores_Llamados l
            INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            UNION ALL
            SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
            FROM Llamadores.Llamadores_Llamados_Historico l
            INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
        ),
        LlamadosValidos AS (
            SELECT DISTINCT s.Id_Llamable
            FROM Solicitudes s
            INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
            WHERE s.IdEstadoActual = 5
            AND l.IdEstadoActual = 4
        )
        SELECT
            ll.Sujeto,
            ll.FechaAlta,
            DATEDIFF(SECOND, ll.FechaAlta, GETDATE()) AS SegundosEspera
        FROM LlamablesDia ll
        LEFT JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id
        WHERE lv.Id_Llamable IS NULL
        ORDER BY ll.FechaAlta ASC;
    """
    try:
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        llamadores = []
        for sujeto, fecha_alta, segundos_espera in filas:
            llamadores.append({
                "sujeto": str(sujeto),
                "fecha_alta": fecha_alta.isoformat() if fecha_alta else None,
                "segundos_espera": int(segundos_espera or 0),
            })
        return JsonResponse({"success": True, "total": len(llamadores), "llamadores": llamadores})
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def dashboard_resumen_ajax(request):
    consulta = """
        ;WITH LlamablesDia AS (
            SELECT Id, FechaAlta
            FROM Llamadores.Llamadores_Llamables
            WHERE IdTipoLlamable = 3
            AND FechaAlta >= CONVERT(date, GETDATE())
            AND FechaAlta < DATEADD(DAY, 1, CONVERT(date, GETDATE()))
        ),
        Solicitudes AS (
            SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
            FROM Llamadores.Llamadores_SolicitudesDeLlamado s
            INNER JOIN LlamablesDia ll ON ll.Id = s.Id_Llamable
            UNION ALL
            SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
            FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
            INNER JOIN LlamablesDia ll ON ll.Id = s.Id_Llamable
        ),
        Llamados AS (
            SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
            FROM Llamadores.Llamadores_Llamados l
            INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            UNION ALL
            SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
            FROM Llamadores.Llamadores_Llamados_Historico l
            INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
        ),
        LlamadosValidos AS (
            SELECT
                s.Id_Llamable,
                l.FechaAlta AS FechaLlamado,
                ROW_NUMBER() OVER (
                    PARTITION BY s.Id_Llamable
                    ORDER BY l.FechaAlta ASC
                ) AS rn
            FROM Solicitudes s
            INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
            WHERE s.IdEstadoActual = 5
            AND l.IdEstadoActual = 4
        ),
        Resultado AS (
            SELECT
                ll.Id,
                ll.FechaAlta AS FechaTicket,
                lv.FechaLlamado,
                CASE
                    WHEN lv.FechaLlamado IS NULL THEN NULL
                    WHEN DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado) < 0 THEN 30
                    ELSE DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado)
                END AS SegundosEspera
            FROM LlamablesDia ll
            LEFT JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id AND lv.rn = 1
        )
        SELECT
            COUNT(*) AS TotalIngresados,
            SUM(CASE WHEN FechaLlamado IS NOT NULL THEN 1 ELSE 0 END) AS TotalLlamados,
            AVG(CAST(SegundosEspera AS FLOAT)) AS PromedioSegundos,
            MAX(SegundosEspera) AS MaximoSegundos
        FROM Resultado;
    """
    try:
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta)
            fila = cursor.fetchone()
        total_ingresados = int(fila[0] or 0)
        total_llamados = int(fila[1] or 0)
        promedio_segundos = int(fila[2] or 0)
        maximo_segundos = int(fila[3] or 0)
        porcentaje_llamados = round(total_llamados * 100 / total_ingresados, 1) if total_ingresados else 0
        return JsonResponse({
            "success": True,
            "total_ingresados": total_ingresados,
            "total_llamados": total_llamados,
            "porcentaje_llamados": porcentaje_llamados,
            "promedio_segundos": promedio_segundos,
            "promedio_formateado": formatear_segundos(promedio_segundos),
            "maximo_segundos": maximo_segundos,
            "maximo_formateado": formatear_segundos(maximo_segundos),
        })
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def frecuencia_llamadores_por_letra_ajax(request):
    consulta = """
        ;WITH LlamablesDia AS (
            SELECT Id, Sujeto, FechaAlta
            FROM Llamadores.Llamadores_Llamables
            WHERE IdTipoLlamable = 3
            AND FechaAlta >= CONVERT(date, GETDATE())
            AND FechaAlta < DATEADD(DAY, 1, CONVERT(date, GETDATE()))
            AND NULLIF(LTRIM(RTRIM(Sujeto)), '') IS NOT NULL
        ),
        Solicitudes AS (
            SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
            FROM Llamadores.Llamadores_SolicitudesDeLlamado s
            INNER JOIN LlamablesDia ll ON ll.Id = s.Id_Llamable
            UNION ALL
            SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
            FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
            INNER JOIN LlamablesDia ll ON ll.Id = s.Id_Llamable
        ),
        Llamados AS (
            SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
            FROM Llamadores.Llamadores_Llamados l
            INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            UNION ALL
            SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
            FROM Llamadores.Llamadores_Llamados_Historico l
            INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
        ),
        LlamadosValidos AS (
            SELECT
                s.Id_Llamable,
                l.FechaAlta AS FechaLlamado,
                ROW_NUMBER() OVER (
                    PARTITION BY s.Id_Llamable
                    ORDER BY l.FechaAlta ASC
                ) AS rn
            FROM Solicitudes s
            INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
            WHERE s.IdEstadoActual = 5
            AND l.IdEstadoActual = 4
        ),
        Resultado AS (
            SELECT
                UPPER(LEFT(LTRIM(ll.Sujeto), 1)) AS Letra,
                CASE
                    WHEN DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado) < 0 THEN 30
                    ELSE DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado)
                END AS SegundosEspera
            FROM LlamablesDia ll
            INNER JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id AND lv.rn = 1
        )
        SELECT Letra, COUNT(*) AS Cantidad, AVG(SegundosEspera) AS PromedioSegundos
        FROM Resultado
        GROUP BY Letra
        ORDER BY Letra;
    """
    try:
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        resultados = []
        for letra, cantidad, promedio_segundos in filas:
            promedio_segundos = int(promedio_segundos or 0)
            resultados.append({
                "letra": letra,
                "cantidad": int(cantidad or 0),
                "promedio_segundos": promedio_segundos,
                "promedio_formateado": formatear_segundos(promedio_segundos),
            })
        return JsonResponse({"success": True, "resultados": resultados})
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def atenciones_por_usuario_ajax(request):
    """
    Este indicador mantiene la logica original: cuenta cierres de llamables por IdUsuarioBaja.
    No representa necesariamente al usuario que genero el llamado en pantalla.
    """
    consulta = """
        SELECT
            CONCAT(
                UPPER(LEFT(LEFT(LTRIM(p.Nombres), CHARINDEX(' ', LTRIM(p.Nombres) + ' ') - 1), 1)),
                LOWER(SUBSTRING(LEFT(LTRIM(p.Nombres), CHARINDEX(' ', LTRIM(p.Nombres) + ' ') - 1), 2, 100)),
                ' ',
                UPPER(LEFT(LEFT(LTRIM(p.Apellido), CHARINDEX(' ', LTRIM(p.Apellido) + ' ') - 1), 1)),
                LOWER(SUBSTRING(LEFT(LTRIM(p.Apellido), CHARINDEX(' ', LTRIM(p.Apellido) + ' ') - 1), 2, 100))
            ) AS Usuario,
            COUNT(*) AS Atenciones
        FROM Llamadores.Llamadores_Llamables ll
        INNER JOIN Usuarios u ON ll.IdUsuarioBaja = u.id
        INNER JOIN Personas p ON p.id = u.IdPersona
        WHERE ll.FechaBaja IS NOT NULL
        AND ll.IdTipoLlamable = 3
        AND ll.FechaAlta >= CONVERT(date, GETDATE())
        AND ll.FechaAlta < DATEADD(DAY, 1, CONVERT(date, GETDATE()))
        GROUP BY CONCAT(
            UPPER(LEFT(LEFT(LTRIM(p.Nombres), CHARINDEX(' ', LTRIM(p.Nombres) + ' ') - 1), 1)),
            LOWER(SUBSTRING(LEFT(LTRIM(p.Nombres), CHARINDEX(' ', LTRIM(p.Nombres) + ' ') - 1), 2, 100)),
            ' ',
            UPPER(LEFT(LEFT(LTRIM(p.Apellido), CHARINDEX(' ', LTRIM(p.Apellido) + ' ') - 1), 1)),
            LOWER(SUBSTRING(LEFT(LTRIM(p.Apellido), CHARINDEX(' ', LTRIM(p.Apellido) + ' ') - 1), 2, 100))
        )
        ORDER BY Atenciones DESC;
    """
    try:
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        total_atenciones = sum(int(fila[1] or 0) for fila in filas)
        resultados = []
        for usuario, atenciones in filas:
            atenciones = int(atenciones or 0)
            porcentaje = round(atenciones * 100 / total_atenciones, 1) if total_atenciones else 0
            resultados.append({
                "usuario": usuario or "Sin identificar",
                "cantidad": atenciones,
                "porcentaje": porcentaje,
            })
        return JsonResponse({
            "success": True,
            "total_atenciones": total_atenciones,
            "resultados": resultados,
        })
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def evolucion_tiempo_promedio_ajax(request):
    consulta = """
        ;WITH LlamablesDia AS (
            SELECT Id, FechaAlta
            FROM Llamadores.Llamadores_Llamables
            WHERE IdTipoLlamable = 3
            AND FechaAlta >= CONVERT(date, GETDATE())
            AND FechaAlta < DATEADD(DAY, 1, CONVERT(date, GETDATE()))
        ),
        Solicitudes AS (
            SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
            FROM Llamadores.Llamadores_SolicitudesDeLlamado s
            INNER JOIN LlamablesDia ll ON ll.Id = s.Id_Llamable
            UNION ALL
            SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
            FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
            INNER JOIN LlamablesDia ll ON ll.Id = s.Id_Llamable
        ),
        Llamados AS (
            SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
            FROM Llamadores.Llamadores_Llamados l
            INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            UNION ALL
            SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
            FROM Llamadores.Llamadores_Llamados_Historico l
            INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
        ),
        LlamadosValidos AS (
            SELECT
                s.Id_Llamable,
                l.FechaAlta AS FechaLlamado,
                ROW_NUMBER() OVER (
                    PARTITION BY s.Id_Llamable
                    ORDER BY l.FechaAlta ASC
                ) AS rn
            FROM Solicitudes s
            INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
            WHERE s.IdEstadoActual = 5
            AND l.IdEstadoActual = 4
        ),
        Resultado AS (
            SELECT
                DATEPART(HOUR, ll.FechaAlta) AS Hora,
                CASE
                    WHEN DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado) < 0 THEN 30
                    ELSE DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado)
                END AS SegundosEspera
            FROM LlamablesDia ll
            INNER JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id AND lv.rn = 1
        )
        SELECT
            Hora,
            COUNT(*) AS Cantidad,
            CAST(AVG(CAST(SegundosEspera AS FLOAT)) / 60.0 AS DECIMAL(10, 2)) AS PromedioMinutos
        FROM Resultado
        GROUP BY Hora
        ORDER BY Hora;
    """
    try:
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        resultados = []
        for hora, cantidad, promedio_minutos in filas:
            promedio = float(promedio_minutos or 0)
            promedio_segundos = round(promedio * 60)
            resultados.append({
                "hora": int(hora),
                "hora_formateada": f"{int(hora):02d}:00",
                "cantidad": int(cantidad or 0),
                "promedio_minutos": round(promedio, 2),
                "promedio_formateado": formatear_segundos(promedio_segundos),
            })
        return JsonResponse({"success": True, "resultados": resultados})
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def estadisticas_resumen_ajax(request):
    try:
        fecha_desde, fecha_hasta = obtener_rango_fechas(request)
        consulta = """
            ;WITH LlamablesPeriodo AS (
                SELECT Id, FechaAlta
                FROM Llamadores.Llamadores_Llamables
                WHERE IdTipoLlamable = 3
                AND FechaAlta >= %s
                AND FechaAlta < DATEADD(DAY, 1, %s)
            ),
            Solicitudes AS (
                SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
                UNION ALL
                SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
            ),
            Llamados AS (
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
                UNION ALL
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados_Historico l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            ),
            LlamadosValidos AS (
                SELECT
                    s.Id_Llamable,
                    l.FechaAlta AS FechaLlamado,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.Id_Llamable
                        ORDER BY l.FechaAlta ASC
                    ) AS rn
                FROM Solicitudes s
                INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
                WHERE s.IdEstadoActual = 5
                AND l.IdEstadoActual = 4
            ),
            Resultado AS (
                SELECT
                    ll.Id,
                    lv.FechaLlamado,
                    CASE
                        WHEN lv.FechaLlamado IS NULL THEN NULL
                        WHEN DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado) < 0 THEN 30
                        ELSE DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado)
                    END AS SegundosEspera
                FROM LlamablesPeriodo ll
                LEFT JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id AND lv.rn = 1
            )
            SELECT
                COUNT(*) AS TotalIngresados,
                SUM(CASE WHEN FechaLlamado IS NOT NULL THEN 1 ELSE 0 END) AS TotalLlamados,
                AVG(CAST(SegundosEspera AS FLOAT)) AS PromedioSegundos,
                MAX(SegundosEspera) AS MaximoSegundos
            FROM Resultado;
        """
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta, [fecha_desde, fecha_hasta])
            fila = cursor.fetchone()
        total_ingresados = int(fila[0] or 0)
        total_llamados = int(fila[1] or 0)
        promedio_segundos = int(fila[2] or 0)
        maximo_segundos = int(fila[3] or 0)
        porcentaje_llamados = round(total_llamados * 100 / total_ingresados, 1) if total_ingresados else 0
        return JsonResponse({
            "success": True,
            "periodo": {"fecha_desde": fecha_desde.isoformat(), "fecha_hasta": fecha_hasta.isoformat()},
            "total_ingresados": total_ingresados,
            "total_llamados": total_llamados,
            "porcentaje_llamados": porcentaje_llamados,
            "promedio_segundos": promedio_segundos,
            "promedio_formateado": formatear_segundos(promedio_segundos),
            "maximo_segundos": maximo_segundos,
            "maximo_formateado": formatear_segundos(maximo_segundos),
        })
    except ValueError as error:
        return respuesta_error(error, 400)
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def estadisticas_frecuencia_por_letra_ajax(request):
    try:
        fecha_desde, fecha_hasta = obtener_rango_fechas(request)
        consulta = """
            ;WITH LlamablesPeriodo AS (
                SELECT Id, Sujeto, FechaAlta
                FROM Llamadores.Llamadores_Llamables
                WHERE IdTipoLlamable = 3
                AND FechaAlta >= %s
                AND FechaAlta < DATEADD(DAY, 1, %s)
                AND NULLIF(LTRIM(RTRIM(Sujeto)), '') IS NOT NULL
            ),
            Solicitudes AS (
                SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
                UNION ALL
                SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
            ),
            Llamados AS (
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
                UNION ALL
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados_Historico l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            ),
            LlamadosValidos AS (
                SELECT
                    s.Id_Llamable,
                    l.FechaAlta AS FechaLlamado,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.Id_Llamable
                        ORDER BY l.FechaAlta ASC
                    ) AS rn
                FROM Solicitudes s
                INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
                WHERE s.IdEstadoActual = 5
                AND l.IdEstadoActual = 4
            ),
            Resultado AS (
                SELECT
                    UPPER(LEFT(LTRIM(ll.Sujeto), 1)) AS Letra,
                    CASE
                        WHEN DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado) < 0 THEN 30
                        ELSE DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado)
                    END AS SegundosEspera
                FROM LlamablesPeriodo ll
                INNER JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id AND lv.rn = 1
            )
            SELECT Letra, COUNT(*) AS Cantidad, AVG(SegundosEspera) AS PromedioSegundos
            FROM Resultado
            GROUP BY Letra
            ORDER BY Letra;
        """
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta, [fecha_desde, fecha_hasta])
            filas = cursor.fetchall()
        resultados = []
        for letra, cantidad, promedio_segundos in filas:
            promedio_segundos = int(promedio_segundos or 0)
            resultados.append({
                "letra": letra,
                "cantidad": int(cantidad or 0),
                "promedio_segundos": promedio_segundos,
                "promedio_formateado": formatear_segundos(promedio_segundos),
            })
        return JsonResponse({"success": True, "resultados": resultados})
    except ValueError as error:
        return respuesta_error(error, 400)
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def estadisticas_promedio_por_letra_ajax(request):
    try:
        fecha_desde, fecha_hasta = obtener_rango_fechas(request)
        consulta = """
            ;WITH LlamablesPeriodo AS (
                SELECT Id, Sujeto, FechaAlta
                FROM Llamadores.Llamadores_Llamables
                WHERE IdTipoLlamable = 3
                AND FechaAlta >= %s
                AND FechaAlta < DATEADD(DAY, 1, %s)
                AND NULLIF(LTRIM(RTRIM(Sujeto)), '') IS NOT NULL
            ),
            Solicitudes AS (
                SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
                UNION ALL
                SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
            ),
            Llamados AS (
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
                UNION ALL
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados_Historico l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            ),
            LlamadosValidos AS (
                SELECT
                    s.Id_Llamable,
                    l.FechaAlta AS FechaLlamado,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.Id_Llamable
                        ORDER BY l.FechaAlta ASC
                    ) AS rn
                FROM Solicitudes s
                INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
                WHERE s.IdEstadoActual = 5
                AND l.IdEstadoActual = 4
            ),
            Resultado AS (
                SELECT
                    UPPER(LEFT(LTRIM(ll.Sujeto), 1)) AS Letra,
                    CASE
                        WHEN DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado) < 0 THEN 30
                        ELSE DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado)
                    END AS SegundosEspera
                FROM LlamablesPeriodo ll
                INNER JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id AND lv.rn = 1
            )
            SELECT Letra, COUNT(*) AS Cantidad, CAST(AVG(CAST(SegundosEspera AS FLOAT)) / 60.0 AS DECIMAL(10, 2)) AS PromedioMinutos
            FROM Resultado
            GROUP BY Letra
            ORDER BY Letra;
        """
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta, [fecha_desde, fecha_hasta])
            filas = cursor.fetchall()
        resultados = []
        for letra, cantidad, promedio_minutos in filas:
            promedio_minutos = float(promedio_minutos or 0)
            promedio_segundos = round(promedio_minutos * 60)
            resultados.append({
                "letra": letra,
                "cantidad": int(cantidad or 0),
                "promedio_minutos": round(promedio_minutos, 2),
                "promedio_segundos": promedio_segundos,
                "promedio_formateado": formatear_segundos(promedio_segundos),
            })
        return JsonResponse({"success": True, "resultados": resultados})
    except ValueError as error:
        return respuesta_error(error, 400)
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def estadisticas_atenciones_por_usuario_ajax(request):
    try:
        fecha_desde, fecha_hasta = obtener_rango_fechas(request)
        consulta = """
            SELECT
                CONCAT(
                    UPPER(LEFT(LEFT(LTRIM(p.Nombres), CHARINDEX(' ', LTRIM(p.Nombres) + ' ') - 1), 1)),
                    LOWER(SUBSTRING(LEFT(LTRIM(p.Nombres), CHARINDEX(' ', LTRIM(p.Nombres) + ' ') - 1), 2, 100)),
                    ' ',
                    UPPER(LEFT(LEFT(LTRIM(p.Apellido), CHARINDEX(' ', LTRIM(p.Apellido) + ' ') - 1), 1)),
                    LOWER(SUBSTRING(LEFT(LTRIM(p.Apellido), CHARINDEX(' ', LTRIM(p.Apellido) + ' ') - 1), 2, 100))
                ) AS Usuario,
                COUNT(*) AS Atenciones
            FROM Llamadores.Llamadores_Llamables ll
            INNER JOIN Usuarios u ON ll.IdUsuarioBaja = u.id
            INNER JOIN Personas p ON p.id = u.IdPersona
            WHERE ll.FechaBaja IS NOT NULL
            AND ll.IdTipoLlamable = 3
            AND ll.FechaAlta >= %s
            AND ll.FechaAlta < DATEADD(DAY, 1, %s)
            GROUP BY CONCAT(
                UPPER(LEFT(LEFT(LTRIM(p.Nombres), CHARINDEX(' ', LTRIM(p.Nombres) + ' ') - 1), 1)),
                LOWER(SUBSTRING(LEFT(LTRIM(p.Nombres), CHARINDEX(' ', LTRIM(p.Nombres) + ' ') - 1), 2, 100)),
                ' ',
                UPPER(LEFT(LEFT(LTRIM(p.Apellido), CHARINDEX(' ', LTRIM(p.Apellido) + ' ') - 1), 1)),
                LOWER(SUBSTRING(LEFT(LTRIM(p.Apellido), CHARINDEX(' ', LTRIM(p.Apellido) + ' ') - 1), 2, 100))
            )
            ORDER BY Atenciones DESC;
        """
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta, [fecha_desde, fecha_hasta])
            filas = cursor.fetchall()
        total_atenciones = sum(int(fila[1] or 0) for fila in filas)
        resultados = []
        for usuario, atenciones in filas:
            atenciones = int(atenciones or 0)
            porcentaje = round(atenciones * 100 / total_atenciones, 1) if total_atenciones else 0
            resultados.append({
                "usuario": usuario or "Sin identificar",
                "cantidad": atenciones,
                "porcentaje": porcentaje,
            })
        return JsonResponse({"success": True, "total_atenciones": total_atenciones, "resultados": resultados})
    except ValueError as error:
        return respuesta_error(error, 400)
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def estadisticas_evolucion_ajax(request):
    try:
        fecha_desde, fecha_hasta = obtener_rango_fechas(request)
        consulta = """
            ;WITH LlamablesPeriodo AS (
                SELECT Id, FechaAlta
                FROM Llamadores.Llamadores_Llamables
                WHERE IdTipoLlamable = 3
                AND FechaAlta >= %s
                AND FechaAlta < DATEADD(DAY, 1, %s)
            ),
            Solicitudes AS (
                SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
                UNION ALL
                SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
            ),
            Llamados AS (
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
                UNION ALL
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados_Historico l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            ),
            LlamadosValidos AS (
                SELECT
                    s.Id_Llamable,
                    l.FechaAlta AS FechaLlamado,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.Id_Llamable
                        ORDER BY l.FechaAlta ASC
                    ) AS rn
                FROM Solicitudes s
                INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
                WHERE s.IdEstadoActual = 5
                AND l.IdEstadoActual = 4
            ),
            Resultado AS (
                SELECT
                    CAST(ll.FechaAlta AS DATE) AS Fecha,
                    CASE
                        WHEN DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado) < 0 THEN 30
                        ELSE DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado)
                    END AS SegundosEspera
                FROM LlamablesPeriodo ll
                INNER JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id AND lv.rn = 1
            )
            SELECT
                Fecha,
                COUNT(*) AS Cantidad,
                CAST(AVG(CAST(SegundosEspera AS FLOAT)) / 60.0 AS DECIMAL(10, 2)) AS PromedioMinutos
            FROM Resultado
            GROUP BY Fecha
            ORDER BY Fecha;
        """
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta, [fecha_desde, fecha_hasta])
            filas = cursor.fetchall()
        resultados = []
        for fecha, cantidad, promedio_minutos in filas:
            promedio = float(promedio_minutos or 0)
            promedio_segundos = round(promedio * 60)
            resultados.append({
                "fecha": fecha.isoformat(),
                "fecha_formateada": fecha.strftime("%d/%m"),
                "cantidad": int(cantidad or 0),
                "promedio_minutos": round(promedio, 2),
                "promedio_formateado": formatear_segundos(promedio_segundos),
            })
        return JsonResponse({"success": True, "resultados": resultados})
    except ValueError as error:
        return respuesta_error(error, 400)
    except Exception as error:
        return respuesta_error(error)


@login_required
@require_GET
def estadisticas_detalle_diario_ajax(request):
    try:
        fecha_desde, fecha_hasta = obtener_rango_fechas(request)
        consulta = """
            ;WITH LlamablesPeriodo AS (
                SELECT Id, FechaAlta
                FROM Llamadores.Llamadores_Llamables
                WHERE IdTipoLlamable = 3
                AND FechaAlta >= %s
                AND FechaAlta < DATEADD(DAY, 1, %s)
            ),
            Solicitudes AS (
                SELECT s.Id AS IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
                UNION ALL
                SELECT s.IdSolicitud, s.Id_Llamable, s.IdEstadoActual
                FROM Llamadores.Llamadores_SolicitudesDeLlamado_Historico s
                INNER JOIN LlamablesPeriodo ll ON ll.Id = s.Id_Llamable
            ),
            Llamados AS (
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
                UNION ALL
                SELECT l.IdSolicitud, l.FechaAlta, l.IdEstadoActual
                FROM Llamadores.Llamadores_Llamados_Historico l
                INNER JOIN Solicitudes s ON s.IdSolicitud = l.IdSolicitud
            ),
            LlamadosValidos AS (
                SELECT
                    s.Id_Llamable,
                    l.FechaAlta AS FechaLlamado,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.Id_Llamable
                        ORDER BY l.FechaAlta ASC
                    ) AS rn
                FROM Solicitudes s
                INNER JOIN Llamados l ON l.IdSolicitud = s.IdSolicitud
                WHERE s.IdEstadoActual = 5
                AND l.IdEstadoActual = 4
            ),
            Resultado AS (
                SELECT
                    CAST(ll.FechaAlta AS DATE) AS Fecha,
                    CASE WHEN lv.FechaLlamado IS NOT NULL THEN 1 ELSE 0 END AS FueLlamado,
                    CASE
                        WHEN lv.FechaLlamado IS NULL THEN NULL
                        WHEN DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado) < 0 THEN 30
                        ELSE DATEDIFF(SECOND, ll.FechaAlta, lv.FechaLlamado)
                    END AS SegundosEspera
                FROM LlamablesPeriodo ll
                LEFT JOIN LlamadosValidos lv ON lv.Id_Llamable = ll.Id AND lv.rn = 1
            )
            SELECT
                Fecha,
                COUNT(*) AS Ingresados,
                SUM(FueLlamado) AS Llamados,
                AVG(CAST(SegundosEspera AS FLOAT)) AS PromedioSegundos,
                MAX(SegundosEspera) AS MaximoSegundos
            FROM Resultado
            GROUP BY Fecha
            ORDER BY Fecha;
        """
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta, [fecha_desde, fecha_hasta])
            filas = cursor.fetchall()
        resultados = []
        for fecha, ingresados, llamados, promedio_segundos, maximo_segundos in filas:
            ingresados = int(ingresados or 0)
            llamados = int(llamados or 0)
            promedio_segundos = int(promedio_segundos or 0)
            maximo_segundos = int(maximo_segundos or 0)
            porcentaje_llamados = round(llamados * 100 / ingresados, 1) if ingresados else 0
            resultados.append({
                "fecha": fecha.isoformat(),
                "fecha_formateada": fecha.strftime("%d/%m/%Y"),
                "ingresados": ingresados,
                "llamados": llamados,
                "porcentaje_llamados": porcentaje_llamados,
                "promedio_segundos": promedio_segundos,
                "promedio_formateado": formatear_segundos(promedio_segundos),
                "maximo_segundos": maximo_segundos,
                "maximo_formateado": formatear_segundos(maximo_segundos),
            })
        return JsonResponse({
            "success": True,
            "periodo": {"fecha_desde": fecha_desde.isoformat(), "fecha_hasta": fecha_hasta.isoformat()},
            "resultados": resultados,
        })
    except ValueError as error:
        return respuesta_error(error, 400)
    except Exception as error:
        return respuesta_error(error)



@login_required
@require_GET
def altas_medicas_pendientes_ajax(request):
    consulta = """
        SELECT
            e.Id AS Episodio,
            CONCAT(p.Apellido, ', ', p.Nombres) AS Paciente,
            e.FechaDeEgresoMedico,
            DATEDIFF(SECOND, e.FechaDeEgresoMedico, GETDATE()) AS EsperaSegundos
        FROM Internacion.Episodios e
        INNER JOIN Personas p ON p.Id = e.IdPersona
        WHERE e.FechaDeEgresoMedico >= DATEADD(DAY, -1, CAST(GETDATE() AS DATE))
        AND e.FechaDeEgresoMedico < DATEADD(DAY, 1, CAST(GETDATE() AS DATE))
        AND e.IdTipoEpisodio = 1
        AND e.FechaDeEgresoAdministrativo IS NULL
        ORDER BY e.FechaDeEgresoMedico ASC;
    """
    try:
        with connections["externa_readonly"].cursor() as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        resultados = []
        for episodio, paciente, fecha_egreso_medico, espera_segundos in filas:
            resultados.append({
                "episodio": int(episodio),
                "paciente": paciente or "Sin identificar",
                "fecha_egreso_medico": (
                    fecha_egreso_medico.isoformat()
                    if fecha_egreso_medico
                    else None
                ),
                "espera_segundos": int(espera_segundos or 0),
            })
        return JsonResponse({
            "success": True,
            "total": len(resultados),
            "resultados": resultados,
        })
    except Exception as error:
        return JsonResponse({
            "success": False,
            "error": str(error),
        }, status=500)
