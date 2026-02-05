import streamlit as st
import pandas as pd
from utils import session

# Importamos los submódulos de UI y IO
try:
    from src.ui import tab_cleaner  # <--- Ahora importamos el archivo separado
    from src.io import writer       # <--- Para el guardado
except ImportError:
    pass

"""
DESCRIPCIÓN DEL ARCHIVO: tab_viewer.py
ROL: Contenedor principal de la "Mesa de Trabajo".
Orquesta las sub-pestañas: Ver, Limpiar, Estadísticas, Guardar.
"""

def render_data_explorer(df: pd.DataFrame):
    """Sub-sección: Mostrar Datos y Filtros (Se queda aquí por ser simple visualización)"""
    st.markdown("### 🔍 Explorador de Datos")
    
    all_columns = df.columns.tolist()
    selected_cols = st.multiselect(
        "Columnas:", all_columns, default=all_columns,
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        rows_to_show = st.slider("Filas a mostrar:", 5, len(df), min(100, len(df)))
    
    if selected_cols:
        st.dataframe(df[selected_cols].head(rows_to_show), use_container_width=True, height=400)
        st.caption(f"Mostrando {rows_to_show} de {len(df)} filas.")

def render_statistics(df: pd.DataFrame):
    """Sub-sección: Estadísticas (Se queda aquí por ser simple lectura)"""
    st.markdown("### 📊 Rayos X de tus Datos")
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if numeric_cols:
        target_col = st.selectbox("Analizar columna numérica:", numeric_cols)
        series = df[target_col]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Promedio", f"{series.mean():.2f}")
        c2.metric("Mediana", f"{series.median():.2f}")
        c3.metric("Mínimo", f"{series.min()}")
        c4.metric("Máximo", f"{series.max()}")
        with st.expander("Ver Desviación Estándar y Cuartiles"):
            st.write(series.describe())
    else:
        st.info("No hay columnas numéricas para analizar.")

def render_save_area(df: pd.DataFrame, current_filename: str):
    """Sub-sección: Guardado (Usa writer.py)"""
    st.markdown("### 💾 Guardar y Exportar")
    c1, c2 = st.columns(2)
    
    with c1:
        st.info("📦 **Base de Datos Local (Parquet)**")
        if st.button("Guardar Snapshot", use_container_width=True):
            try:
                msg = writer.save_to_internal_db(df, current_filename)
                st.success(msg)
            except Exception as e:
                st.error(str(e))
                
    with c2:
        st.success("📤 **Exportar (Descargar)**")
        csv_data = writer.convert_to_csv(df)
        st.download_button(
            "Descargar CSV", data=csv_data, 
            file_name=f"procesado_{current_filename}.csv", mime="text/csv", 
            use_container_width=True
        )

def render_viewer_tab():
    """FUNCIÓN PRINCIPAL"""
    df = session.get_main_dataframe()
    filename = session.get_current_filename()
    
    if df is None:
        st.warning("⚠️ No hay datos cargados.")
        return

    st.title(f"🛠️ Mesa de Trabajo: {filename}")
    st.markdown("---")

    # --- DEFINICIÓN DE PESTAÑAS ---
    # Aquí integramos todo: Viewer, Cleaner, Stats, Saver
    tab_view, tab_clean, tab_stats, tab_save = st.tabs([
        "👁️ Ver Datos", 
        "🧼 Limpieza", 
        "📈 Estadísticas",
        "💾 Guardar"
    ])
    
    with tab_view:
        render_data_explorer(df)
        
    with tab_clean:
        # AQUÍ LLAMAMOS AL ARCHIVO EXTERNO tab_cleaner.py
        tab_cleaner.render(df)
        
    with tab_stats:
        render_statistics(df)
        
    with tab_save:
        render_save_area(df, filename)