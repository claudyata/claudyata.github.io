"""
app.py
================

Interfaz web para el sistema RAG de análisis de fútbol luxemburgués.

Título del Trabajo: Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva  
Nombre del Estudiante: Pedro José García Fernández  
Tutor/a de TF: Arturo González Martínez  
Profesor/a responsable: Susana Acedo  
Fecha:** Enero 2026 
Titulación o programa: Grado de Ciencia de Datos Aplicada  
Área de trabajo: Trabajo Final de Grado  
Idioma:** Castellano  
Palabras Clave:** Jetson AGX Orin - Ollama - RAG
"""

import streamlit as st

#from core.shared_resources import bootstrap
try:
    from core.config import *
    from core.dependencies import *
    from core.data_loaders import *
    from core.utils import *
    from core.features import *
except ImportError:
    from config import *
    from dependencies import *
    from data_loaders import *
    from utils import *
    from features import *

from tabs import (
    tab_busqueda_rag,
    tab_info,
    tab_gpu_monitor,
    tab_resumen,
    tab_dafo,
    tab_terminal
)

from default import get_custom_css
#from styles_fcbissen import get_custom_css
#from styles_fcbissen import (
#    get_custom_css,
#    get_fcbissen_header,
#    get_fcbissen_footer
#)

# ============================================================================
# CONFIGURACIÓN PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(get_custom_css(), unsafe_allow_html=True)


#st.set_page_config(page_title="Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva - FC Bissen", layout="wide")
#st.markdown(get_custom_css(), unsafe_allow_html=True)
#st.markdown(get_fcbissen_header(), unsafe_allow_html=True)




@st.cache_resource
def load_system():
    return bootstrap()

with st.spinner("🚀 Inicializando sistema RAG..."):
    rag_client, nlp_analyzer, storage, partidos = bootstrap()

ctx = {
    "rag_client": rag_client,
    "nlp_analyzer": nlp_analyzer,
    "storage": storage,
    "partidos": partidos,
}

# ============================================================================
# HEADER
# ============================================================================

#st.markdown('<div class="main-header">⚽ Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva </div>', unsafe_allow_html=True)


st.image("assets/logo_uoc.png", width=300)

stats = rag_client.get_stats()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Eventos Indexados", stats["total_eventos"])
with col2:
    st.metric("Partidos en ChromaDB", stats["total_partidos"])
with col3:
    st.metric("Partidos en PLATA", len(partidos))

# ============================================================================
# SIDEBAR - INFORMACIÓN DEL PROYECTO
# ============================================================================

# Logo del FC Bissen (local)
st.sidebar.image("assets/fcbissen_logo.png", width=120)

st.sidebar.header("⚽ Cl@udiata")
st.sidebar.markdown("*Modelos de Lenguaje en la Analítica Deportiva*")

st.sidebar.markdown("---")

# Info del TFG
st.sidebar.markdown("""
**Autor:** Pedro José García Fernández  
**Tutor:** Arturo González Martínez  
**Responsable:** Susana Acedo  

**Titulación:** Grado de Ciencia de Datos Aplicada  
**Universidad:** UOC  
**Fecha:** Enero 2026

**Stack Tecnológico:**  
🤖 Jetson AGX Orin  
🦙 Ollama (Qwen2.5:32B)  
🔍 RAG + ChromaDB  
📦 MinIO (Medallion)
""")

# ============================================================================
# TABS PRINCIPALES
# ============================================================================

tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🖥️ Terminal",
    "🔍 Búsqueda RAG",
    "📝 Resumen NLP",
    "📊 Análisis DAFO",
    "🖥️ Información GPU",
    "ℹ️ Información"
])

# ============================================================================
# TAB 0: Infraestructura y Setup
# ============================================================================

with tab0:
    tab_terminal.render(ctx)

# ============================================================================
# TAB 1: BÚSQUEDA RAG
# ============================================================================

with tab1:
    tab_busqueda_rag.render(ctx)

# ============================================================================
# TAB 2: RESUMEN NLP
# ============================================================================

with tab2:
    tab_resumen.render(ctx)

# ============================================================================
# TAB 3: ANÁLISIS DAFO
# ============================================================================

with tab3:
    tab_dafo.render(ctx)

# ============================================================================
# TAB 4: INFORMACIÓN GPU
# ============================================================================

with tab4:
    tab_gpu_monitor.render(ctx)
  
# ============================================================================
# TAB 5: INFORMACIÓN
# ============================================================================

with tab5:
    tab_info.render(ctx)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Sistema RAG - Cl@udiata | TFG Ciencia de Datos Aplicada | UOC 2025-2026"
    "</div>",
    unsafe_allow_html=True
)

#st.markdown(get_fcbissen_footer(), unsafe_allow_html=True)