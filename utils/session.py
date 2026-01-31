import streamlit as st
import pandas as pd

"""
DESCRIPCIÓN DEL ARCHIVO: session.py

ROL:
Este módulo actúa como el GESTOR DE MEMORIA (State Manager) de la aplicación.
Streamlit es "stateless" por naturaleza (no recuerda nada entre interacciones). 
Este archivo encapsula la lógica para inicializar, recuperar y guardar datos 
en 'st.session_state'.

FUNCIONES PRINCIPALES:
1. init_session_state(): Se llama al inicio de la app para asegurar que las variables existen.
2. set_main_dataframe(): Guarda el DataFrame (Arrow/Pandas) en memoria.
3. get_main_dataframe(): Recupera el DataFrame actual para usarlo en gráficas o tablas.
4. clear_data(): Limpia la memoria (útil cuando se sube un archivo nuevo).
"""

# Definimos las claves (keys) que usaremos en el diccionario de sesión
KEY_MAIN_DF = "main_data"         # Aquí vivirá el DataFrame principal
KEY_FILE_NAME = "current_filename" # Nombre del archivo para mostrar en UI

def init_session_state():
    """
    Inicializa las variables de estado si no existen.
    Debe llamarse al principio de app.py.
    """
    if KEY_MAIN_DF not in st.session_state:
        st.session_state[KEY_MAIN_DF] = None
        
    if KEY_FILE_NAME not in st.session_state:
        st.session_state[KEY_FILE_NAME] = "Ningún archivo cargado"

def set_main_dataframe(df: pd.DataFrame, filename: str = None):
    """
    Guarda un DataFrame en la memoria de la sesión.
    
    Args:
        df: El DataFrame de Pandas (idealmente con backend PyArrow).
        filename: El nombre del archivo fuente (opcional).
    """
    st.session_state[KEY_MAIN_DF] = df
    if filename:
        st.session_state[KEY_FILE_NAME] = filename

def get_main_dataframe() -> pd.DataFrame:
    """
    Recupera el DataFrame almacenado en memoria.
    
    Returns:
        pd.DataFrame or None: El dataframe actual o None si no hay nada cargado.
    """
    return st.session_state.get(KEY_MAIN_DF, None)

def get_current_filename() -> str:
    """Devuelve el nombre del archivo actual."""
    return st.session_state.get(KEY_FILE_NAME, "")

def clear_session():
    """
    Borra los datos de la sesión. Útil al reiniciar el laboratorio.
    """
    st.session_state[KEY_MAIN_DF] = None
    st.session_state[KEY_FILE_NAME] = "Ningún archivo cargado"

def is_data_loaded() -> bool:
    """
    Helper para saber rápidamente si tenemos datos listos para trabajar.
    """
    return st.session_state[KEY_MAIN_DF] is not None