from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.db import connections

@login_required
def dashboard_llamadores(request):
    """
    Renderiza el dashboard de llamadores.
    Los datos se cargan mediante AJAX desde llamadores_en_espera_ajax.
    """
    return render(request, "innova/llamadores/llamadores_totem.html")


@login_required
@require_GET
def llamadores_en_espera_ajax(request):
    """
    Devuelve los llamadores del día que todavía no tienen FechaBaja.
    """

    consulta = """
        SELECT
            ll.Sujeto,
            ll.FechaAlta,
            DATEDIFF(SECOND, ll.FechaAlta, GETDATE()) AS SegundosEspera
        FROM HCE.Llamadores.Llamadores_Llamables ll
        WHERE ll.IdTipoLlamable = 3
          AND ll.FechaAlta >= CONVERT(date, GETDATE())
          AND ll.FechaAlta < DATEADD(day, 1, CONVERT(date, GETDATE()))
          AND ll.FechaBaja IS NULL
        ORDER BY ll.FechaAlta ASC;
    """

    with connections['externa_readonly'].cursor()  as cursor:
        cursor.execute(consulta)
        filas = cursor.fetchall()

    llamadores = []

    for sujeto, fecha_alta, segundos_espera in filas:
        llamadores.append({
            "sujeto": str(sujeto),
            "fecha_alta": fecha_alta.isoformat() if fecha_alta else None,
            "segundos_espera": segundos_espera or 0,
        })

    return JsonResponse({
        "success": True,
        "total": len(llamadores),
        "llamadores": llamadores,
    })



@login_required
@require_GET
def frecuencia_llamadores_por_letra_ajax(request):
    consulta = """
        SELECT
            UPPER(LEFT(LTRIM(ll.Sujeto), 1)) AS Letra,
            COUNT(*) AS Cantidad,
            AVG(
                DATEDIFF(
                    SECOND,
                    ll.FechaAlta,
                    ll.FechaBaja
                )
            ) AS PromedioSegundos
        FROM Llamadores.Llamadores_Llamables ll
        WHERE ll.FechaBaja IS NOT NULL
          AND ll.IdTipoLlamable = 3
          AND ll.FechaAlta >= CONVERT(date, GETDATE())
          AND DATEDIFF(MINUTE, ll.FechaAlta, ll.FechaBaja) <= 60
          AND ll.FechaAlta < DATEADD(
                DAY,
                1,
                CONVERT(date, GETDATE())
          )
          AND NULLIF(LTRIM(RTRIM(ll.Sujeto)), '') IS NOT NULL
        GROUP BY UPPER(LEFT(LTRIM(ll.Sujeto), 1))
        ORDER BY Letra;
    """

    try:
        with connections['externa_readonly'].cursor()  as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()

        resultados = []

        for letra, cantidad, promedio_segundos in filas:
            promedio_segundos = promedio_segundos or 0

            resultados.append({
                "letra": letra,
                "cantidad": cantidad or 0,
                "promedio_segundos": promedio_segundos,
                "promedio_formateado": (
                    f"{promedio_segundos // 60} min "
                    f"{promedio_segundos % 60} seg"
                ),
            })

        return JsonResponse({
            "success": True,
            "resultados": resultados,
        })

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "error": str(error),
            },
            status=500,
        )
    

@login_required
@require_GET
def atenciones_por_usuario_ajax(request):
    consulta = """
        SELECT
            CONCAT(
                UPPER(
                    LEFT(
                        LEFT(
                            LTRIM(p.Nombres),
                            CHARINDEX(
                                ' ',
                                LTRIM(p.Nombres) + ' '
                            ) - 1
                        ),
                        1
                    )
                ),
                LOWER(
                    SUBSTRING(
                        LEFT(
                            LTRIM(p.Nombres),
                            CHARINDEX(
                                ' ',
                                LTRIM(p.Nombres) + ' '
                            ) - 1
                        ),
                        2,
                        100
                    )
                ),
                ' ',
                UPPER(
                    LEFT(
                        LEFT(
                            LTRIM(p.Apellido),
                            CHARINDEX(
                                ' ',
                                LTRIM(p.Apellido) + ' '
                            ) - 1
                        ),
                        1
                    )
                ),
                LOWER(
                    SUBSTRING(
                        LEFT(
                            LTRIM(p.Apellido),
                            CHARINDEX(
                                ' ',
                                LTRIM(p.Apellido) + ' '
                            ) - 1
                        ),
                        2,
                        100
                    )
                )
            ) AS Usuario,
            COUNT(*) AS Atenciones
        FROM llamadores.Llamadores_Llamables ll
        INNER JOIN Usuarios u
            ON ll.IdUsuarioBaja = u.id
        INNER JOIN Personas p
            ON p.id = u.IdPersona
        WHERE ll.FechaBaja IS NOT NULL
          AND ll.IdTipoLlamable = 3
          AND ll.FechaAlta >= CONVERT(date, GETDATE())
          AND ll.FechaAlta < DATEADD(
                DAY,
                1,
                CONVERT(date, GETDATE())
          )
        GROUP BY
            CONCAT(
                UPPER(
                    LEFT(
                        LEFT(
                            LTRIM(p.Nombres),
                            CHARINDEX(
                                ' ',
                                LTRIM(p.Nombres) + ' '
                            ) - 1
                        ),
                        1
                    )
                ),
                LOWER(
                    SUBSTRING(
                        LEFT(
                            LTRIM(p.Nombres),
                            CHARINDEX(
                                ' ',
                                LTRIM(p.Nombres) + ' '
                            ) - 1
                        ),
                        2,
                        100
                    )
                ),
                ' ',
                UPPER(
                    LEFT(
                        LEFT(
                            LTRIM(p.Apellido),
                            CHARINDEX(
                                ' ',
                                LTRIM(p.Apellido) + ' '
                            ) - 1
                        ),
                        1
                    )
                ),
                LOWER(
                    SUBSTRING(
                        LEFT(
                            LTRIM(p.Apellido),
                            CHARINDEX(
                                ' ',
                                LTRIM(p.Apellido) + ' '
                            ) - 1
                        ),
                        2,
                        100
                    )
                )
            )
        ORDER BY Atenciones DESC;
    """

    try:
        with connections['externa_readonly'].cursor()  as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()

        total_atenciones = sum(
            fila[1] or 0
            for fila in filas
        )

        resultados = []

        for usuario, atenciones in filas:
            atenciones = atenciones or 0

            porcentaje = (
                round(
                    atenciones * 100 / total_atenciones,
                    1,
                )
                if total_atenciones > 0
                else 0
            )

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
        return JsonResponse(
            {
                "success": False,
                "error": str(error),
            },
            status=500,
        )
    

@login_required
@require_GET
def evolucion_tiempo_promedio_ajax(request):
    consulta = """
        SELECT
            DATEPART(HOUR, ll.FechaAlta) AS Hora,
            COUNT(*) AS Cantidad,
            CAST(
                AVG(
                    CAST(
                        DATEDIFF(
                            SECOND,
                            ll.FechaAlta,
                            ll.FechaBaja
                        ) AS FLOAT
                    )
                ) / 60.0
                AS DECIMAL(10, 2)
            ) AS PromedioMinutos
        FROM Llamadores.Llamadores_Llamables ll
        WHERE ll.IdTipoLlamable = 3
          AND ll.FechaBaja IS NOT NULL
          AND ll.FechaAlta >= CONVERT(date, GETDATE())
          AND DATEDIFF(MINUTE, ll.FechaAlta, ll.FechaBaja) <= 60
          AND ll.FechaAlta < DATEADD(
                DAY,
                1,
                CONVERT(date, GETDATE())
          )
        GROUP BY DATEPART(HOUR, ll.FechaAlta)
        ORDER BY Hora;
    """

    try:
        with connections['externa_readonly'].cursor()  as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()

        resultados = []

        for hora, cantidad, promedio_minutos in filas:
            promedio = float(promedio_minutos or 0)

            minutos_enteros = int(promedio)
            segundos = round(
                (promedio - minutos_enteros) * 60
            )

            # Evita mostrar 4 min 60 seg.
            if segundos == 60:
                minutos_enteros += 1
                segundos = 0

            resultados.append({
                "hora": int(hora),
                "hora_formateada": f"{int(hora):02d}:00",
                "cantidad": int(cantidad or 0),
                "promedio_minutos": round(promedio, 2),
                "promedio_formateado": (
                    f"{minutos_enteros} min {segundos:02d} seg"
                ),
            })

        return JsonResponse({
            "success": True,
            "resultados": resultados,
        })

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "error": str(error),
            },
            status=500,
        )