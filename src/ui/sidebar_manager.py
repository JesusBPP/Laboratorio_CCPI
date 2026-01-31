import streamlit as st
from utils import session

"""
DESCRIPCIÓN DEL ARCHIVO: sidebar_manager.py

ROL:
Actúa como el panel de control lateral persistente. No solo maneja la navegación,
sino que proporciona contexto global al usuario sobre el estado de la sesión.

CARACTERÍSTICAS:
- Navegación Principal (Radio Button estilizado).
- Monitor de Estado: Muestra qué archivo está en memoria RAM.
- Botón de Reset: Permite limpiar la sesión (session.clear_session).
- Footer: Información de versión y créditos.
"""

def render_project_info():
    """Muestra el logo y título del proyecto."""
    # Usamos columnas para centrar o dar estilo
    st.markdown("### 🧬 Data Lab")
    st.caption("Laboratorio de Limpieza y Transformación CCPI")
    st.markdown("---")

def render_status_monitor():
    """
    Panel Dinámico: Cambia según si hay datos cargados o no.
    Conecta con session.py para leer el estado.
    """
    st.markdown("#### 📡 Estado de Memoria")
    
    if session.is_data_loaded():
        # CASO 1: Hay datos cargados
        filename = session.get_current_filename()
        df = session.get_main_dataframe()
        
        # Tarjeta de información activa (Usando success para verde suave)
        st.success(f"📂 Archivo Activo:\n**{filename}**")
        
        # Métricas compactas en el sidebar
        c1, c2 = st.columns(2)
        c1.metric("Filas", f"{df.shape[0]/1000:.1f}k") # Muestra miles (ej. 1.5k)
        c2.metric("Cols", df.shape[1])
        
        # Botón de Pánico (Reset)
        st.markdown("---")
        if st.button("🗑️ Liberar Memoria", type="secondary", help="Borra los datos actuales y reinicia."):
            session.clear_session()
            st.rerun() # Recarga la app inmediatamente
            
    else:
        # CASO 2: No hay datos (Modo espera)
        st.info("☁️ Memoria Vacía")
        st.caption("Ve a 'Subir Datos' para comenzar.")

def render_navigation():
    """Renderiza el menú de selección."""
    st.markdown("#### 🧭 Menú")
    
    # Definimos las opciones con iconos
    options = {
        "Subir Datos": "📂 Ingesta de Datos",
        "Transformar": "🛠️ Mesa de Trabajo"
    }
    
    selection = st.radio(
        "Navegación",
        options=list(options.keys()),
        format_func=lambda x: options[x], # Muestra el texto bonito con iconos
        label_visibility="collapsed"
    )
    
    return selection

def render_footer():
    """Pie de página del sidebar."""
    st.markdown("---")
    st.caption("🔒 **Modo Local:**\nApache Arrow Engine Active")
    st.caption("v1.0.2 | CCPI Dev Team")

def render_sidebar():
    """
    FUNCIÓN PRINCIPAL
    Llamada por app.py para construir toda la barra lateral.
    Retorna: La opción seleccionada por el usuario (str).
    """
    with st.sidebar:
        # 1. Identidad del Proyecto
        render_project_info()
        
        # 2. Navegación
        selection = render_navigation()
        
        st.markdown("---")
        
        # 3. Monitor de Estado (Dinámico)
        render_status_monitor()
        
        # 4. Footer
        render_footer()
        
    return selection