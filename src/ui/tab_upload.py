import streamlit as st
import pandas as pd
from io import BytesIO

# Importamos módulos internos con manejo de errores para desarrollo
try:
    from src.io import loader
    from utils import session
except ImportError:
    pass

"""
DESCRIPCIÓN DEL ARCHIVO: tab_upload.py
ROL: Interfaz visual para la carga de datos.
ESTILO: Adaptado para Tema Claro (Light Theme) con acentos pastel.
"""

# --- ESTILOS CSS PERSONALIZADOS (Tema Claro Elegante) ---
custom_css = """
<style>
    /* Estilo de las etiquetas de formatos (Badges) */
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
    
    /* Colores Específicos - Optimizados para fondo blanco */
    .badge-blue { background-color: #E3F2FD; color: #1565C0; }   /* CSV, Excel */
    .badge-purple { background-color: #F3E5F5; color: #7B1FA2; } /* Parquet, JSON */
    .badge-green { background-color: #E8F5E9; color: #2E7D32; }  /* Mapas */
    .badge-red { background-color: #FFEBEE; color: #C62828; }    /* XML */
    
    /* Tarjetas contenedoras sutiles */
    .stFileUploader {
        background-color: #FAFAFA;
        padding: 15px;
        border-radius: 10px;
        border: 1px dashed #D1D5DB;
    }
</style>
"""

def render_supported_formats():
    """Muestra los badges de formatos soportados."""
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

def process_and_save(file_obj, file_name):
    """Procesa el archivo y lo guarda en memoria de sesión."""
    try:
        with st.spinner(f"🔄 Leyendo y optimizando {file_name}..."):
            # 1. Llamar al Loader
            df = loader.load_file_to_dataframe(file_obj, file_name)
            
            # 2. Guardar en Sesión
            session.set_main_dataframe(df, filename=file_name)
            
        # 3. Feedback de Éxito
        st.success(f"✅ ¡Listo! {file_name} cargado en memoria.")
        
        # 4. Tarjetas de métricas visuales
        # Usamos un contenedor para darle un fondo sutil si fuera necesario
        with st.container():
            col1, col2, col3 = st.columns(3)
            col1.metric("Filas Totales", f"{df.shape[0]:,}")
            col2.metric("Columnas Detectadas", f"{df.shape[1]}")
            mem_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)
            col3.metric("Uso RAM (Arrow)", f"{mem_usage:.2f} MB")
        
        return True
        
    except ValueError as e:
        st.error(f"⚠️ Formato no reconocido: {str(e)}")
    except Exception as e:
        st.error(f"❌ Error crítico: {str(e)}")
        
    return False

def render_single_upload():
    """Renderiza el área de carga individual."""
    st.markdown("#### Carga Directa")
    st.caption("Arrastra tu archivo al área punteada para comenzar el análisis.")
    
    uploaded_file = st.file_uploader(
        "Seleccionar archivo", 
        type=['csv', 'xlsx', 'xls', 'parquet', 'json', 'xml', 'geojson', 'topjson'],
        key="single_uploader",
        label_visibility="collapsed" # Ocultamos label para un look más limpio
    )
    
    if uploaded_file is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        # Botón grande y claro
        if st.button("🚀 Procesar Archivo", key="btn_process_single", use_container_width=True, type="primary"):
            process_and_save(uploaded_file, uploaded_file.name)

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
        st.markdown("##### ⚙️ Configuración de Fusión")
        
        merge_type = st.radio(
            "Método de unión:",
            options=["Agregar Renglones (Vertical)", "Agregar Columnas (Horizontal)"],
            horizontal=True
        )
        
        if merge_type == "Agregar Renglones (Vertical)":
            st.caption("⬇️ **Append:** Los datos de B se pondrán debajo de A. (Ej. Ventas Enero + Ventas Febrero)")
        else:
            st.caption("➡️ **Join:** Las columnas de B se pegarán a la derecha de A. (Ej. Lista Clientes + Lista Direcciones)")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔗 Fusionar Datos", key="btn_process_merge", use_container_width=True, type="primary"):
            st.warning("🚧 El motor 'Merger' se está construyendo. Cargando solo Archivo A por ahora.")
            process_and_save(file_a, f"Fusionado_{file_a.name}")

def render_upload_tab():
    """Función principal de la pestaña."""
    
    # Renderizamos los badges CSS primero
    render_supported_formats()
    
    st.divider()
    
    # Tabs nativos de Streamlit
    tab1, tab2 = st.tabs(["📄 Carga Simple", "🔗 Herramienta de Fusión"])
    
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True) # Espacio extra
        render_single_upload()
            
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        render_merge_upload()

    st.markdown("---")
    st.caption("🔒 Seguridad: Los datos viven temporalmente en tu memoria RAM y se eliminan al cerrar la pestaña.")