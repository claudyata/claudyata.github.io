"""
Tab Resumen Demo - Panel de Estado y Guía de Demo

Panel resumen del entregable Cl@udiata:
- Identidad del proyecto
- Arquitectura (Medallion + RAG)
- Estado del sistema (Ollama, ChromaDB, MinIO)
- Métricas de demo (eventos/partidos, latencias orientativas, tok/s)
- Tabla MVP vs Extras
- Bloques "copiables" para explicar en la demo o indexar en RAG

Autor: Pedro José García Fernández
"""

import streamlit as st
import subprocess
from datetime import datetime


#from core.shared_resources import *

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

# ---------------------------------------------------------------------------
# Helpers (sin sudo)
# ---------------------------------------------------------------------------

def run_cmd(cmd: list[str], timeout=3) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out.strip()
    except Exception as e:
        return 1, str(e)

def systemctl_is_active(service: str) -> bool | None:
    code, out = run_cmd(["systemctl", "is-active", service])
    if code != 0 and not out:
        return None
    return out.strip() == "active"

def safe_stats(rag_client):
    try:
        return rag_client.get_stats() if rag_client else {"total_eventos": 0, "total_partidos": 0}
    except Exception:
        return {"total_eventos": 0, "total_partidos": 0}

def safe_list_matches(rag_client):
    try:
        return rag_client.list_available_matches() if rag_client else []
    except Exception:
        return []

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(ctx):
    """
    ctx esperado:
      ctx["rag_client"]
      ctx["nlp_analyzer"]
      ctx["storage"]
    """
    rag_client = ctx.get("rag_client") or get_rag_client()
    nlp_analyzer = ctx.get("nlp_analyzer") or get_nlp_analyzer()
    storage = ctx.get("storage") or get_storage()

    st.header("📌 Resumen de la Demo – Cl@udiata")

    # -----------------------------------------------------------------------
    # Barra superior: métricas rápidas
    # -----------------------------------------------------------------------
    stats = safe_stats(rag_client)
    partidos_plata = []
    try:
        partidos_plata = load_partidos_disponibles(nlp_analyzer) if nlp_analyzer else []
    except Exception:
        partidos_plata = []

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Eventos indexados", stats.get("total_eventos", 0))
    with col2:
        st.metric("Partidos en ChromaDB", stats.get("total_partidos", 0))
    with col3:
        st.metric("Partidos en PLATA", len(partidos_plata))
    with col4:
        st.metric("Última revisión", datetime.now().strftime("%H:%M:%S"))

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Sub-tabs internas
    # -----------------------------------------------------------------------
    t1, t3, t4, t8 = st.tabs([
        "ℹ️ Proyecto",
        "🔍 RAG",
        "🗄️ Indexación", 
        "🧪 MVP"
    ])

    # =======================================================================
    # TAB 1: Proyecto
    # =======================================================================
    with t1:
        st.subheader("🎯 Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva")

        st.markdown("""
**Título:** Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva  
**Autor:** Pedro José García Fernández  
**Tutor:** Arturo González Martínez  
**Responsable:** Susana Acedo  
**Titulación:** Grado de Ciencia de Datos Aplicada (UOC)  
**Enfoque:** IA generativa local para fútbol semiprofesional (Luxemburgo)  
**Palabras clave:** Jetson AGX Orin – Ollama – RAG  
""")

        st.info("""
En este TFG se plantea una pregunta de investigación y una solución fundamentada:

¿Es posible llevar capacidades de IA generativa avanzada al fútbol semi profesional, de una manera privada y sostenible a bajo coste y sin renunciar a la calidad exigida?

**La hipótesis**: Es técnicamente viable desplegar modelos de lenguaje (LLMs) 
de 7-32 mil millones de parámetros en infraestructura local de bajo consumo, 
con rendimiento suficiente para casos de uso reales.

La Solucion: Cl@ud-ia-data Agente IA Generativo para Análisis Deportivo
""")


       # st.info("""
#**Hipótesis del TFG (resumen):**  
#Es viable desplegar IA generativa avanzada (RAG + LLM) de forma local y sostenible
#en entornos con recursos limitados, manteniendo calidad y coste operativo bajo.
#""")

        st.markdown("### 🔎 Qué demuestra la demo")
        st.markdown("""
- Validación de infraestructura (Jetson + CUDA + Docker + Ollama + MinIO)  
- Búsqueda semántica sobre eventos de partidos (RAG)  
- Generación de resúmenes narrativos (NLP)  
- Análisis DAFO táctico por equipo (NLP)  
- Monitorización de GPU/energía para justificar sostenibilidad (Green AI)
""")

    # ========================================================================
    # INFORMACIÓN ADICIONAL
    # ========================================================================

    with t3:
        st.markdown("""
        ### 🔍 ¿Qué es RAG?
        
        **RAG (Retrieval-Augmented Generation)** es una técnica que combina:
        
        1. **Recuperación:** Búsqueda semántica en base de datos vectorial (ChromaDB)
        2. **Generación:** LLM (Qwen2.5) genera respuesta basada en documentos recuperados
        
        ### 🎯 Ventajas del Sistema
        
        - ✅ **Sin alucinaciones:** Solo usa información real de los partidos
        - ✅ **Contextual:** Respuestas específicas al partido seleccionado
        - ✅ **Transparente:** Muestra las fuentes utilizadas
        
        ### 🛠️ Tecnología
        
        **Vector Store:**
        - ChromaDB (base de datos vectorial)
        - E5-large embeddings (1024 dimensiones)
        - Búsqueda por similitud coseno
        
        **LLM:**
        - Modelo: Qwen2.5:32b (Ollama)
        - Hardware: Jetson AGX Orin 64GB (ejecución local)
        - Temperatura: 0.3 (respuestas más precisas)
        - Documentos por query: top-k=100 (configurable)


        **Pipeline:**
        1. Query → E5 embedding (1024-d vector)
        2. Búsqueda en ChromaDB (top-k=4 documentos)
        3. Contexto + Query → Qwen2.5
        4. Respuesta generada + fuentes
        """)

    with t4:
        st.markdown("""
        ### 🗄️ ¿Qué es la Indexación?
        
        **Proceso:**
        
        1. **Carga de Eventos** - Lee eventos desde PLATA (MinIO)
        2. **Traducción** - Traduce eventos al español (si necesario)
        3. **Embeddings** - Genera vectores semánticos (E5-large)
        4. **ChromaDB** - Almacena en base de datos vectorial
        5. **ORO Layer** - Guarda versión procesada
        
        **¿Por qué es necesario?**
        
        - Permite búsqueda semántica rápida
        - Recuperación eficiente de eventos (RAG)
        - Base para generación de resúmenes
        
        **Indexación On-Demand vs Batch:**
        
        | Aspecto | On-Demand | Batch (Gestión ChromaDB) |
        |---------|-----------|--------------------------|
        | **Velocidad** | ~30s | ~5-10 min (múltiples) |
        | **Uso** | 1 partido | Múltiples partidos |
        | **Cuándo** | Necesidad inmediata | Mantenimiento |
        
        **Almacenamiento:**
        
        - ChromaDB: `ación On-Demand vs Batchroma_db`
        - Colección: `football_events_2025_2026`
        - Persiste entre sesiones ✅
        """)

    # =======================================================================
    # TAB 8: MVP y Extras
    # =======================================================================
    with t8:
        st.subheader("🧪 Alcance del Proyecto: MVP y Extras")

        st.markdown("""
        Este bloque resume **qué partes del sistema forman el MVP evaluable del TFG**
        y cuáles se incluyen como **líneas de evolución**.
        """)

        # =========================
        # MVP
        # =========================
        mvp = [
            {
                "Tab": "Tab 0",
                "Funcionalidad": "Terminal / Validación INFRA",
                "Épicas": "INFRA · RAG",
                "Tareas": "INFRA-10 · 20 · 30 · 40 · RAG-10",
                "Qué demuestra": "Infraestructura real: Jetson, CUDA, Docker, Ollama, MinIO"
            },
            {
                "Tab": "Tab 1",
                "Funcionalidad": "Búsqueda RAG",
                "Épicas": "DATA · DWH · RAG",
                "Tareas": "DATA-10 · 20 · DWH-10 · 20 · 30 · RAG-20 · 40",
                "Qué demuestra": "Retrieval semántico + generación con fuentes reales"
            },
            {
                "Tab": "Tab 2",
                "Funcionalidad": "Resumen NLP",
                "Épicas": "NLP · RAG",
                "Tareas": "NLP-30 · DWH-20 · RAG-30",
                "Qué demuestra": "Resumen narrativo + streaming + métricas tok/s"
            },
            {
                "Tab": "Tab 3",
                "Funcionalidad": "Análisis DAFO",
                "Épicas": "NLP",
                "Tareas": "NLP-10",
                "Qué demuestra": "Análisis táctico estructurado por equipo"
            },
            {
                "Tab": "Tab 4",
                "Funcionalidad": "Monitorización GPU",
                "Épicas": "INFRA",
                "Tareas": "INFRA-50",
                "Qué demuestra": "Green AI: consumo, coste, logs y análisis post-mortem"
            },
        ]

        st.markdown("### ✅ MVP – Entregable evaluable del TFG")
        st.dataframe(mvp, use_container_width=True, hide_index=True)

        # =========================
        # EXTRAS
        # =========================
        extras = [
            {
                "Tab": "Tab 5",
                "Funcionalidad": "Actas y Documentos",
                "Épicas": "DATA",
                "Tareas": "DATA-30",
                "Notas": "Procesamiento PDF · Consideraciones GDPR"
            },
            {
                "Tab": "Tab 6",
                "Funcionalidad": "Vídeos",
                "Épicas": "DATA · NLP",
                "Tareas": "DATA-40 · NLP-20",
                "Notas": "Evolución futura · Multimodalidad"
            },
        ]

        st.markdown("### ➕ Extras – Evolución futura del sistema")
        st.dataframe(extras, use_container_width=True, hide_index=True)


    st.markdown("---")
    st.caption("Cl@udiata – Panel Resumen | Streamlit | Jetson AGX Orin | MinIO | ChromaDB | Ollama")

