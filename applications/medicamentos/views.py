from django.shortcuts import render
from django.db import connections
from datetime import date, datetime

def obtener_datos_sqlserver():
    with connections['externa_readonly'].cursor() as cursor:
        cursor.execute("""
            SELECT 
                CONCAT(p.Apellido, ', ', p.Nombres) AS Paciente,
                (SELECT m.NombreHabitual FROM dbo.mutuales m WHERE m.id = t.idmutual) AS 'Obra Social',
                (SELECT CONCAT(per.Apellido, ', ', per.Nombres)
                 FROM dbo.Profesionales prof
                 INNER JOIN dbo.personas per ON per.id = prof.idpersona
                 WHERE prof.id = r.IdExterna) AS Profesional,
                CAST(t.FechaTurno AS date) AS FechaTurno,
                t.HoraTurno,
                te.Nombre AS Estado,
                t.FechaOtorgado AS 'Fecha Emision'
            FROM dbo.turnos t
            INNER JOIN dbo.Personas p ON t.IdPersona = p.Id
            INNER JOIN dbo.Turno_Estados te ON te.Id = t.IdTurno_Estado
            LEFT JOIN dbo.Recursos r ON r.Id = t.IdRecurso
            LEFT JOIN dbo.Usuarios u ON u.Id = t.IdUsuario_Otorgo
            WHERE t.IdUsuario_Otorgo = 2
              AND CAST(t.fechaotorgado AS date) > '2025-07-08'
              AND t.IdTurno_Estado != 3
              AND t.IdPersona != 1720437
            ORDER BY t.FechaOtorgado DESC
        """)
        columnas = [col[0] for col in cursor.description]
        resultados_crudos = cursor.fetchall()
        datos = []
        for fila in resultados_crudos:
            fila_dict = dict(zip(columnas, fila))
            # Formatear cualquier campo tipo fecha
            for clave, valor in fila_dict.items():
                if isinstance(valor, (date, datetime)):
                    fila_dict[clave] = valor.strftime('%d/%m/%Y')
            datos.append(fila_dict)
        return datos

def medicamentos(request):
    datos = obtener_datos_sqlserver()
    return render(request, 'medicamentos/reporte.html', {'datos': datos})
