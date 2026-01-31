import streamlit as st
import pandas as pd
from utils import session

"""
DESCRIPCIÓN DEL ARCHIVO: tab_viewer.py
ROL: Módulo de visualización y transformación interactiva.
FUNCIONALIDAD:
- Opción 1: Explorador de Datos (Tabla + Filtros).
- Opción 2: Herramientas de Limpieza (Imputación, formatos).
- Opción 3: Estadísticas rápidas (Describe, Info).
"""

def render_data_explorer(df: pd.DataFrame):
    """Sub-sección: Mostrar Datos y Filtros"""
    st.markdown("### 🔍 Explorador de Datos")
    
    # Selector de Columnas
    all_columns = df.columns.tolist()
    selected_cols = st.multiselect(
        "Seleccionar columnas a visualizar:",
        all_columns,
        default=all_columns,
        help="Elimina columnas de la vista para enfocar tu análisis (no se borran de la memoria)."
    )
    
    # Filtro de Renglones (Slice)
    col1, col2 = st.columns(2)
    with col1:
        rows_to_show = st.slider("Cantidad de filas a mostrar:", 5, len(df), min(100, len(df)))
    
    if selected_cols:
        # Mostramos el dataframe con un estilo contenedor para que resalte en fondo blanco
        st.dataframe(
            df[selected_cols].head(rows_to_show),
            use_container_width=True,
            height=400
        )
        st.caption(f"Mostrando {rows_to_show} de {len(df)} filas.")
    else:
        st.warning("⚠️ Selecciona al menos una columna para visualizar.")

def render_cleaning_tools(df: pd.DataFrame):
    """Sub-sección: Limpieza y Transformación"""
    st.markdown("### 🧹 Limpieza de Datos")
    
    col_tools, col_action = st.columns([1, 2])
    
    with col_tools:
        st.markdown("#### Configuración")
        action_type = st.radio(
            "Acción a realizar:",
            ["Rellenar Nulos (Imputar)", "Cambiar Tipo de Dato", "Eliminar Duplicados"],
            key="clean_action_radio"
        )
    
    with col_action:
        st.markdown(f"#### Ejecutar: {action_type}")
        
        # --- LÓGICA: RELLENAR NULOS ---
        if action_type == "Rellenar Nulos (Imputar)":
            # Detectar columnas con nulos
            null_cols = df.columns[df.isnull().any()].tolist()
            
            if not null_cols:
                st.success("✨ ¡Tus datos están limpios! No hay valores nulos detectados.")
            else:
                target_col = st.selectbox("Columna con nulos:", null_cols)
                method = st.selectbox("Método de relleno:", ["Promedio (Media)", "Mediana", "Valor Cero", "Eliminar Renglones"])
                
                if st.button("Aplicar Corrección", type="primary"):
                    # NOTA: Aquí iría la llamada a engines/cleaner.py
                    # Por ahora hacemos una simulación visual
                    st.info(f"🚧 Conectando motor: Rellenando '{target_col}' usando '{method}'...")

        # --- LÓGICA: CAMBIAR TIPO ---
        elif action_type == "Cambiar Tipo de Dato":
            target_col = st.selectbox("Seleccionar Columna:", df.columns)
            current_type = df[target_col].dtype
            st.code(f"Tipo actual: {current_type}")
            
            new_type = st.selectbox("Nuevo Formato:", ["Texto (String)", "Número Entero", "Número Decimal", "Fecha"])
            
            if st.button("Convertir Formato"):
                st.info(f"🚧 Conectando motor: Convirtiendo '{target_col}' a {new_type}...")

def render_statistics(df: pd.DataFrame):
    """Sub-sección: Estadísticas sin alterar datos (Solo lectura)"""
    st.markdown("### 📊 Rayos X de tus Datos")
    
    # Seleccionamos solo columnas numéricas para estadísticas matemáticas
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if numeric_cols:
        target_col = st.selectbox("Analizar columna numérica:", numeric_cols)
        
        # Tarjetas de métricas (Diseño limpio)
        col1, col2, col3, col4 = st.columns(4)
        
        series = df[target_col]
        col1.metric("Promedio", f"{series.mean():.2f}")
        col2.metric("Mediana", f"{series.median():.2f}")
        col3.metric("Mínimo", f"{series.min()}")
        col4.metric("Máximo", f"{series.max()}")
        
        # Expander para ver detalles técnicos
        with st.expander("Ver Desviación Estándar y Cuartiles"):
            st.write(series.describe())
    else:
        st.info("No hay columnas numéricas para analizar estadísticamente.")

def render_viewer_tab():
    """Función Principal llamada por app.py"""
    
    # 1. Recuperar datos de la memoria
    df = session.get_main_dataframe()
    filename = session.get_current_filename()
    
    if df is None:
        # Estado Vacío (Empty State) bonito
        st.warning("⚠️ No hay datos cargados en memoria.")
        st.markdown("""
            Para comenzar:
            1. Ve a la pestaña **📂 Subir Datos**.
            2. Carga un archivo CSV o Excel.
            3. Regresa aquí para transformarlo.
        """)
        return

    # 2. Header de la sección
    st.title(f"🛠️ Mesa de Trabajo: {filename}")
    st.caption("Los cambios que hagas aquí se aplicarán a la versión en memoria.")
    st.markdown("---")

    # 3. Sidebar interno (Menú de herramientas)
    # Usamos tabs superiores para organizar las herramientas del laboratorio
    tab_view, tab_clean, tab_stats = st.tabs([
        "👁️ Mostrar Datos", 
        "🧼 Limpieza y Transformación", 
        "📈 Estadísticas (Solo Lectura)"
    ])
    
    with tab_view:
        render_data_explorer(df)
        
    with tab_clean:
        render_cleaning_tools(df)
        
    with tab_stats:
        render_statistics(df)