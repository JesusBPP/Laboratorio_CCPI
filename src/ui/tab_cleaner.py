import streamlit as st
import pandas as pd
try:
    from src.engines import cleaner
    from utils import session
except ImportError:
    pass

"""
DESCRIPCIÓN DEL ARCHIVO: tab_cleaner.py
ROL: Interfaz gráfica avanzada.
ACTUALIZACIÓN:
- Inspección detallada de valores dentro de un grupo (<= 20 visual, > 20 mensaje).
"""

def render_health_sidebar(df: pd.DataFrame):
    stats = cleaner.get_data_health_summary(df)
    st.markdown("##### 🏥 Salud del Archivo")
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Filas Duplicadas", f"{stats['total_dupes']}", delta_color="inverse")
    kpi2.metric("Celdas Vacías", f"{stats['total_nulls']}", delta_color="inverse")
    st.divider()
    if not stats['null_cols_df'].empty:
        st.markdown("**Columnas con Nulos:**")
        st.dataframe(
            stats['null_cols_df'],
            use_container_width=True,
            hide_index=True,
            column_config={
                "%": st.column_config.ProgressColumn("%", format="%.1f%%", min_value=0, max_value=100)
            },
            height=200
        )
    else:
        st.success("✅ Sin columnas con valores nulos.")

def render_pattern_analysis(df: pd.DataFrame, selected_col: str):
    st.markdown(f"**🔍 Análisis de Patrones: `{selected_col}`**")
    with st.spinner("Escaneando grupos y detectando homogeneidad..."):
        patterns_df = cleaner.analyze_text_patterns(df, selected_col)
    
    st.dataframe(
        patterns_df.style.background_gradient(subset=['% del Total'], cmap="Blues"),
        use_container_width=True,
        hide_index=True,
        column_config={
            "¿Valor Único?": st.column_config.CheckboxColumn(
                "¿Valor Único?",
                help="Si está marcado, significa que TODOS los registros con este patrón tienen exactamente el mismo texto."
            )
        },
        height=250
    )
    return patterns_df

def render(df: pd.DataFrame):
    # --- SECCIÓN SUPERIOR ---
    col_main, col_info = st.columns([2, 1], gap="large")
    
    with col_main:
        st.markdown("#### 🕵️ Inspector de Columnas")
        target_col = st.selectbox("Selecciona una columna para analizar:", df.columns, index=0, key="inspector_col_select")
        # Tabla Principal
        patterns_df = render_pattern_analysis(df, target_col)

    with col_info:
        with st.container(border=True):
            render_health_sidebar(df)

    st.markdown("---")
    
    # --- SECCIÓN INFERIOR: OPERACIONES ---
    st.markdown("#### 🛠️ Herramientas de Corrección")
    
    tab_nulls, tab_format, tab_dupes = st.tabs([
        "Rellenar Nulos", 
        "Gestión de Patrones y Tipos", 
        "Eliminar Duplicados"
    ])
    
    # --- 1. RELLENAR NULOS ---
    with tab_nulls:
        st.caption(f"Operando en: **{target_col}**")
        
        with st.expander("ℹ️ ¿Qué considera el sistema como 'Nulo'?", expanded=False):
            st.markdown("""
            * `NaN` (Not a Number)
            * `None` (Vacío de Python)
            * `<NA>` (Nulo de Pandas/Arrow)
            """)
        
        nulos_en_col = df[target_col].isnull().sum()
        if nulos_en_col == 0:
            st.info(f"La columna '{target_col}' no tiene nulos técnicos.")
        else:
            c1, c2 = st.columns([1, 3])
            with c1:
                method = st.selectbox("Método:", ["Promedio (Media)", "Mediana", "Valor Cero", "Eliminar Renglones"])
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Aplicar Relleno", type="primary"):
                    try:
                        new_df = cleaner.impute_missing_values(df, target_col, method)
                        session.set_main_dataframe(new_df)
                        st.success(f"✅ Corregidos {nulos_en_col} registros.")
                        st.rerun()
                    except ValueError as ve:
                        st.error(f"⚠️ {ve}")

    # --- 2. GESTIÓN DE PATRONES ---
    with tab_format:
        st.caption(f"Operando en: **{target_col}**")
        
        type_mode = st.radio(
            "Acción:", 
            ["Cambio de Tipo Básico", "Homologación (Regex)", "Reemplazar Valor de Grupo"], 
            horizontal=True
        )
        
        # A. CAMBIO BÁSICO
        if type_mode == "Cambio de Tipo Básico":
            c1, c2 = st.columns([1, 3])
            with c1:
                new_type = st.selectbox("Nuevo Tipo:", ["Texto (String)", "Número Entero", "Número Decimal", "Fecha"])
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Convertir", type="primary"):
                    try:
                        new_df = cleaner.convert_column_type(df, target_col, new_type)
                        session.set_main_dataframe(new_df)
                        st.success(f"✅ Convertido a {new_type}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        # B. HOMOLOGACIÓN REGEX
        elif type_mode == "Homologación (Regex)":
            st.info("Usa esto para corregir formatos mezclados (ej. `12-34` a `12/34`).")
            pattern_opts = patterns_df.apply(lambda x: f"{x['Patrón']} (Ej: {x['Ejemplo']})", axis=1).tolist()
            selected_pat = st.selectbox("Formato a corregir:", pattern_opts)
            if selected_pat:
                example_origin = selected_pat.split("(Ej: ")[1][:-1]
                example_target = st.text_input("Corrección:", value=example_origin)
                if st.button("✨ Aplicar Homologación"):
                    try:
                        new_df = cleaner.standardize_by_example(df, target_col, example_origin, example_target)
                        session.set_main_dataframe(new_df)
                        st.success("✅ Homologación aplicada.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        # C. REEMPLAZO DE GRUPO (ACTUALIZADO CON INSPECCIÓN)
        elif type_mode == "Reemplazar Valor de Grupo":
            st.info("Usa esto para convertir textos como 'SIN ACTA' en Nulos o en otro valor.")
            
            # Selector de patrón
            pattern_opts_raw = patterns_df.apply(
                lambda x: f"{'✅' if x['¿Valor Único?'] else '⚠️'} {x['Patrón']} ({x['Cantidad']} filas)", 
                axis=1
            ).tolist()
            
            selected_pat_idx = st.selectbox("Selecciona el grupo a modificar:", range(len(pattern_opts_raw)), format_func=lambda i: pattern_opts_raw[i])
            
            # Recuperamos datos del patrón seleccionado
            target_pattern = patterns_df.iloc[selected_pat_idx]['Patrón']
            is_unique = patterns_df.iloc[selected_pat_idx]['¿Valor Único?']
            
            # --- NUEVA LÓGICA DE INSPECCIÓN ---
            with st.spinner("Analizando variaciones dentro del grupo..."):
                unique_vals = cleaner.get_unique_values_by_pattern(df, target_col, target_pattern)
                n_unique = len(unique_vals)
            
            st.markdown("---")
            st.markdown(f"**🔬 Inspección del Grupo:**")
            
            if n_unique <= 20:
                st.caption(f"Este grupo contiene **{n_unique}** valores distintos:")
                # Mostramos tabla de valores reales
                st.dataframe(pd.DataFrame(unique_vals, columns=["Valores Reales Encontrados"]), use_container_width=True, height=150)
            else:
                st.warning(f"⚠️ Este grupo es muy grande. Contiene **{n_unique}** valores distintos (demasiados para mostrar en lista).")
                st.caption(f"Ejemplos: {', '.join([str(v) for v in unique_vals[:5]])}...")
            
            st.markdown("---")
            st.markdown("**Acción:**")
            
            # Inputs de acción
            c1, c2 = st.columns(2)
            with c1:
                replace_action = st.selectbox("¿Qué quieres hacer?", ["Escribir nuevo valor", "Convertir a Nulo (Vacío)"])
            
            with c2:
                if replace_action == "Escribir nuevo valor":
                    new_val_input = st.text_input("Nuevo valor para todo el grupo:")
                    final_val = new_val_input
                else:
                    st.warning("Se borrará el contenido.")
                    final_val = "NULL_marker_internal"
            
            if st.button(f"🚨 Aplicar a {patterns_df.iloc[selected_pat_idx]['Cantidad']} filas"):
                try:
                    new_df = cleaner.replace_values_by_pattern(df, target_col, target_pattern, final_val)
                    session.set_main_dataframe(new_df)
                    st.success("✅ Reemplazo masivo completado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- 3. DUPLICADOS ---
    with tab_dupes:
        dupes = cleaner.count_duplicates(df)
        st.metric("Filas totalmente idénticas", dupes)
        if dupes > 0:
            if st.button("🗑️ Eliminar Todos", type="primary"):
                new_df = cleaner.remove_duplicates(df)
                session.set_main_dataframe(new_df)
                st.rerun()