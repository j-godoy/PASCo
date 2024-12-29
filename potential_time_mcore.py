import os
import pandas as pd
import sys
import math

def process_csv(file_path, n_cores, summary_data):
    # Leer el archivo CSV
    df = pd.read_csv(file_path)

    # Filtrar las filas por tipo
    query_reduce = df[df['Type'] == 'QUERY_REDUCE_COMBINATION']
    other_queries = df[df['Type'] != 'QUERY_REDUCE_COMBINATION']

    # Calcular N para QUERY_REDUCE_COMBINATION
    n_query_reduce = math.ceil(len(query_reduce) / n_cores)
    # Calcular N para las demás filas
    n_other_queries = math.ceil(len(other_queries) / n_cores)

    simulaciones = 100
    promedios_query_reduce = []
    promedios_other_queries = []
    for i in range(simulaciones):
        # Seleccionar los N filas aleatoriamente para QUERY_REDUCE_COMBINATION
        top_query_reduce = query_reduce.sample(n=n_query_reduce, random_state=None) if n_query_reduce > 0 else pd.DataFrame()
        
        # Seleccionar los N filas aleatoriamente para otras consultas
        top_other_queries = other_queries.sample(n=n_other_queries, random_state=None) if n_other_queries > 0 else pd.DataFrame()
        
        # Calcular la suma de tiempos para cada tipo
        if len(top_query_reduce) > 0:
            total_time_query_reduce = top_query_reduce['time(sec)'].sum()
            promedios_query_reduce.append(total_time_query_reduce)
        if len(top_other_queries) > 0:
            total_time_other_queries = top_other_queries['time(sec)'].sum()     
            promedios_other_queries.append(total_time_other_queries)

        # Combinar los resultados
        result = pd.concat([top_query_reduce, top_other_queries])
        total_queries = len(result)
    
    # Calcular los promedios finales
    promedio_time_query_reduce = sum(promedios_query_reduce) / simulaciones
    promedio_time_other_queries = sum(promedios_other_queries) / simulaciones
    total_time = round(promedio_time_query_reduce + promedio_time_other_queries, 2)
    # Obtener el nombre del archivo sin la extensión "_query_time.csv"
    subject = os.path.basename(file_path).replace('_query_time.csv', '')
    
    # Añadir los datos al resumen
    summary_data.append({'subject': subject, 'total_queries': total_queries, 'time(secs)': total_time})
    
    # print(f"Archivo: {file_path}, Suma total de 'time(sec)': {total_time}")


def process_directory(path, n_cores):
    
    summary_data = []
    output_file = "summary_query_time_ncores.csv"
    
    # Buscar todos los archivos que terminan en _query_time.csv
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('_query_time.csv'):
                file_path = os.path.join(root, file)
                print(f"Procesando: {file_path}")
                process_csv(file_path, n_cores, summary_data)
    
    # Crear un DataFrame con el resumen
    summary_df = pd.DataFrame(summary_data)
    # Guardar el resumen en un archivo CSV
    summary_df.to_csv(output_file, index=False)

def main():
    if len(sys.argv) != 3:
        print("Uso: python script.py <path> <n_cores>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        n_cores = int(sys.argv[2])
    except ValueError:
        print("second argument must be an integer.")
        sys.exit(1)

    if not os.path.exists(path):
        print(f"Path {path} does not exist.")
        sys.exit(1)

    process_directory(path, n_cores)

if __name__ == "__main__":
    main()
