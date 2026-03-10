from django.shortcuts import render
from django.db import connections
from datetime import date, datetime
from applications.medicamentos.models import NomencladorIpsPromedi

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


 
import os 
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from io import BytesIO 
import pandas as pd
from django.shortcuts import render 
from django.contrib import messages
   
 

def procesar_excel(df):
    try:
        # Crear listas para almacenar resultados
        filas_fecha = []  # Lista para almacenar las filas con fechas válidas
        afiliado = None  # Para almacenar el paciente actual
        nro_episodio = None # Para almacenar el pago actual para
        # Recorrer las filas del DataFrame
        for _, row in df.iterrows():
            # Verificar que la fila no esté vacía y que el contenido esté en la primera columna
            if pd.isna(row[0]): 
                continue  # Saltar filas vacías

            contenido = str(row[0])  # Leer la primera columna como texto

            if contenido.startswith("Paciente:"):
                # Si es un paciente, guardar su nombre en la variable 'afiliado' sin el prefijo "Paciente:" y sin espacios
                afiliado = contenido.replace("Paciente:", "").strip()  # Eliminar "Paciente:" y quitar espacios
                nro_afiliado = row[1].replace("Nro.Afiliado:","").strip() # Eliminar
                nro_episodio = row[5].replace("Nro.Episodio:", "").strip() # Eliminar
                if nro_afiliado == "":
                    nro_afiliado = "34"
            else:
                # Intentar convertir el valor a fecha de manera flexible
                try:
                    fecha = pd.to_datetime(contenido, errors='coerce')
                    if pd.notna(fecha):  # Solo agregar si es una fecha válida
                        # Formatear la fecha al formato requerido 'dd/mm/yyyy HH:MM:SS'
                        fecha_formateada = fecha.strftime('%d/%m/%Y')

                        # Crear una copia de la fila y agregarle el valor de 'afiliado' y la fecha formateada
                        row = row.tolist()  # Convertir la fila a lista
                        row[0] = fecha_formateada  # Reemplazar la fecha original por la fecha formateada
                        row.append(afiliado)  # Añadir el paciente a la fila
                        row.append(nro_afiliado)
                        row.append(nro_episodio)
                        filas_fecha.append(row)  # Añadir la fila procesada con el afiliado
                except Exception:
                    # Si no es una fecha válida, no hacer nada
                    continue

        # Verificar que tengamos filas procesadas
        if not filas_fecha:
            raise ValueError("No se encontraron filas con fechas válidas.")

        # Crear un nuevo DataFrame con las filas procesadas
        df_fechas = pd.DataFrame(filas_fecha)

        # Seleccionar las columnas necesarias (A, B, C, E, F, I, J, M)
        columnas_conservadas = [0, 1, 2, 4, 5, 8, 9,10,11,12, 25,26,27,3]
        df_fechas = df_fechas.iloc[:, columnas_conservadas]

        # Ahora añadimos la columna "Afiliado" correctamente
        # Ahora deberíamos tener 9 columnas, así que renombramos los encabezados
        df_fechas.columns = ['Fecha', 'Codigo', 'Descripcion', 'Cantidad', 'FD', 'Gastos', 'Honorarios','HonoAnes','HonoAyud', 'Total', 'Afiliado','Numero','Episodio','Medico']

        # Crear un archivo de salida en memoria
        output = BytesIO()

        # Usar openpyxl como motor para crear el archivo
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_fechas.to_excel(writer, index=False, sheet_name="Fechas")

        # Regresar el archivo en formato binario para la descarga
        output.seek(0)
        return output

    except Exception as e:
        raise Exception(f"Error al procesar el archivo Excel: {str(e)}")


# Función de vista para subir el archivo
def upload_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('file')

        if not excel_file:
            messages.error(request, "Por favor, sube un archivo Excel.")
            return render(request, 'medicamentos/upload_excel.html')

        fs = FileSystemStorage()
        filename = fs.save(excel_file.name, excel_file)
        file_path = fs.path(filename)
        tipo_excel = request.POST.get('select-paso')

        try:
            # Leer el archivo Excel con pandas
            df = pd.read_excel(file_path)

            # Llamar a la función de procesamiento
            if tipo_excel:
                if tipo_excel =='preanexo':
                    excel_output = procesar_excel(df)
                    # Devolver el archivo como respuesta
                    response = HttpResponse(
                        excel_output, 
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename="preanexo-ips.xlsx"'
                if tipo_excel == 'medicamentos-osuthgra':
                    excel_output = process_excel_osuthgra(df)
                    # Devolver el archivo como respuesta
                    response = HttpResponse(
                        excel_output,
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename="medicamentos-osuthgra.xlsx"'

                if tipo_excel =='anexo-ambulatorio':
                    excel_output = process_excel_ips_ambulatorio(df)
                    # Devolver el archivo como respuesta
                    response = HttpResponse(
                        excel_output,
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename="anexo-ips-ambulatorio.xlsx"'
                if tipo_excel =='anexo-internado':
                    excel_output = process_excel_ips_internado(df)
                    # Devolver el archivo como respuesta
                    response = HttpResponse(
                        excel_output,
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename="anexo-ips-internado.xlsx"'
                if tipo_excel =='anexo-internado-momentaneo':
                    excel_output = process_excel_ips_internado_momentaneo(df)
                    # Devolver el archivo como respuesta
                    response = HttpResponse(
                        excel_output,
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename="anexo-ips-internado.xlsx"'
            else:
                messages.error(request, "Por favor, selecciona un tipo de excel.")
                return render(request, 'medicamentos/upload_excel.html')
            return response

        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {str(e)}")
            return render(request, 'medicamentos/upload_excel.html')
    return render(request, 'medicamentos/upload_excel.html')


from django.templatetags.static import static



def normalizar_codigo(codigo: str) -> int:
    if not codigo:
        return 0

    codigo = codigo.strip().upper()

    # Si empieza con DES → descartar
    if codigo.startswith("DES"):
        return 0

    # Si tiene X, tomar lo anterior
    if "X" in codigo:
        codigo = codigo.split("X")[0]

    # Convertir a int si es numérico
    return int(codigo) if codigo.isdigit() else 0

from datetime import date

MESES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

hoy = date.today()

# calcular mes anterior
if hoy.month == 1:
    mes = 12
    anio = hoy.year - 1
else:
    mes = hoy.month - 1
    anio = hoy.year

mes_anio_texto = f"{MESES[mes - 1]} {anio}"


def process_excel_osuthgra(df):
     # Crear un buffer para el archivo en memoria
    output = BytesIO()
    
    # Crear el escritor Excel usando xlsxwriter
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Facturación internado')

    # Formatos
    bold_format = workbook.add_format({'bold': True})
    header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#D9D9D9'})
    border_format = workbook.add_format({'border': 1}) 
    money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    total_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'border': 1, 'bg_color': '#FFFFCC'})
    title_format = workbook.add_format({'bold': True, 'font_size': 14})
    general_total_label_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'right'})
    subtotal_label_format = workbook.add_format({'bold': True, 'align': 'right'}) 

    # Cargar logo desde la carpeta estática
    logo_path = static('fotos/logo-santa-clara.png')  # Ajusta el path según tu estructura de archivos
    logo_full_path = os.path.join(os.getcwd(), logo_path.lstrip('/'))  # Convertir a ruta absoluta

    # Insertar logo en las primeras filas
    try:
        worksheet.insert_image('A1', logo_full_path, {'x_scale': 1, 'y_scale': 1.3, 'x_offset': 10, 'y_offset': 10})
    except FileNotFoundError:
        worksheet.write('A1', 'Logo no encontrado', bold_format)

    # Escribir descripción del hospital 
    worksheet.write('C2', 'HOSPITAL PRIVADO SANTA CLARA DE ASIS', title_format)
    worksheet.write('C3', 'Obra Social: OSUTHGRA', title_format)
    worksheet.write('C4', f'Facturación Internado Medicamentos {mes_anio_texto}', title_format)

    row = 6  # Fila inicial después del encabezado principal

    # Variables para los totales generales

    # Definir los grupos de códigos
    # Grupos de códigos como enteros 
    # Filtrar los registros donde 'Codigo' contiene letras
    df = df[df['Codigo'].astype(str).str.contains(r'[A-Za-z]', na=False)]
    df['Numero'] = df['Numero'].astype(str)

    # Ahora puedes usar 'df_medicamentos' para realizar cualquier operación adicional
    total_general_gastos = df['Gastos'].sum() 

    grupos = df.groupby(['Afiliado', 'Episodio'])
 
    # Iterar sobre cada grupo
    for (paciente, episodio), data_paciente in grupos: 
        # Filtrar datos del paciente
        data_paciente = df[(df['Afiliado'] == paciente) & (df['Episodio'] == episodio)]

        # Escribir encabezado del paciente
        worksheet.write(row, 0, 'Afiliado:', bold_format)
        worksheet.write(row, 1, paciente, bold_format)
        row += 1

        # Escribir número de afiliado
        numero_afiliado = data_paciente['Numero'].iloc[0]
        worksheet.write(row, 0, 'Nro. Afiliado:', bold_format)
        worksheet.write(row, 1, numero_afiliado, bold_format)
        row += 1

        # Encabezado de las columnas
        columnas = ['Código','Descripcion', 'Cant.', 'Precio U', 'Desc.(%)','Descuento', 'Con descuento', 'Subtotal']
        for col_num, columna in enumerate(columnas):
            worksheet.write(row, col_num, columna, header_format)

        row += 1

        # Inicializar el subtotal para el paciente
        subtotal_paciente = 0 

        # Escribir datos del paciente
        for _, fila in data_paciente.iterrows(): 

            worksheet.write(row, 1, fila['Descripcion'], border_format)
            worksheet.write(row, 0, fila['Codigo'], border_format)
            worksheet.write(row, 2, fila['Cantidad'], border_format)
            print("El codigo es : ", fila['Codigo'])
            print("El codigo formateado es:", normalizar_codigo(fila['Codigo']))
            codigo_normalizado = normalizar_codigo(fila['Codigo'])
            porcentaje = ListadoOsuthgra.obtener_porcentaje_por_codigo(codigo_normalizado)
            subtotal = fila['Total']
            cantidad = fila['Cantidad']
            print("Porcentaje:",porcentaje)
            subtotal_sin_descuento = subtotal/(1-porcentaje)
            valor_unitario= subtotal_sin_descuento/cantidad
            valor_unitario_descuento = valor_unitario * 0.9
            worksheet.write(row, 3, valor_unitario, money_format)
            worksheet.write(row, 4, porcentaje*100, border_format)  # Recargo modificado (faltante a 100)
            worksheet.write(row, 5, valor_unitario * porcentaje, money_format)
            worksheet.write(row, 6,valor_unitario*(1-porcentaje), money_format)
            worksheet.write(row, 7, subtotal, money_format)  # Valor Promedio calculado

            # Actualizar el subtotal y valor promedio del paciente
            subtotal_paciente += fila['Total'] 

            row += 1

        # Escribir el subtotal del paciente y el valor promedio
        worksheet.write(row, 6, 'Total paciente:', subtotal_label_format)
        worksheet.write(row, 7, subtotal_paciente, total_format) 
        row += 2  # Separación entre pacientes 

    # Escribir totales generales
    worksheet.write(row, 6, 'TOTAL GENERAL:', general_total_label_format)
    worksheet.write(row, 7, total_general_gastos, total_format) 

    # Ajustar ancho de las columnas
    worksheet.set_column('A:A', 9)  # Codigo
    worksheet.set_column('B:B', 33)  # Descripcion
    worksheet.set_column('C:C', 7)  # Cantidad
    worksheet.set_column('D:D', 14)  # Gastos
    worksheet.set_column('E:E', 9)  # Recargo
    worksheet.set_column('F:H', 15)  # Montos

    # Guardar archivo en el buffer
    writer.close()
    output.seek(0)

    return output


def process_excel_ips_internado(df):
    # Crear un buffer para el archivo en memoria
    output = BytesIO()
    
    # Crear el escritor Excel usando xlsxwriter
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Facturación internado')

    # Formatos
    bold_format = workbook.add_format({'bold': True})
    header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#D9D9D9'})
    border_format = workbook.add_format({'border': 1})
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
    money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    total_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'border': 1, 'bg_color': '#FFFFCC'})
    title_format = workbook.add_format({'bold': True, 'font_size': 14})
    general_total_label_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'right'})
    subtotal_label_format = workbook.add_format({'bold': True, 'align': 'right'})
    description_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center'})

    # Cargar logo desde la carpeta estática
    logo_path = static('fotos/logo-santa-clara.jpg')  # Ajusta el path según tu estructura de archivos
    logo_full_path = os.path.join(os.getcwd(), logo_path.lstrip('/'))  # Convertir a ruta absoluta

    # Insertar logo en las primeras filas
    try:
        worksheet.insert_image('A1', logo_full_path, {'x_scale': 1, 'y_scale': 1.3, 'x_offset': 10, 'y_offset': 10})
    except FileNotFoundError:
        worksheet.write('A1', 'Logo no encontrado', bold_format)

    # Escribir descripción del hospital 
    worksheet.write('D2', 'HOSPITAL PRIVADO SANTA CLARA DE ASIS', title_format)
    worksheet.write('D3', 'Obra Social: Instituto Provincial de Salud', title_format)
    worksheet.write('D4', 'Facturacion Internado Noviembre 2024', title_format)

    row = 6  # Fila inicial después del encabezado principal

    # Variables para los totales generales
    total_general_gastos = 0
    total_general_honorarios = 0
    total_general_valor_promedio = 0

    # Definir los grupos de códigos
    # Grupos de códigos como enteros
    df['Codigo'] = df['Codigo'].astype(int) 
    grupos = df.groupby(['Afiliado', 'Episodio'])

    # Iterar sobre cada grupo
    for (paciente, episodio), data_paciente in grupos: 
        # Filtrar datos del paciente
        data_paciente = df[(df['Afiliado'] == paciente) & (df['Episodio'] == episodio)]

        # Escribir encabezado del paciente
        worksheet.write(row, 0, 'Afiliado:', bold_format)
        worksheet.write(row, 1, paciente, bold_format)
        row += 1

        # Escribir número de afiliado
        numero_afiliado = data_paciente['Numero'].iloc[0]
        worksheet.write(row, 0, 'Nro. Afiliado:', bold_format)
        worksheet.write(row, 1, numero_afiliado, bold_format)
        row += 1

        # Encabezado de las columnas
        columnas = ['Fecha', 'Código', 'Cantidad', 'Gastos', 'Recargo (%)','Honorarios', 'Subtotal', 'VALOR PROMEDI']
        for col_num, columna in enumerate(columnas):
            worksheet.write(row, col_num, columna, header_format)

        row += 1

        # Inicializar el subtotal para el paciente
        subtotal_paciente = 0
        valor_promedio_paciente = 0
        total_gastos_paciente = 0 
        total_honorarios_paciente = 0
        for _, fila in data_paciente.iterrows():
            # Calcular el faltante a 100 para la columna 'FD'
            codigo = int(fila['Codigo'])
            if float(fila['Gastos'])>0:
                modified_fd = -100 + fila['FD']  
                # Asignar valor a 'VALOR PROMEDI' según el código
            # Escribir la fila con el valor de 'FD' modificado y 'VALOR PROMEDI'  
                gastos = float(fila['Gastos'])
                if codigo == 400101:
                    honorarios = float(fila['Honorarios'])
                else:
                    honorarios=0
                total = gastos+honorarios
                valor_promedio = total * (NomencladorIpsPromedi.obtener_porcentaje_por_codigo(fila['Codigo'])/100)
 
                worksheet.write(row, 0, fila['Fecha'], date_format)
                worksheet.write(row, 1, fila['Codigo'], border_format)
                worksheet.write(row, 2, fila['Cantidad'], border_format)
                worksheet.write(row, 3, fila['Gastos'], money_format)
                worksheet.write(row, 4, modified_fd, border_format)  # Recargo modificado (faltante a 100)
                worksheet.write(row, 5, honorarios, money_format)
                worksheet.write(row, 6, total, money_format)
                worksheet.write(row, 7, valor_promedio, money_format)  # Valor Promedio calculado

                # Actualizar el subtotal y valor promedio del paciente
                subtotal_paciente += total
                valor_promedio_paciente += valor_promedio
                
                total_gastos_paciente += gastos
                total_honorarios_paciente += honorarios

                row += 1

        # Escribir el subtotal del paciente y el valor promedio
        worksheet.write(row, 5, 'Total paciente:', subtotal_label_format)
        worksheet.write(row, 6, subtotal_paciente, total_format)
        worksheet.write(row, 7, valor_promedio_paciente, total_format)
        row += 2  # Separación entre pacientes
        total_general_valor_promedio += valor_promedio_paciente
        total_general_gastos += total_gastos_paciente
        total_general_honorarios += total_honorarios_paciente

    # Escribir totales generales
    worksheet.write(row, 6, 'TOTAL GASTOS:', general_total_label_format)
    worksheet.write(row, 7, total_general_gastos, total_format)
    row += 1

    worksheet.write(row, 6, 'TOTAL HONORARIOS:', general_total_label_format)
    worksheet.write(row, 7, total_general_honorarios, total_format)
    row += 1 

    worksheet.write(row, 6, 'TOTAL VALOR PROMEDI:', general_total_label_format)
    worksheet.write(row, 7, total_general_valor_promedio, total_format)
    
    row += 1   
    worksheet.write(row, 6, 'TOTAL GENERAL:', general_total_label_format)
    worksheet.write(row, 7, total_general_valor_promedio+total_general_gastos+total_general_honorarios, total_format)

    # Ajustar ancho de las columnas
    worksheet.set_column('A:A', 15)  # Fecha
    worksheet.set_column('B:B', 10)  # Código
    worksheet.set_column('C:C', 10)  # Cantidad
    worksheet.set_column('D:D', 15)  # Gastos
    worksheet.set_column('E:E', 10)  # Recargo
    worksheet.set_column('F:H', 15)  # Montos

    # Guardar archivo en el buffer
    writer.close()
    output.seek(0)

    return output




def process_excel_ips_internado_momentaneo(df):
    # Crear un buffer para el archivo en memoria
    output = BytesIO()
    
    # Crear el escritor Excel usando xlsxwriter
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Facturación internado')

    # Formatos
    bold_format = workbook.add_format({'bold': True})
    header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#D9D9D9'})
    border_format = workbook.add_format({'border': 1})
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
    money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    total_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'border': 1, 'bg_color': '#FFFFCC'})
    title_format = workbook.add_format({'bold': True, 'font_size': 14})
    general_total_label_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'right'})
    subtotal_label_format = workbook.add_format({'bold': True, 'align': 'right'})
    description_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center'})

    # Cargar logo desde la carpeta estática
    logo_path = static('fotos/logo-santa-clara.jpg')  # Ajusta el path según tu estructura de archivos
    logo_full_path = os.path.join(os.getcwd(), logo_path.lstrip('/'))  # Convertir a ruta absoluta

    # Insertar logo en las primeras filas
    try:
        worksheet.insert_image('A1', logo_full_path, {'x_scale': 1, 'y_scale': 1.3, 'x_offset': 10, 'y_offset': 10})
    except FileNotFoundError:
        worksheet.write('A1', 'Logo no encontrado', bold_format)

    # Escribir descripción del hospital 
    worksheet.write('D2', 'HOSPITAL PRIVADO SANTA CLARA DE ASIS', title_format)
    worksheet.write('D3', 'Obra Social: Instituto Provincial de Salud', title_format)
    worksheet.write('D4', 'Facturacion Internado Noviembre 2024', title_format)

    row = 6  # Fila inicial después del encabezado principal

    # Variables para los totales generales
    total_general_gastos = 0
    total_general_honorarios = 0 
    total_general_valor_promedio = 0

    # Definir los grupos de códigos
    # Grupos de códigos como enteros
    df['Codigo'] = df['Codigo'].astype(int) 
    grupos = df.groupby(['Afiliado', 'Episodio'])

    # Iterar sobre cada grupo
    for (paciente, episodio), data_paciente in grupos: 
        # Filtrar datos del paciente
        row_inicio = row
        data_paciente = df[(df['Afiliado'] == paciente) & (df['Episodio'] == episodio)]

        # Escribir encabezado del paciente
        worksheet.write(row, 0, 'Afiliado:', bold_format)
        worksheet.write(row, 1, paciente, bold_format)
        row += 1

        # Escribir número de afiliado
        numero_afiliado = data_paciente['Numero'].iloc[0]
        worksheet.write(row, 0, 'Nro. Afiliado:', bold_format)
        worksheet.write(row, 1, numero_afiliado, bold_format)
        row += 1

        # Encabezado de las columnas
        columnas = ['Fecha', 'Código', 'Cantidad', 'Gastos','Honorarios','H.Ayudantes', 'Total']
        for col_num, columna in enumerate(columnas):
            worksheet.write(row, col_num, columna, header_format)

        row += 1

        # Inicializar el subtotal para el paciente
        subtotal_paciente = 0 
        total_honorario_paciente = 0
        total_gastos_paciente = 0
        for _, fila in data_paciente.iterrows():
            # Calcular el faltante a 100 para la columna 'FD'
            codigo = int(fila['Codigo'])
            if codigo != 400101:
                if codigo in (170101,240000,200222,240133,240144,340907):
                    gastos = float(fila['Gastos'])
                else: 
                    gastos = 0
                if float(fila['Honorarios'])>0 or float(fila['HonoAyud'])>0 or codigo in (170101,240000,200222,240133,240144,340907): 
                    worksheet.write(row, 0, fila['Fecha'], date_format)
                    worksheet.write(row, 1, fila['Codigo'], border_format)
                    worksheet.write(row, 2, fila['Cantidad'], border_format)
                    worksheet.write(row, 3, gastos, money_format)
                    worksheet.write(row, 4, fila['Honorarios'], money_format)
                    worksheet.write(row, 5, fila['HonoAyud'], money_format) 
                    total = gastos+ float(fila['Honorarios']) + float(fila['HonoAyud'])
                    worksheet.write(row, 6, total, money_format) 
                    # Actualizar el subtotal y valor promedio del paciente
                    total_gastos_paciente += gastos
                    total_honorario_paciente += float(fila['Honorarios']) + float(fila['HonoAyud']) 
                    subtotal_paciente += total
                    row += 1
        
            # ============================
        # 🔥 SI EL TOTAL ES 0 → BORRAR
        # ============================
        if subtotal_paciente == 0:
            # Limpia visualmente las filas escritas
            for r in range(row_inicio, row):
                worksheet.write(r, 0, "")
                worksheet.write(r, 1, "")
                worksheet.write(r, 2, "")
                worksheet.write(r, 3, "")
                worksheet.write(r, 4, "")
                worksheet.write(r, 5, "")
                worksheet.write(r, 6, "")

            # Retroceder row al inicio del paciente
            row = row_inicio
            continue  # ← Pasar al siguiente paciente
        else:        
            # Escribir el subtotal del paciente y el valor promedio
            worksheet.write(row, 5, 'Total paciente:', subtotal_label_format)
            worksheet.write(row, 6, subtotal_paciente, total_format) 
            row += 2  # Separación entre pacientes
            total_general_honorarios+=total_honorario_paciente
            total_general_gastos+= total_gastos_paciente

    # Escribir totales generales
    worksheet.write(row, 6, 'TOTAL GASTOS:', general_total_label_format)
    worksheet.write(row, 7, total_general_gastos, total_format)
    row += 1

    worksheet.write(row, 6, 'TOTAL HONORARIOS:', general_total_label_format)
    worksheet.write(row, 7, total_general_honorarios, total_format)
    row += 1 
 
    worksheet.write(row, 6, 'TOTAL GENERAL:', general_total_label_format)
    worksheet.write(row, 7, total_general_gastos+total_general_honorarios, total_format)

    # Ajustar ancho de las columnas
    worksheet.set_column('A:A', 15)  # Fecha
    worksheet.set_column('B:B', 10)  # Código
    worksheet.set_column('C:C', 10)  # Cantidad
    worksheet.set_column('D:D', 15)  # Gastos
    worksheet.set_column('E:E', 10)  # Recargo
    worksheet.set_column('F:H', 15)  # Montos

    # Guardar archivo en el buffer
    writer.close()
    output.seek(0)

    return output





def process_excel_ips_ambulatorio(df):
    # Crear un buffer para el archivo en memoria
    output = BytesIO()
    
    # Crear el escritor Excel usando xlsxwriter
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Facturación ambulatorio')

    # Formatos
    bold_format = workbook.add_format({'bold': True})
    header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#D9D9D9'})
    border_format = workbook.add_format({'border': 1})
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
    money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    total_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'border': 1, 'bg_color': '#FFFFCC'})
    title_format = workbook.add_format({'bold': True, 'font_size': 14})
    general_total_label_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'right'})
    subtotal_label_format = workbook.add_format({'bold': True, 'align': 'right'})
    description_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center'})

    # Cargar logo desde la carpeta estática
    logo_path = static('images/logo-santa-clara.png')  # Ajusta el path según tu estructura de archivos
    logo_full_path = os.path.join(os.getcwd(), logo_path.lstrip('/'))  # Convertir a ruta absoluta

    # Insertar logo en las primeras filas
    try:
        worksheet.insert_image('A1', logo_full_path, {'x_scale': 1, 'y_scale': 1.3, 'x_offset': 10, 'y_offset': 10})
    except FileNotFoundError:
        worksheet.write('A1', 'Logo no encontrado', bold_format)

    # Escribir descripción del hospital 
    worksheet.write('D2', 'HOSPITAL PRIVADO SANTA CLARA DE ASIS', title_format)
    worksheet.write('D3', 'Obra Social: Instituto Provincial de Salud', title_format)
    worksheet.write('D4', 'Facturacion Ambulatoria Noviembre 2024', title_format)

    row = 6  # Fila inicial después del encabezado principal

    # Variables para los totales generales
    total_general_gastos = df['Gastos'].sum()
    total_general_honorarios = df['Honorarios'].sum()
    total_general_valor_promedio = 0

    # Definir los grupos de códigos
    # Grupos de códigos como enteros 
    # ordenamos por nombre de afiliado
    df = df.sort_values(by='Afiliado')
    # Iterar por paciente
    for paciente in df['Afiliado'].unique():
        # Filtrar datos del paciente
        data_paciente = df[df['Afiliado'] == paciente]

        # Escribir encabezado del paciente
        worksheet.write(row, 0, 'Afiliado:', bold_format)
        worksheet.write(row, 1, paciente, bold_format)
        row += 1

        # Escribir número de afiliado
        numero_afiliado = data_paciente['Numero'].iloc[0]
        worksheet.write(row, 0, 'Nro. Afiliado:', bold_format)
        worksheet.write(row, 1, numero_afiliado, bold_format)
        row += 1

        # Encabezado de las columnas
        columnas = ['Fecha', 'Código', 'Cantidad', 'Gastos', 'Recargo (%)','Honorarios', 'Subtotal']
        for col_num, columna in enumerate(columnas):
            worksheet.write(row, col_num, columna, header_format)

        row += 1

        # Inicializar el subtotal para el paciente
        subtotal_paciente = 0 

        # Escribir datos del paciente
        for _, fila in data_paciente.iterrows():
            # Calcular el faltante a 100 para la columna 'FD'
            modified_fd = -100 + fila['FD']   

            worksheet.write(row, 0, fila['Fecha'], date_format)
            worksheet.write(row, 1, fila['Codigo'], border_format)
            worksheet.write(row, 2, fila['Cantidad'], border_format)
            worksheet.write(row, 3, fila['Gastos'], money_format)
            worksheet.write(row, 4, modified_fd, border_format)  # Recargo modificado (faltante a 100)
            worksheet.write(row, 5, fila['Honorarios'], money_format)
            worksheet.write(row, 6, fila['Total'], money_format) 

            # Actualizar el subtotal y valor promedio del paciente
            subtotal_paciente += fila['Total'] 
            row += 1

        # Escribir el subtotal del paciente y el valor promedio
        worksheet.write(row, 5, 'Total paciente:', subtotal_label_format)
        worksheet.write(row, 6, subtotal_paciente, total_format) 
        row += 2  # Separación entre pacientes 

    # Escribir totales generales
    worksheet.write(row, 5, 'TOTAL GASTOS:', general_total_label_format)
    worksheet.write(row, 6, total_general_gastos, total_format)
    row += 1

    worksheet.write(row, 5, 'TOTAL HONORARIOS:', general_total_label_format)
    worksheet.write(row, 6, total_general_honorarios, total_format)
    row += 1 
  
    worksheet.write(row, 5, 'TOTAL GENERAL:', general_total_label_format)
    worksheet.write(row, 6,total_general_gastos+total_general_honorarios, total_format)

    # Ajustar ancho de las columnas
    worksheet.set_column('A:A', 12)  # Fecha
    worksheet.set_column('B:B', 10)  # Código
    worksheet.set_column('C:C', 10)  # Cantidad
    worksheet.set_column('D:D', 15)  # Gastos
    worksheet.set_column('E:E', 10)  # Recargo
    worksheet.set_column('F:G', 15)  # Montos

    # Guardar archivo en el buffer
    writer.close()
    output.seek(0)

    return output


 





from django.contrib import messages
from django.core.files.storage import FileSystemStorage
 
def process_excel_ips(df):
    # Crear una carpeta para guardar los archivos de salida
    output_dir = 'output_excels'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Crear el archivo Excel único para todos los pacientes
    file_path = os.path.join(output_dir, 'todos_pacientes.xlsx')

    # Usar `pandas` con `xlsxwriter` para crear un archivo Excel
    writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
    workbook  = writer.book
    worksheet = workbook.add_worksheet('Resumen Medicamentos')

    # Formatos para el archivo Excel
    bold_format = workbook.add_format({'bold': True})  # Negrita
    border_format = workbook.add_format({'border': 1})  # Borde alrededor de la tabla
    header_format = workbook.add_format({'bold': True, 'border': 1})  # Negrita y borde para el encabezado
    title_format = workbook.add_format({'bold': True, 'font_size': 14})  # Negrita y tamaño de fuente 14 para el título

    # Inicializar fila inicial y total general
    start_row = 0
    total_general = 0

    # Iterar sobre cada grupo de pacientes
    for paciente in df['Paciente'].unique():
        # Filtrar los datos por el paciente actual
        data_paciente = df[df['Paciente'] == paciente]

        # Calcular el subtotal por medicamento y el total financiador por paciente
        data_paciente['Subtotal'] = data_paciente['Cantidad'] * data_paciente['Precio']
        total_financiador = data_paciente['Subtotal'].sum()

        # Agregar al total general
        total_general += total_financiador

        # Encabezado personalizado por paciente
        worksheet.write(start_row, 0, 'Paciente:', bold_format)
        worksheet.write(start_row, 1, paciente)

        
        # Encabezado de la tabla
        headers = ['Codigo', 'Descripcion','Cantidad', 'Precio U', 'Subtotal']
        for col_num, header in enumerate(headers):
            worksheet.write(start_row + 2, col_num, header, header_format)

        # Escribir los datos del paciente
        for row_num, row_data in enumerate(data_paciente[['Codigo','Descripcion','Cantidad', 'Precio', 'Subtotal']].values, start=start_row + 3):
            for col_num, value in enumerate(row_data):
                worksheet.write(row_num, col_num, value, border_format)

        for col_num, col in enumerate(['Codigo', 'Descripcion','Cantidad', 'Precio', 'Subtotal']):
            max_len = max(data_paciente[col].astype(str).map(len).max(), len(col)) + 2  # Encontrar la longitud máxima
            worksheet.set_column(col_num, col_num, max_len)  # Ajustar el ancho de la columna


        # Escribir el total financiador para el paciente
        total_row = row_num + 1
        worksheet.write(total_row, 3, 'Total:', bold_format)
        worksheet.write(total_row, 4, total_financiador, bold_format)

        # Ajustar la fila inicial para el próximo paciente (dejando una fila en blanco)
        start_row = total_row + 3

    # Escribir el total general en la última fila
    worksheet.write(start_row, 2, 'Total General:', bold_format)
    worksheet.write(start_row, 3, total_general, bold_format)

    # Guardar y cerrar el archivo Excel
    writer.close()

    return "Archivo Excel generado exitosamente con todos los pacientes y total general."

 
import os
import pandas as pd

def process_excel(df):
    # Crear una carpeta para guardar los archivos de salida
    output_dir = 'output_excels'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Crear el archivo Excel único para todos los pacientes
    file_path = os.path.join(output_dir, 'todos_pacientes.xlsx')

    # Usar `pandas` con `xlsxwriter` para crear un archivo Excel
    writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
    workbook  = writer.book
    worksheet = workbook.add_worksheet('Resumen Medicamentos')

    # Formatos para el archivo Excel
    bold_format = workbook.add_format({'bold': True})  # Negrita
    border_format = workbook.add_format({'border': 1})  # Borde alrededor de la tabla
    header_format = workbook.add_format({'bold': True, 'border': 1})  # Negrita y borde para el encabezado
    title_format = workbook.add_format({'bold': True, 'font_size': 14})  # Negrita y tamaño de fuente 14 para el título

    # Inicializar fila inicial y total general
    start_row = 0
    total_general = 0

    # Iterar sobre cada grupo de pacientes
    for paciente in df['Paciente'].unique():
        # Filtrar los datos por el paciente actual
        data_paciente = df[df['Paciente'] == paciente]

        # Calcular el subtotal por medicamento y el total financiador por paciente
        data_paciente['Subtotal'] = data_paciente['Cantidad'] * data_paciente['Precio']
        total_financiador = data_paciente['Subtotal'].sum()

        # Agregar al total general
        total_general += total_financiador

        # Encabezado personalizado por paciente
        worksheet.write(start_row, 0, 'Paciente:', bold_format)
        worksheet.write(start_row, 1, paciente)

        
        # Encabezado de la tabla
        headers = ['Codigo', 'Medicamento','Cantidad', 'Precio U', 'Subtotal']
        for col_num, header in enumerate(headers):
            worksheet.write(start_row + 2, col_num, header, header_format)

        # Escribir los datos del paciente
        for row_num, row_data in enumerate(data_paciente[['Codigo','Medicamento','Cantidad', 'Precio', 'Subtotal']].values, start=start_row + 3):
            for col_num, value in enumerate(row_data):
                worksheet.write(row_num, col_num, value, border_format)

        for col_num, col in enumerate(['Codigo', 'Medicamento','Cantidad', 'Precio', 'Subtotal']):
            max_len = max(data_paciente[col].astype(str).map(len).max(), len(col)) + 2  # Encontrar la longitud máxima
            worksheet.set_column(col_num, col_num, max_len)  # Ajustar el ancho de la columna


        # Escribir el total financiador para el paciente
        total_row = row_num + 1
        worksheet.write(total_row, 3, 'Total:', bold_format)
        worksheet.write(total_row, 4, total_financiador, bold_format)

        # Ajustar la fila inicial para el próximo paciente (dejando una fila en blanco)
        start_row = total_row + 3

    # Escribir el total general en la última fila
    worksheet.write(start_row, 2, 'Total General:', bold_format)
    worksheet.write(start_row, 3, total_general, bold_format)

    # Guardar y cerrar el archivo Excel
    writer.close()

    return "Archivo Excel generado exitosamente con todos los pacientes y total general."
 







import os
import re
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage   
from io import BytesIO

# Patrones de búsqueda (puedes personalizarlos según tus necesidades)
PATTERNS = {
    "fechas": r"\\d{2}/\\d{2}/\\d{4}",  # Ejemplo: 01/12/2024
    "matriculas": r"MP\\s?\\d+",         # Ejemplo: MP 12345
    "medicos": r"Dr\\.\\s?[A-Za-z]+",   # Ejemplo: Dr. García
}

# Función para encontrar patrones en el texto de una página
def find_patterns_in_page(text):
    results = {}
    for key, pattern in PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            results[key] = matches
    return results

# Función para procesar un PDF y encontrar páginas relevantes
@csrf_exempt
def process_pdf_and_filter(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]

        # Guardar el archivo temporalmente
        temp_file_path = default_storage.save(uploaded_file.name, uploaded_file)
        full_temp_file_path = default_storage.path(temp_file_path)

        try:
            relevant_pages = []
            with pdfplumber.open(full_temp_file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    matches = find_patterns_in_page(text)
                    if matches:
                        # Generar una vista previa de la página como imagen
                        image = convert_from_path(full_temp_file_path, first_page=i+1, last_page=i+1)[0]
                        image_path = f"page_preview_{i+1}.png"
                        image.save(image_path)
                        relevant_pages.append({
                            "page_number": i+1,
                            "matches": matches,
                            "image_path": image_path,
                        })

            # Devuelve las páginas relevantes
            return JsonResponse({"pages": relevant_pages})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        finally:
            # Eliminar archivo temporal
            default_storage.delete(temp_file_path)

    return JsonResponse({"error": "Solo se permiten solicitudes POST con un archivo PDF."}, status=400)

# Función para editar una página específica del PDF
def annotate_pdf_page(pdf_path, page_number, annotations):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    # Crear una nueva página con anotaciones
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    for annotation in annotations:
        x, y, text = annotation
        can.drawString(x, y, text)
    can.save()

    # Mover al principio para leer
    packet.seek(0)
    overlay = PdfReader(packet).pages[0]

    # Combinar la página original con la nueva
    original_page = reader.pages[page_number - 1]
    original_page.merge_page(overlay)
    writer.add_page(original_page)

    # Añadir las otras páginas sin modificar
    for i, page in enumerate(reader.pages):
        if i != page_number - 1:
            writer.add_page(page)

    # Guardar el PDF modificado en memoria
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# Vista para editar páginas seleccionadas
@csrf_exempt
def edit_pdf_page(request):
    if request.method == "POST" and request.FILES.get("file"):
        pdf_file = request.FILES["file"]
        page_number = int(request.POST.get("page_number", 1))
        annotations = [
            # Ejemplo de anotaciones: [(x, y, "Texto")]
            (100, 750, "Texto añadido aquí"),
            (150, 700, "Otra anotación")
        ]

        # Anotar el PDF y devolver el archivo modificado
        modified_pdf = annotate_pdf_page(pdf_file, page_number, annotations)
        return FileResponse(modified_pdf, as_attachment=True, filename="PDF_editado.pdf")

    return JsonResponse({"error": "Solo se permiten solicitudes POST con archivo PDF y parámetros."}, status=400)

from django.shortcuts import render

# Vista para cargar la página principal con el formulario
def pdf_filter_view(request):
    return render(request, 'inventaries/upload_pdf.html')  # Aquí se llama al template HTML



 
import os
from .forms import UploadFileForm
# Ruta donde guardar los archivos subidos
UPLOAD_DIR = 'uploaded_files/'

def upload_txt(request):
    template_name = 'medicamentos/upload_txt.html'

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']

            # Guardar archivo en el servidor
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            with open(file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            # Procesar archivo
            data = []
            with open(file_path, 'r') as f:
                for line in f:
                    # Convertir la línea en una lista de caracteres para manipular directamente
                    line_chars = list(line)  # Línea como lista de caracteres
                    columns = line.split()  # Separar por columnas temporales

                    # Procesar columnas sin alterar los espacios originales
                    if len(columns) > 2:
                        col2 = columns[2]
                        if col2.startswith('DES'):
                            start_idx = line.find(col2)
                            line_chars[start_idx:start_idx + len(col2)] = '930306'.ljust(len(col2))
                        elif col2.endswith('X1'):
                            previous_value = col2[:-2].zfill(6)
                            start_idx = line.find(col2)
                            line_chars[start_idx:start_idx + len(col2)] = previous_value.ljust(len(col2))
                    if len(columns) > 5:
                        col5 = columns[5]
                        start_idx = line.find(col5)
                        new_value = col5[:-2] + '26'
                        line_chars[start_idx:start_idx + len(col5)] = new_value.ljust(len(col5))

                    # Reconstruir la línea a partir de la lista de caracteres
                    processed_line = ''.join(line_chars)
                    data.append(processed_line)

            # Guardar las líneas procesadas en el archivo de salida
            output_file_path = os.path.join(UPLOAD_DIR, 'processed_' + uploaded_file.name)
            with open(output_file_path, 'w') as output_file:
                output_file.write(''.join(data))

            # Descargar archivo procesado
            return FileResponse(open(output_file_path, 'rb'), as_attachment=True, filename='processed_' + uploaded_file.name)

        return render(request, template_name, {'form': form, 'error': 'Archivo inválido'})

    else:
        form = UploadFileForm()
        return render(request, template_name, {'form': form})

