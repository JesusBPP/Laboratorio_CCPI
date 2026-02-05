import pandas as pd
import pyarrow as pa
import json
import io
import os
import csv

# Importamos lxml para XML, pero lo manejamos con cuidado por si falta
try:
    import lxml
except ImportError:
    lxml = None

"""
DESCRIPCIÓN DEL ARCHIVO: loader.py

ROL:
Este módulo es la PUERTA DE ENTRADA de datos al sistema. Su responsabilidad es
tomar cualquier archivo binario subido por el usuario o recuperado del disco,
detectar su formato, limpiar inconsistencias iniciales (como metadatos en CSV)
y convertirlo exitosamente en un DataFrame de Pandas optimizado con PyArrow.

FUNCIONES PRINCIPALES:
1. load_file_to_dataframe(): Procesa archivos subidos (Upload), gestionando extensiones.
2. load_parquet_from_path(): Recupera archivos ya procesados del disco local.
3. _detect_header_row_and_delimiter(): (Smart Sniffer) Analiza archivos CSV sucios 
   para encontrar automáticamente dónde empieza la tabla real, ignorando títulos o logos.

SOPORTE:
- Tabulares: CSV, Excel, Parquet.
- Estructurados: JSON, XML.
- Geoespaciales: GeoJSON, TopJSON.
"""

def _convert_to_arrow_backend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ayuda interna para asegurar que cualquier DataFrame (venga de Excel o JSON)
    se convierta al motor de memoria eficiente de PyArrow.
    """
    try:
        return df.convert_dtypes(dtype_backend="pyarrow")
    except Exception as e:
        # Si falla la conversión estricta, devolvemos el df estándar pero logueamos
        print(f"Advertencia: No se pudo optimizar a tipos Arrow completamente: {e}")
        return df

def _detect_header_row_and_delimiter(file_buffer, max_scan_lines=50):
    """
    Función Inteligente:
    Escanea las primeras N líneas para detectar metadatos "basura" al inicio.
    Retorna la fila donde probablemente empieza la tabla y el delimitador usado.
    """
    file_buffer.seek(0)
    lines = []
    
    # Leemos una muestra decodificando bytes a string
    for _ in range(max_scan_lines):
        line = file_buffer.readline()
        if not line: break
        try:
            lines.append(line.decode('utf-8', errors='ignore'))
        except:
            continue
            
    file_buffer.seek(0) # Reseteamos el puntero SIEMPRE
    
    if not lines:
        return 0, ','

    delimiters = [',', ';', '\t', '|']
    best_delimiter = ','
    max_cols_found = 0
    best_header_row = 0
    
    # Heurística: La fila de encabezado real suele tener muchas columnas
    # comparado con los títulos del reporte (que suelen tener 1 sola columna)
    for i, line in enumerate(lines):
        if not line.strip(): continue # Ignorar líneas vacías
        
        for delim in delimiters:
            # Contamos separadores. Columnas = separadores + 1
            cols = line.count(delim) + 1
            
            # Buscamos la fila que maximice el número de columnas (la tabla real)
            # Filtramos casos triviales (cols > 1)
            if cols > max_cols_found and cols > 1:
                max_cols_found = cols
                best_header_row = i
                best_delimiter = delim

    return best_header_row, best_delimiter

def _load_csv(file_buffer) -> pd.DataFrame:
    """
    Carga CSV de forma robusta. Intenta lectura directa primero,
    si falla, activa el 'Smart Sniffer' para saltar metadatos.
    """
    try:
        # Intento 1: Lectura Rápida (PyArrow Engine)
        # Asumimos archivo limpio (Header en fila 0)
        return pd.read_csv(file_buffer, engine="pyarrow", dtype_backend="pyarrow")
    
    except (pd.errors.ParserError, ValueError):
        # Intento 2: Falló la lectura. Probablemente hay títulos arriba.
        # Activamos detección inteligente.
        try:
            skip_rows, detected_sep = _detect_header_row_and_delimiter(file_buffer)
            
            file_buffer.seek(0)
            # Usamos engine='python' que es más tolerante con skiprows dinámicos
            return pd.read_csv(
                file_buffer, 
                skiprows=skip_rows, 
                sep=detected_sep,
                dtype_backend="pyarrow" # Intentamos mantener la optimización de memoria
            )
        except Exception as e:
            raise ValueError(f"No se pudo leer el CSV. Posible formato corrupto o metadatos complejos. Detalle: {str(e)}")

def _load_excel(file_buffer) -> pd.DataFrame:
    """Carga Excel (.xlsx) usando openpyxl."""
    # Excel suele manejar mejor los headers, pero si falla podríamos implementar lógica similar
    df = pd.read_excel(file_buffer, engine="openpyxl")
    return df 

def _load_parquet(file_buffer) -> pd.DataFrame:
    """Carga formato Parquet nativo."""
    return pd.read_parquet(file_buffer, engine="pyarrow")

def _load_json(file_buffer) -> pd.DataFrame:
    """Carga JSON, intentando aplanar estructuras anidadas."""
    try:
        return pd.read_json(file_buffer, dtype_backend="pyarrow")
    except ValueError:
        file_buffer.seek(0)
        data = json.load(file_buffer)
        return pd.json_normalize(data)

def _load_xml(file_buffer) -> pd.DataFrame:
    """Carga XML (requiere lxml)."""
    if lxml is None:
        raise ImportError("La librería 'lxml' es necesaria para leer XML.")
    return pd.read_xml(file_buffer)

def _load_geojson(file_buffer) -> pd.DataFrame:
    """Extrae propiedades (tabla de atributos) de un GeoJSON."""
    data = json.load(file_buffer)
    if "features" not in data:
        raise ValueError("El archivo no parece ser un GeoJSON válido")
    df = pd.json_normalize(data["features"])
    # Limpiamos prefijos feos de la conversión
    df.columns = [c.replace("properties.", "") for c in df.columns]
    return df

def _load_topjson(file_buffer) -> pd.DataFrame:
    """Extrae propiedades de un TopJSON iterando sobre sus objetos."""
    data = json.load(file_buffer)
    if "objects" not in data:
        raise ValueError("El archivo no parece ser TopJSON válido")
    all_rows = []
    for object_name, obj_content in data["objects"].items():
        geometries = obj_content.get("geometries", [])
        for geom in geometries:
            props = geom.get("properties", {})
            props["_topjson_group"] = object_name 
            all_rows.append(props)
    if not all_rows:
        raise ValueError("No se encontraron propiedades/datos en el archivo TopJSON.")
    return pd.DataFrame(all_rows)

def load_file_to_dataframe(file_buffer, file_name: str) -> pd.DataFrame:
    """
    FUNCIÓN PRINCIPAL (UPLOADS)
    Identifica la extensión y delega la carga al motor correspondiente.
    """
    extension = file_name.split('.')[-1].lower()
    df = None
    
    try:
        if extension == 'csv':
            df = _load_csv(file_buffer)
        elif extension in ['xlsx', 'xls']:
            df = _load_excel(file_buffer)
        elif extension == 'parquet':
            df = _load_parquet(file_buffer)
        elif extension == 'json':
            df = _load_json(file_buffer)
        elif extension == 'xml':
            df = _load_xml(file_buffer)
        elif extension == 'geojson':
            df = _load_geojson(file_buffer)
        elif extension == 'topjson':
            df = _load_topjson(file_buffer) 
        elif extension == 'json' and 'topo' in file_name.lower(): 
             pass # Tratamiento especial ambiguo (asumimos json)
        else:
            raise ValueError(f"Formato no soportado: .{extension}")

        # Estandarización final a Arrow
        if df is not None:
            return _convert_to_arrow_backend(df)
        
    except Exception as e:
        raise ValueError(f"Error procesando {file_name}: {str(e)}")

    return pd.DataFrame()

def load_parquet_from_path(file_path: str) -> pd.DataFrame:
    """
    NUEVA FUNCIÓN: Carga un archivo Parquet directamente desde el disco local.
    Usada para recuperar archivos guardados en data/parquet_db/
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"El archivo no existe: {file_path}")
        
    try:
        # Leemos directo del path usando pyarrow
        df = pd.read_parquet(file_path, engine='pyarrow')
        # Aseguramos compatibilidad
        return _convert_to_arrow_backend(df)
    except Exception as e:
        raise ValueError(f"Error leyendo archivo local: {str(e)}")