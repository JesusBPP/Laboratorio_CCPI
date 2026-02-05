import pandas as pd
import numpy as np
import re

"""
DESCRIPCIÓN DEL ARCHIVO: cleaner.py
ROL: Motor lógico encargado de las operaciones de limpieza y estandarización.
ACTUALIZACIÓN:
- Función 'get_unique_values_by_pattern' para inspección profunda de grupos.
"""

# --- FUNCIONES DE AYUDA (Helpers) ---

def _safe_duplicate_check(df: pd.DataFrame):
    try:
        return df.duplicated()
    except TypeError:
        return df.astype(str).duplicated()

def _generate_skeleton(text: str) -> str:
    if pd.isna(text): return "NULO"
    text = str(text)
    text = re.sub(r'\d', 'N', text)
    text = re.sub(r'[a-zA-Z]', 'A', text)
    return text

# --- METRICAS DE SALUD GLOBAL ---

def get_data_health_summary(df: pd.DataFrame) -> dict:
    # 1. Nulos (Nativos)
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0].sort_values(ascending=False)
    total_cells = df.size
    total_nulls = null_counts.sum()
    
    # 2. Duplicados
    duplicates_count = _safe_duplicate_check(df).sum()
    
    return {
        "total_nulls": total_nulls,
        "pct_nulls": (total_nulls / total_cells) * 100 if total_cells > 0 else 0,
        "total_dupes": duplicates_count,
        "pct_dupes": (duplicates_count / len(df)) * 100 if len(df) > 0 else 0,
        "null_cols_df": pd.DataFrame({
            "Columna": null_cols.index,
            "Nulos": null_cols.values,
            "%": ((null_cols.values / len(df)) * 100).round(1)
        })
    }

# --- FUNCIONES DE PATRONES Y HOMOGENEIDAD ---

def analyze_text_patterns(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Analiza patrones y determina si son grupos homogéneos.
    """
    series = df[column].astype(str)
    
    temp_df = pd.DataFrame({
        'val': series,
        'patron': series.map(_generate_skeleton)
    })
    
    stats = temp_df.groupby('patron')['val'].agg([
        ('Cantidad', 'count'),
        ('Ejemplo', 'first'),
        ('ValoresDistintos', 'nunique')
    ]).reset_index()
    
    stats['% del Total'] = (stats['Cantidad'] / len(df) * 100).round(1)
    stats['¿Valor Único?'] = stats['ValoresDistintos'] == 1
    
    stats = stats.sort_values('Cantidad', ascending=False)
    stats = stats.rename(columns={'patron': 'Patrón'})
    
    return stats[['Patrón', 'Cantidad', '% del Total', '¿Valor Único?', 'Ejemplo']]

def get_unique_values_by_pattern(df: pd.DataFrame, column: str, pattern: str) -> list:
    """
    Retorna la lista de valores únicos reales que caen bajo un patrón específico.
    Usado para dar contexto al usuario antes de un reemplazo masivo.
    """
    # Filtramos las filas que coinciden con el esqueleto
    mask = df[column].astype(str).map(_generate_skeleton) == pattern
    # Extraemos los valores únicos
    return df[mask][column].unique().tolist()

def replace_values_by_pattern(df: pd.DataFrame, column: str, target_pattern: str, new_value) -> pd.DataFrame:
    """
    Reemplaza TODOS los valores que coincidan con un patrón específico.
    """
    df_clean = df.copy()
    mask = df_clean[column].astype(str).map(_generate_skeleton) == target_pattern
    
    if new_value == "NULL_marker_internal":
        df_clean.loc[mask, column] = None
    else:
        df_clean.loc[mask, column] = new_value
        
    return df_clean

def standardize_by_example(df: pd.DataFrame, column: str, example_origin: str, example_target: str) -> pd.DataFrame:
    df_clean = df.copy()
    tokens = re.findall(r'[a-zA-Z0-9]+', example_origin)
    if not tokens: raise ValueError("No pude detectar datos en el ejemplo.")
    
    regex_pattern = re.escape(example_origin)
    for token in tokens:
        regex_pattern = regex_pattern.replace(re.escape(token), r'([a-zA-Z0-9]+)', 1)
        
    replacement_str = example_target
    for i, token in enumerate(tokens):
        group_ref = f"\\g<{i+1}>"
        replacement_str = replacement_str.replace(token, group_ref, 1)
        
    skeleton_origin = _generate_skeleton(example_origin)
    mask = df_clean[column].astype(str).map(_generate_skeleton) == skeleton_origin
    
    try:
        df_clean.loc[mask, column] = df_clean.loc[mask, column].astype(str).str.replace(
            regex_pattern, replacement_str, regex=True
        )
    except Exception as e:
        raise ValueError(f"Error aplicando regex: {e}")
        
    return df_clean

# --- FUNCIONES PRINCIPALES ---

def count_duplicates(df: pd.DataFrame) -> int:
    return _safe_duplicate_check(df).sum()

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    mask = _safe_duplicate_check(df)
    return df[~mask].copy()

def impute_missing_values(df: pd.DataFrame, column: str, method: str) -> pd.DataFrame:
    df_clean = df.copy()
    if method == 'Eliminar Renglones':
        return df_clean.dropna(subset=[column])
    
    if method in ['Promedio (Media)', 'Mediana']:
        try:
            numeric_series = pd.to_numeric(df_clean[column], errors='coerce')
            if numeric_series.isnull().all() and not df_clean[column].isnull().all():
                 raise ValueError(f"La columna '{column}' contiene texto y no se puede calcular {method}.")
            val = numeric_series.mean() if method == 'Promedio (Media)' else numeric_series.median()
            
            if pd.api.types.is_string_dtype(df_clean[column]):
                df_clean[column] = numeric_series
            df_clean[column] = df_clean[column].fillna(val)
        except Exception as e:
            raise ValueError(f"Error calculando estadística: {str(e)}")
            
    elif method == 'Valor Cero':
        if pd.api.types.is_numeric_dtype(df_clean[column]):
            df_clean[column] = df_clean[column].fillna(0)
        else:
            df_clean[column] = df_clean[column].fillna("0")
    return df_clean

def convert_column_type(df: pd.DataFrame, column: str, new_type: str) -> pd.DataFrame:
    df_clean = df.copy()
    try:
        if new_type == "Texto (String)":
            df_clean[column] = df_clean[column].astype(str)
        elif new_type == "Número Entero":
            df_clean[column] = pd.to_numeric(df_clean[column], errors='coerce').fillna(0).astype(int)
        elif new_type == "Número Decimal":
            df_clean[column] = pd.to_numeric(df_clean[column], errors='coerce')
        elif new_type == "Fecha":
            df_clean[column] = pd.to_datetime(df_clean[column], errors='coerce')
        return df_clean
    except Exception as e:
        raise ValueError(f"No se pudo convertir: {str(e)}")