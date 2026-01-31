import streamlit as st
import sys
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Laboratorio CCPI - Data Lab",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- IMPORTACIONES ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from utils.session import init_session_state
from src.ui.tab_upload import render_upload_tab
from src.ui.tab_viewer import render_viewer_tab
from src.ui.sidebar_manager import render_sidebar  # <<< AHORA SÍ IMPORTAMOS ESTO

def main():
    # 1. Inicializar Memoria
    init_session_state() 

    # 2. Renderizar Sidebar y obtener navegación
    # Ya no usamos 'with st.sidebar' aquí, delegamos todo al manager.
    menu_selection = render_sidebar() # <<< LLAMADA AL NUEVO MANAGER

    # Título Principal (Cuerpo de la página)
    # Podemos mover el título dentro de las tabs si quieres más limpieza, 
    # pero dejarlo aquí está bien como encabezado global.
    if menu_selection == "Subir Datos":
        st.title("📂 Ingesta de Datos")
    else:
        st.title("🛠️ Mesa de Trabajo")
    
    st.markdown("---")

    # 3. Router de Vistas
    if menu_selection == "Subir Datos":
        render_upload_tab()
        
    elif menu_selection == "Transformar":
        render_viewer_tab()

if __name__ == "__main__":
    main()