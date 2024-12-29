import os
import csv

def unir_archivos_query_time(path, resumen_path, file_ends_with="_query_time.csv"):
    
    # Lista para almacenar las filas combinadas
    filas_combinadas = []
    
    # Bandera para escribir encabezados solo una vez
    encabezados_escritos = False
    
    # Buscar y procesar todos los archivos que terminan en "_query_time.csv"
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(file_ends_with):
                archivo_path = os.path.join(root, file)
                print(f"Procesando archivo: {archivo_path}")
                
                # Extraer el nombre base del archivo (antes de "_query_time.csv")
                nombre_base = file.replace("_query_time.csv", "")
                
                with open(archivo_path, "r", newline='', encoding="utf-8") as f:
                    reader = csv.reader(f)
                    encabezados = next(reader)  # Leer encabezados
                    
                    # Escribir encabezados solo si aún no se han escrito
                    if not encabezados_escritos:
                        filas_combinadas.append(encabezados + ["source_file"])  # Agregar nueva columna
                        encabezados_escritos = True
                    
                    # Leer y almacenar las filas del archivo, agregando la nueva columna
                    for row in reader:
                        # if len(row) != 4:
                        #     continue
                        filas_combinadas.append(row + [nombre_base])
    
    # Crear el archivo de resumen
    with open(resumen_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(filas_combinadas)
    
    print(f"Archivo de resumen generado: {resumen_path}")

# Path de búsqueda
path = r"path/to/files"
file_ends_with="_query_time.csv"

# Crear el nombre del archivo de resumen
salida = os.path.join("summary_query_time.csv")
unir_archivos_query_time(path, salida, file_ends_with)
