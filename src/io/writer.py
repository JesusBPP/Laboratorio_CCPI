import pandas as pd
import os
import io
from datetime import datetime

"""
DESCRIPCIÓN DEL ARCHIVO: writer.py

ROL:
Este módulo es la SALIDA DE DATOS del sistema. Se encarga de la persistencia
en disco y de la generación de archivos para descargar.

FUNCIONES PRINCIPALES:
1. save_to_internal_db(df, filename): Guarda el DataFrame actual en formato 
   Apache Parquet dentro de la carpeta 'data/parquet_db/'. Esto actúa como
   nuestra "Base de Datos" local.
   
2. convert_to_csv(df): Convierte el DataFrame a bytes CSV para descarga.
3. convert_to_excel(df): Convierte el DataFrame a bytes Excel para descarga.

BUENAS PRÁCTICAS:
- Usa compresión 'snappy' para Parquet (balance ideal entre velocidad/peso).
- Gestiona nombres de archivo automáticos con timestamps para no sobrescribir 
  si el usuario no quiere.
"""

# Rutas constantes (basadas en tu arquitectura de carpetas)
DB_PATH = "data/parquet_db"
EXPORT_PATH = "data/exports"

def _ensure_folder_exists(folder_path):
    """Crea la carpeta si no existe."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def save_to_internal_db(df: pd.DataFrame, original_filename: str) -> str:
    """
    Guarda el DataFrame en la 'Base de Datos' local (sistema de archivos)
    usando formato Parquet.
    
    Args:
        df: El DataFrame a guardar.
        original_filename: Nombre base para generar el archivo.
        
    Returns:
        str: Mensaje de éxito con la ruta del archivo guardado.
    """
    _ensure_folder_exists(DB_PATH)
    
    # Limpiamos la extensión original y agregamos timestamp para historial
    clean_name = os.path.splitext(original_filename)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Nombre final: reporte_ventas_PROCESADO_20231027_1030.parquet
    final_name = f"{clean_name}_PROCESADO_{timestamp}.parquet"
    full_path = os.path.join(DB_PATH, final_name)
    
    try:
        # Guardamos usando el motor PyArrow
        df.to_parquet(full_path, engine='pyarrow', compression='snappy')
        return f"Guardado correctamente en: {final_name}"
    except Exception as e:
        raise IOError(f"Error al escribir Parquet: {str(e)}")

def convert_to_csv(df: pd.DataFrame) -> bytes:
    """Convierte DF a bytes CSV para el botón de descarga."""
    output = io.BytesIO()
    # index=False para no ensuciar el archivo con el índice numérico de pandas
    df.to_csv(output, index=False, encoding='utf-8')
    return output.getvalue()

def convert_to_excel(df: pd.DataFrame) -> bytes:
    """Convierte DF a bytes Excel para el botón de descarga."""
    output = io.BytesIO()
    # Usamos xlsxwriter como motor
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos_Procesados')
    return output.getvalue()