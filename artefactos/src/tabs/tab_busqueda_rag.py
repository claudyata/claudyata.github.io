"""
Tab de Búsqueda Semántica RAG
Permite hacer queries sobre eventos de partidos usando RAG
"""

import streamlit as st
import pandas as pd

#from core.shared_resources import cargar_equipos_csv, IDIOMAS, indexar_partido_on_demand, ejecutar_query_sugerida

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


def render(ctx):
    
    """Renderiza el tab de búsqueda RAG"""

    st.header("🔍 Búsqueda Semántica RAG")
    
    st.markdown("""
    Realiza consultas en lenguaje natural sobre eventos de partidos de fútbol.
    El sistema utiliza **RAG (Retrieval-Augmented Generation)** para encontrar 
    información relevante y generar respuestas contextualizadas con Qwen2.5.
    """)
    
    # ========================================================================
    # INICIALIZACIÓN
    # ========================================================================
    
    rag_client = ctx["rag_client"]
    nlp_analyzer = ctx["nlp_analyzer"]
    storage = ctx["storage"]

    
    # ========================================================================
    # CARGAR PARTIDOS INDEXADOS
    # ========================================================================
    
    partidos_indexados = []
    try:
        if rag_client:
            partidos_indexados = rag_client.list_available_matches()

    except Exception as e:
        st.warning(f"⚠️ No se pudo verificar ChromaDB: {e}")
    
    # ========================================================================
    # CARGAR EQUIPOS
    # ========================================================================
       
    df_equipos = cargar_equipos_csv(storage)
    
    if df_equipos is None:
        st.error("❌ No se pudo cargar el CSV de equipos")
        st.stop()
    
    # ========================================================================
    # SELECTOR DE JORNADA Y PARTIDO
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📅 Seleccionar Partido")
    
    jornadas_disponibles = sorted(df_equipos['jornada'].unique())
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        jornada_seleccionada = st.selectbox(
            "Jornada:",
            options=jornadas_disponibles,
            format_func=lambda x: f"Jornada {x}"
        )
    
    with col2:
        partidos_jornada = df_equipos[df_equipos['jornada'] == jornada_seleccionada]
        st.info(f"📊 {len(partidos_jornada)} partidos en Jornada {jornada_seleccionada}")
    
    # Selector de partido
    st.markdown("**Partido:**")
    
    partidos_opciones = {}
    for idx, row in partidos_jornada.iterrows():
        # Indicar si está indexado
        indexado = row['match_id'] in partidos_indexados
        indexado_icon = "✅" if indexado else "⚠️"
        label = f"{indexado_icon} Partido {row['partido']}: {row['equipo_local']} vs {row['equipo_visitante']}"
        
        partidos_opciones[label] = {
            'match_id': row['match_id'],
            'jornada': row['jornada'],
            'partido': row['partido'],
            'equipo_local': row['equipo_local'],
            'equipo_visitante': row['equipo_visitante'],
            'indexado': indexado
        }
    
    selected_partido_label = st.selectbox(
        "Seleccionar partido:",
        options=list(partidos_opciones.keys())
    )
    
    partido_info = partidos_opciones[selected_partido_label]
    
    # Mostrar info del partido seleccionado
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Match ID", partido_info['match_id'])
    
    with col2:
        st.metric("Jornada", partido_info['jornada'])
    
    with col3:
        st.metric("Partido", partido_info['partido'])
    
    with col4:
        if partido_info['indexado']:
            st.metric("Estado", "✅ Indexado")
        else:
            st.metric("Estado", "⚠️ No indexado")
    
    # ========================================================================
    # VERIFICAR SI PARTIDO ESTÁ INDEXADO
    # ========================================================================
    
    if not partido_info['indexado']:
        st.warning(f"⚠️ El partido **{partido_info['equipo_local']} vs {partido_info['equipo_visitante']}** no está indexado en ChromaDB")
        
        st.markdown("---")
        st.markdown("### 🔧 Indexación Requerida")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("""
            **Para generar el resumen, este partido debe estar indexado.**
            
            📊 **Proceso de indexación:**
            1. Carga eventos desde PLATA (MinIO)
            2. Traduce al español si es necesario
            3. Genera embeddings vectoriales (E5-large)
            4. Almacena en ChromaDB
            
            ⏱️ **Tiempo estimado:** ~30 segundos
            """)
        
        with col2:
            if st.button(
                "🚀 Indexar Ahora",
                type="primary",
                key="indexar_partido_btn",
                help="Indexa este partido específico en ChromaDB"
            ):
                # Contenedores para UI
                progress_container = st.empty()
                status_container = st.empty()
                result_container = st.empty()
                
                # Callback para actualizar UI
                def update_ui(step, progress):
                    with progress_container:
                        st.progress(progress / 100)
                    with status_container:
                        st.text(step)
                
                # Ejecutar indexación (PASAR nlp_analyzer)
                exito, mensaje, num_eventos = indexar_partido_on_demand(
                    partido_info['match_id'],
                    nlp_analyzer,
                    idioma_traduccion='en',
                    progress_callback=update_ui
                )
                
                # Mostrar resultado
                progress_container.empty()
                status_container.empty()
                
                if exito:
                    with result_container:
                        st.success(f"✅ {mensaje}")
                        st.info(f"📊 {num_eventos} eventos indexados")
                    
                    st.balloons()
                    
                    # Limpiar cache RAG client para que recargue índice
                    st.cache_resource.clear()
                    
                    st.success("🔄 Recargando en 2 segundos...")
                    import time
                    time.sleep(2)
                    st.rerun()
                
                else:
                    with result_container:
                        st.error(f"❌ Error en indexación")
                        with st.expander("Ver Detalles"):
                            st.code(mensaje)
        
        # No permitir generar resumen sin indexar
        st.markdown("---")
        st.info("💡 **Acción requerida:** Indexa el partido usando el botón arriba para continuar")
        st.stop()
    
    # ========================================================================
    # BÚSQUEDA RAG
    # ========================================================================

    st.markdown("---")
    st.markdown("### 🔍 Realizar Consulta")
    modo_streaming = True
    idioma_seleccionado = 'es'

    
    match_id = partido_info['match_id']
    
    # Input de query
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query_input = st.text_input(
            "Pregunta:",
            placeholder="¿Hubo goles? ¿Quién destacó? ¿Cómo fue el primer tiempo?",
            key="query_input"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        buscar_btn = st.button("🔍 Buscar", key="buscar_rag", type="primary")
    
    # ========================================================================
    # EJECUTAR BÚSQUEDA
    # ========================================================================
    
    if buscar_btn and query_input:
        
        if modo_streaming:
            # ================================================================
            # MODO STREAMING
            # ================================================================
            
            # Contenedores para actualización en tiempo real
            status_container = st.empty()
            respuesta_container = st.empty()
            metrics_container = st.empty()
            fuentes_container = st.empty()
            
            try:
                # Iniciar búsqueda con streaming
                status_container.info(f"🤖 Consultando a Qwen2.5 en {IDIOMAS[idioma_seleccionado]['nombre']}...")
                
                resultado_stream = rag_client.query_stream(
                    query_input,
                    match_id=match_id,
                    language=idioma_seleccionado,
                    verbose=False
                )
                
                respuesta_parcial = ""
                fuentes = []
                tokens_count = 0
                
                # Procesar stream
                for chunk in resultado_stream:
                    
                    if chunk['type'] == 'sources':
                        # Guardar fuentes
                        fuentes = chunk['documents']
                        status_container.success(f"📚 {len(fuentes)} fuentes recuperadas, generando respuesta...")
                    
                    elif chunk['type'] == 'token':
                        # Actualizar respuesta en tiempo real
                        respuesta_parcial = chunk['answer_partial']
                        tokens_count = chunk.get('tokens', 0)
                        
                        # Crear contenedor para toda la sección
                        with respuesta_container.container():
                            st.markdown(f"### 💬 Respuesta ({IDIOMAS[idioma_seleccionado]['flag']} {IDIOMAS[idioma_seleccionado]['nombre']})")
                            st.markdown(
                                f'<div class="resultado-box">{respuesta_parcial}<span style="animation: blink 1s infinite;">▌</span></div>',
                                unsafe_allow_html=True
                            )

                        # Métricas en tiempo real
                        with metrics_container.container():
                            col1, col2, col3 = st.columns(3)
                            
                            palabras = len(respuesta_parcial.split())
                            caracteres = len(respuesta_parcial)
                            
                            with col1:
                                st.metric("Palabras", palabras)
                            with col2:
                                st.metric("Caracteres", caracteres)
                            with col3:
                                st.metric("Tokens", tokens_count)
                    
                    elif chunk['type'] == 'complete':
                        # Finalizado
                        respuesta_final = chunk['answer']
                        
                        status_container.success("✅ Respuesta completada")
                        
                        # Mostrar respuesta final (sin cursor)
                
                        with respuesta_container.container():
                            st.markdown(f"### 💬 Respuesta ({IDIOMAS[idioma_seleccionado]['flag']} {IDIOMAS[idioma_seleccionado]['nombre']})")
                            #st.markdown(
                            #    f'<div class="resultado-box">{respuesta_final}</div>',
                            #    unsafe_allow_html=True
                            #)

                            # Mostrar en text_area con scroll automático
                            st.text_area(
                                label="Respuesta completa",
                                value=respuesta_final,
                                height=600,  # Ajusta altura
                                disabled=True,
                                label_visibility="collapsed"
                            )

                # Mostrar fuentes
                if fuentes:
                    with fuentes_container.container():
                        st.markdown("---")
                        
                        with st.expander(f"📚 Ver {len(fuentes)} fuentes utilizadas"):
                            for i, doc in enumerate(fuentes, 1):
                                st.markdown(f"""
                                <div class="fuente-box">
                                    <strong>Fuente {i}:</strong> Match {doc['match_id']} | 
                                    Min {doc['minuto']} | {doc['equipo']}<br>
                                    <em>{doc['texto'][:300]}...</em>
                                </div>
                                """, unsafe_allow_html=True)
                
                # Estadísticas finales
                st.markdown("---")
                st.markdown("#### 📊 Estadísticas de la Consulta")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Fuentes", len(fuentes))
                
                with col2:
                    palabras_respuesta = len(respuesta_final.split())
                    st.metric("Palabras", palabras_respuesta)
                
                with col3:
                    caracteres_respuesta = len(respuesta_final)
                    st.metric("Caracteres", caracteres_respuesta)
                
                with col4:
                    st.metric("Idioma", f"{IDIOMAS[idioma_seleccionado]['flag']} {IDIOMAS[idioma_seleccionado]['codigo_iso'].upper()}")
            
            except Exception as e:
                status_container.error(f"❌ Error en la consulta: {e}")
                import traceback
                with st.expander("Ver Traceback"):
                    st.code(traceback.format_exc())
        
        else:
            # ================================================================
            # MODO NORMAL (SIN STREAMING)
            # ================================================================
            
            with st.spinner(f'🤖 Consultando a Qwen2.5 en {IDIOMAS[idioma_seleccionado]["nombre"]}...'):
                try:
                    resultado = rag_client.query(
                        query_input,
                        match_id=match_id,
                        language=idioma_seleccionado,
                        verbose=False
                    )
                    
                    # Mostrar respuesta
                    st.markdown("---")
                    st.markdown(f"### 💬 Respuesta ({IDIOMAS[idioma_seleccionado]['flag']} {IDIOMAS[idioma_seleccionado]['nombre']})")
                    
                    st.markdown(
                        f'<div class="resultado-box">{resultado["answer"]}</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Mostrar fuentes
                    if resultado.get('source_documents'):
                        st.markdown("---")
                        
                        with st.expander(f"📚 Ver {len(resultado['source_documents'])} fuentes utilizadas"):
                            for i, doc in enumerate(resultado['source_documents'], 1):
                                st.markdown(f"""
                                <div class="fuente-box">
                                    <strong>Fuente {i}:</strong> Match {doc['match_id']} | 
                                    Min {doc['minuto']} | {doc['equipo']}<br>
                                    <em>{doc['texto'][:300]}...</em>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    # Estadísticas
                    st.markdown("---")
                    st.markdown("#### 📊 Estadísticas de la Consulta")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Fuentes", len(resultado.get('source_documents', [])))
                    
                    with col2:
                        palabras_respuesta = len(resultado['answer'].split())
                        st.metric("Palabras", palabras_respuesta)
                    
                    with col3:
                        caracteres_respuesta = len(resultado['answer'])
                        st.metric("Caracteres", caracteres_respuesta)
                    
                    with col4:
                        st.metric("Idioma", f"{IDIOMAS[idioma_seleccionado]['flag']} {idioma_seleccionado.upper()}")
                
                except Exception as e:
                    st.error(f"❌ Error en la consulta: {e}")
                    import traceback
                    with st.expander("Ver Traceback"):
                        st.code(traceback.format_exc())

    
    # ========================================================================
    # QUERIES SUGERIDAS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 💡 Consultas Sugeridas")
    
    st.info("Haz clic en cualquiera de estas consultas predefinidas para probar el sistema")
    
    col1, col2, col3 = st.columns(3)
    
    # Query 1: Goles
    with col1:
        if st.button("⚽ ¿Hubo goles?", key="query_goles", use_container_width=True):
            st.markdown("---")
            st.markdown("### 💬 Respuesta: ¿Hubo goles?")
            ejecutar_query_sugerida(
                "¿Hubo goles en este partido? ¿Quién marcó?",
                match_id,
                idioma_seleccionado,
                modo_streaming,
                rag_client
            )
    
    # Query 2: Jugadores destacados
    with col2:
        if st.button("⭐ ¿Quién destacó?", key="query_destacado", use_container_width=True):
            st.markdown("---")
            st.markdown("### 💬 Respuesta: ¿Quién destacó?")
            ejecutar_query_sugerida(
                "¿Qué jugador o jugadores destacaron en este partido?",
                match_id,
                idioma_seleccionado,
                modo_streaming,
                rag_client
            )
    
    # Query 3: Tarjetas
    with col3:
        if st.button("🟨 ¿Tarjetas?", key="query_tarjetas", use_container_width=True):
            st.markdown("---")
            st.markdown("### 💬 Respuesta: ¿Tarjetas?")
            ejecutar_query_sugerida(
                "¿Hubo tarjetas amarillas o rojas en este partido?",
                match_id,
                idioma_seleccionado,
                modo_streaming,
                rag_client
            )

    # ========================================================================
    # INFORMACIÓN ADICIONAL
    # ========================================================================
    
    st.markdown("---")
    with st.expander("ℹ️ Información sobre Búsqueda RAG"):
        
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
        - Modelo: Qwen2.5:32b
        - Hardware: Jetson AGX Orin 64GB
        - Temperatura: 0.3 (respuestas precisas)
        
        **LLM:**
        - Modelo: Qwen2.5:32b (Ollama)
        - Hardware: Jetson AGX Orin 64GB (ejecución local)
        - Temperatura: 0.3 (respuestas más precisas)
        - Documentos por query: top-k=4 (configurable)


        **Pipeline:**
        1. Query → E5 embedding (1024-d vector)
        2. Búsqueda en ChromaDB (top-k=4 documentos)
        3. Contexto + Query → Qwen2.5
        4. Respuesta generada + fuentes
        """)