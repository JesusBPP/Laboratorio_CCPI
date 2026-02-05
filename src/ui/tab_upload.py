import streamlit as st
import pandas as pd
import os
from io import BytesIO

# Importamos módulos internos
try:
    from src.io import loader
    from utils import session
except ImportError:
    pass

"""
DESCRIPCIÓN DEL ARCHIVO: tab_upload.py
ROL: Interfaz visual para la carga de datos (Nuevos o Existentes).
"""

# Ruta donde buscamos los archivos guardados
DB_PATH = "data/parquet_db"

# --- ESTILOS CSS ---
custom_css = """
<style>
    .badge-base {
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
        margin-right: 6px;
        margin-bottom: 8px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .badge-blue { background-color: #E3F2FD; color: #1565C0; }   
    .badge-purple { background-color: #F3E5F5; color: #7B1FA2; } 
    .badge-green { background-color: #E8F5E9; color: #2E7D32; }  
    .badge-red { background-color: #FFEBEE; color: #C62828; }    
    
    /* Estilo para la caja de archivos guardados */
    .saved-files-box {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
    }
</style>
"""

def render_supported_formats():
    st.markdown(custom_css, unsafe_allow_html=True)
    st.markdown("### 📂 Ingesta de Datos")
    st.markdown("""
    El sistema acepta y estandariza automáticamente los siguientes formatos:
    <div style="margin-top: 10px; margin-bottom: 20px;">
        <span class="badge-base badge-blue">CSV</span>
        <span class="badge-base badge-blue">Excel</span>
        <span class="badge-base badge-purple">Parquet</span>
        <span class="badge-base badge-purple">JSON</span>
        <span class="badge-base badge-green">GeoJSON</span>
        <span class="badge-base badge-green">TopJSON</span>
        <span class="badge-base badge-red">XML</span>
    </div>
    """, unsafe_allow_html=True)

def show_success_metrics(df, file_name):
    """Muestra el feedback visual después de cargar cualquier archivo."""
    st.success(f"✅ ¡Listo! **{file_name}** cargado en memoria.")
    with st.container():
        col1, col2, col3 = st.columns(3)
        col1.metric("Filas Totales", f"{df.shape[0]:,}")
        col2.metric("Columnas Detectadas", f"{df.shape[1]}")
        mem_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)
        col3.metric("Uso RAM", f"{mem_usage:.2f} MB")

def process_and_save(file_obj, file_name):
    """Procesa un archivo NUEVO (Upload)."""
    try:
        with st.spinner(f"🔄 Procesando subida de {file_name}..."):
            df = loader.load_file_to_dataframe(file_obj, file_name)
            session.set_main_dataframe(df, filename=file_name)
        show_success_metrics(df, file_name)
        return True
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
    return False

def load_local_file(file_name):
    """Procesa un archivo EXISTENTE (Local)."""
    full_path = os.path.join(DB_PATH, file_name)
    try:
        with st.spinner(f"💾 Recuperando {file_name} del disco..."):
            df = loader.load_parquet_from_path(full_path)
            session.set_main_dataframe(df, filename=file_name)
        show_success_metrics(df, file_name)
        return True
    except Exception as e:
        st.error(f"❌ Error al leer archivo local: {str(e)}")
    return False

def render_single_upload():
    """Renderiza la pantalla dividida: Carga Nueva (Izq) vs Archivos Guardados (Der)."""
    st.markdown("#### Carga Directa o Recuperación")
    
    # DIVIDIMOS LA PANTALLA EN 2 COLUMNAS (Ratio 2:1)
    col_upload, col_saved = st.columns([2, 1], gap="large")
    
    # --- COLUMNA IZQUIERDA: SUBIR ARCHIVO NUEVO ---
    with col_upload:
        st.info("⬆️ **Subir Nuevo Archivo**")
        st.caption("Arrastra tu archivo aquí para comenzar un nuevo análisis.")
        
        uploaded_file = st.file_uploader(
            "Seleccionar archivo", 
            type=['csv', 'xlsx', 'xls', 'parquet', 'json', 'xml', 'geojson', 'topjson'],
            key="single_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Procesar Nuevo", key="btn_process_single", use_container_width=True, type="primary"):
                process_and_save(uploaded_file, uploaded_file.name)

    # --- COLUMNA DERECHA: ARCHIVOS GUARDADOS (LO QUE PEDISTE) ---
    with col_saved:
        st.warning("🗄️ **Base de Datos Local**")
        st.caption("Archivos guardados en `data/parquet_db/`")
        
        # 1. Escanear carpeta
        saved_files = []
        if os.path.exists(DB_PATH):
            saved_files = [f for f in os.listdir(DB_PATH) if f.endswith('.parquet')]
            # Ordenamos por fecha (más reciente primero)
            saved_files.sort(key=lambda x: os.path.getmtime(os.path.join(DB_PATH, x)), reverse=True)
        
        # 2. Renderizar la caja de selección
        if saved_files:
            selected_file = st.selectbox(
                "Selecciona un archivo:", 
                saved_files, 
                key="saved_file_selector",
                index=0
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Botón para cargar
            if st.button("📂 Cargar Seleccionado", key="btn_load_local", use_container_width=True):
                load_local_file(selected_file)
        else:
            st.markdown("""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; color: #666;">
                    <i>No hay archivos guardados aún.</i>
                </div>
            """, unsafe_allow_html=True)

def render_merge_upload():
    """Renderiza el área de fusión de archivos."""
    st.markdown("#### Fusión de Tablas (Merge/Append)")
    st.info("💡 Sube dos archivos para combinarlos en una sola tabla maestra.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Archivo Principal (A)**")
        file_a = st.file_uploader("Base", key="merge_a")
    with col_b:
        st.markdown("**Archivo Secundario (B)**")
        file_b = st.file_uploader("A unir", key="merge_b")
        
    if file_a and file_b:
        st.divider()
        merge_type = st.radio("Método de unión:", ["Agregar Renglones (Vertical)", "Agregar Columnas (Horizontal)"], horizontal=True)
        if st.button("🔗 Fusionar Datos", key="btn_process_merge", use_container_width=True, type="primary"):
            st.warning("🚧 El motor 'Merger' se está construyendo.")
            process_and_save(file_a, f"Fusionado_{file_a.name}")

def render_upload_tab():
    """Función principal de la pestaña."""
    render_supported_formats()
    st.divider()
    
    tab1, tab2 = st.tabs(["📄 Carga y Recuperación", "🔗 Herramienta de Fusión"])
    
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        render_single_upload()
            
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        render_merge_upload()

    st.markdown("---")
    st.caption("🔒 Seguridad: Los datos viven temporalmente en tu memoria RAM.")