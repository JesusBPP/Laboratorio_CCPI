import pandas as pd
import pyarrow as pa
import json
import io
# Importamos lxml para XML, pero lo manejamos con cuidado por si falta
try:
    import lxml
except ImportError:
    lxml = None

"""
DESCRIPCIÓN DEL ARCHIVO: loader.py

ROL:
Este módulo es la PUERTA DE ENTRADA de datos al sistema. Su responsabilidad es
tomar cualquier archivo binario subido por el usuario, detectar su formato
y convertirlo exitosamente en un DataFrame de Pandas optimizado con PyArrow.

FUNCIONES:
1. load_file_to_dataframe(): Función maestra que decide qué sub-función llamar.
2. Soporte multiformato: CSV, Excel, Parquet, JSON, XML, GeoJSON, TopJSON.
3. Estandarización: Todos los datos salen convertidos a tipos PyArrow (dtype_backend='pyarrow')
   para garantizar consistencia y velocidad en el resto del laboratorio.

MANEJO DE ERRORES:
Implementa bloques try-except específicos para dar mensajes claros al usuario
si un archivo está corrupto o tiene un formato no soportado.
"""

def _convert_to_arrow_backend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ayuda interna para asegurar que cualquier DataFrame (venga de Excel o JSON)
    se convierta al motor de memoria eficiente de PyArrow.
    """
    try:
        # Intenta convertir tipos automáticamente a sus equivalentes en Arrow
        # (ej. int64 -> int64[pyarrow], object -> string[pyarrow])
        return df.convert_dtypes(dtype_backend="pyarrow")
    except Exception as e:
        # Si falla la conversión optimizada, devolvemos el df normal pero logueamos el aviso
        print(f"Advertencia: No se pudo optimizar a tipos Arrow completamente: {e}")
        return df

def _load_csv(file_buffer) -> pd.DataFrame:
    """Carga CSV usando el motor de PyArrow para velocidad máxima."""
    try:
        return pd.read_csv(
            file_buffer, 
            engine="pyarrow", 
            dtype_backend="pyarrow"
        )
    except Exception as e:
        # Fallback: Si falla pyarrow (a veces pasa con codificaciones raras), intentamos engine 'c'
        file_buffer.seek(0)
        return pd.read_csv(file_buffer)

def _load_excel(file_buffer) -> pd.DataFrame:
    """Carga Excel (.xlsx). Requiere openpyxl."""
    # Excel no soporta motor pyarrow nativo al leer, así que leemos normal y luego convertimos
    df = pd.read_excel(file_buffer, engine="openpyxl")
    return df # Se convertirá a Arrow en la función principal

def _load_parquet(file_buffer) -> pd.DataFrame:
    """Carga Apache Parquet."""
    return pd.read_parquet(file_buffer, engine="pyarrow")

def _load_json(file_buffer) -> pd.DataFrame:
    """
    Carga JSON estándar. 
    Intenta normalizar si es una lista de objetos.
    """
    try:
        return pd.read_json(file_buffer, dtype_backend="pyarrow")
    except ValueError:
        # Si falla, puede ser un JSON anidado complejo.
        # Reiniciamos el puntero del archivo
        file_buffer.seek(0)
        data = json.load(file_buffer)
        # Intentamos normalizar (aplanar) el JSON
        return pd.json_normalize(data)

def _load_xml(file_buffer) -> pd.DataFrame:
    """Carga XML. Requiere librería 'lxml' instalada."""
    if lxml is None:
        raise ImportError("La librería 'lxml' es necesaria para leer XML. Agrégala a requirements.txt")
    
    return pd.read_xml(file_buffer)

def _load_geojson(file_buffer) -> pd.DataFrame:
    """
    Extrae la tabla de atributos (Properties) de un GeoJSON.
    Ignora la geometría para fines de limpieza de datos tabular.
    """
    data = json.load(file_buffer)
    
    if "features" not in data:
        raise ValueError("El archivo no parece ser un GeoJSON válido (falta la clave 'features')")
    
    # Aplanamos solo la parte de 'properties' de cada feature
    # Esto crea una tabla con columnas como 'nombre', 'poblacion', etc.
    df = pd.json_normalize(data["features"])
    
    # Limpiamos prefijos feos si json_normalize los deja (opcional, pero recomendado)
    # Por ejemplo, transforma "properties.nombre" a "nombre" si es posible
    df.columns = [c.replace("properties.", "") for c in df.columns]
    
    return df

def _load_topjson(file_buffer) -> pd.DataFrame:
    """
    Extrae atributos de TopJSON. Es más complejo porque puede tener múltiples objetos.
    Busca dentro de 'objects' y extrae sus propiedades.
    """
    data = json.load(file_buffer)
    
    if "objects" not in data:
        raise ValueError("El archivo no parece ser TopJSON válido (falta la clave 'objects')")
    
    all_rows = []
    
    # Un TopJSON puede tener varios grupos de geometrías (ej. "estados", "condados")
    for object_name, obj_content in data["objects"].items():
        geometries = obj_content.get("geometries", [])
        for geom in geometries:
            # Extraemos las propiedades
            props = geom.get("properties", {})
            # Agregamos una columna para saber de qué grupo vino
            props["_topjson_group"] = object_name 
            all_rows.append(props)
            
    if not all_rows:
        raise ValueError("No se encontraron propiedades/datos en el archivo TopJSON.")
        
    return pd.DataFrame(all_rows)


def load_file_to_dataframe(file_buffer, file_name: str) -> pd.DataFrame:
    """
    FUNCIÓN PRINCIPAL
    Identifica la extensión y delega la carga al motor correspondiente.
    
    Args:
        file_buffer: El objeto bytesIO que entrega Streamlit.
        file_name (str): Nombre del archivo para detectar extensión.
        
    Returns:
        pd.DataFrame: DataFrame con backend PyArrow.
        
    Raises:
        ValueError: Si el formato no es soportado o el archivo está corrupto.
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
            df = _load_topjson(file_buffer) # Usamos extensión .topjson por convención
        # Soporte para topjson si viene como .json pero el usuario sabe que es mapa
        elif extension == 'json' and 'topo' in file_name.lower(): 
             # Nota: Esto es ambiguo, por ahora asumimos json normal si la extensión es json
             pass 
        else:
            raise ValueError(f"Formato no soportado: .{extension}")

        # Paso Final: Estandarización a Arrow
        # Si el loader específico no devolvió Arrow backend (como Excel o JSON), lo forzamos aquí.
        if df is not None:
            return _convert_to_arrow_backend(df)
        
    except Exception as e:
        # Re-lanzamos el error con contexto para que la UI lo muestre bonito
        raise ValueError(f"Error procesando {file_name}: {str(e)}")

    return pd.DataFrame() # Retorno vacío por seguridad