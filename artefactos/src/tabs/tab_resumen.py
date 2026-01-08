"""
Tab de Resumen Narrativo
Genera resúmenes periodísticos de partidos usando Qwen2.5
"""

import streamlit as st
import pandas as pd

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

def render(ctx):
    """Renderiza el tab de resumen narrativo"""
    
    st.header("📝 Resumen Narrativo del Partido")
    
    st.markdown("""
    Genera resúmenes narrativos estilo **crónica periodística** de partidos 
    usando Qwen2.5. Los resúmenes tienen 300-400 palabras y estructura profesional.
    """)
    
    # ========================================================================
    # INICIALIZACIÓN
    # ========================================================================
    
    nlp_analyzer = ctx["nlp_analyzer"]
    storage = ctx["storage"]
    
    # ========================================================================
    # CONFIGURACIÓN DE IDIOMA
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 🌍 Configuración de Idioma")

    col1, col2 = st.columns([2, 3])
    
    with col1:
        idioma_seleccionado = st.selectbox(
            "Idioma del resumen:",
            options=list(IDIOMAS.keys()),
            format_func=lambda x: f"{IDIOMAS[x]['flag']} {IDIOMAS[x]['nombre']}",
            index=0,  # Español por defecto
            key="idioma_resumen",
            help="El resumen se generará en el idioma seleccionado. Eventos originales en luxemburgués indexados con E5-large (óptimo para multilingüe)."
        )
    
    with col2:
        st.info(f"""
        **Idioma seleccionado:** {IDIOMAS[idioma_seleccionado]['flag']} {IDIOMAS[idioma_seleccionado]['nombre']}
        
        **Modelo embeddings:** E5-large (multilingual)
        
        **Soporte:** lb→es, lb→pt, lb→en, lb→de, lb→fr
        """)

    
    # ========================================================================
    # CARGAR PARTIDOS INDEXADOS
    # ========================================================================
    
    partidos_indexados = []
    try:
        if nlp_analyzer.rag_client:
            partidos_indexados = nlp_analyzer.rag_client.list_available_matches()

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
            format_func=lambda x: f"Jornada {x}",
            key="jornada_resumen"
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
        options=list(partidos_opciones.keys()),
        key="partido_resumen"
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
                #help="Indexa este partido específico en ChromaDB"
                help="Indexa este partido en inglés (vectores) para mejor calidad de embeddings"
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
                
                # Ejecutar indexación
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
    # GENERAR RESUMEN (Solo si está indexado)
    # ========================================================================
    
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        generar_resumen_btn = st.button(
            "📝 Generar Resumen",
            type="primary",
            key="gen_resumen"
        )
    
    with col2:
        modo_streaming = st.checkbox(
            "🌊 Streaming",
            value=True,
            help="Ver el resumen generándose en tiempo real",
            key="modo_streaming"
        )
    
    if generar_resumen_btn:
        
        match_id = partido_info['match_id']
        equipo_local = partido_info['equipo_local']
        equipo_visitante = partido_info['equipo_visitante']
        jornada = partido_info['jornada']
        
        if modo_streaming:
            # ================================================================
            # MODO STREAMING
            # ================================================================
            
            # Contenedores
            header_container = st.empty()
            resumen_container = st.empty()
            metrics_container = st.empty()
            validacion_container = st.empty()
            download_container = st.empty()
            
            try:
                # Iniciar generación con streaming
                stream_gen = nlp_analyzer.generar_resumen_partido(
                    match_id, 
                    verbose=False, 
                    stream=True,
                    idioma=idioma_seleccionado
                )
                
                # Verificar si hubo error
                if isinstance(stream_gen, dict):
                    if 'error' in stream_gen:
                        st.error(f"❌ {stream_gen['error']}")
                        st.info("💡 Esto no debería pasar ya que verificamos indexación antes")
                        st.stop()
                
                metadata = None
                resumen_completo = ""
                tokens_generados = 0
                
                # Procesar stream
                for chunk in stream_gen:
                    
                    if not isinstance(chunk, dict):
                        st.warning(f"⚠️ Chunk inesperado: {type(chunk)}")
                        continue
                    
                    if chunk.get('type') == 'metadata':

                        # Mostrar header
                        metadata = chunk
                        idioma_flag = IDIOMAS.get(chunk['idioma'], {}).get('flag', '🌍')
                        
                        header_container.markdown(f"""
                        ### 🏟️ {equipo_local} vs {equipo_visitante}
                        **Jornada {jornada}** | Eventos: {chunk['num_eventos']} | {idioma_flag} Idioma: {IDIOMAS[chunk['idioma']]['nombre']} | 🌊 Generando...
                        """)


                        #header_container.markdown(f"""
                        ### 🏟️ {equipo_local} vs {equipo_visitante}
                        #**Jornada {jornada}** | Eventos analizados: {chunk['num_eventos']} | 🌊 Generando...
                        #""")
                        
                        resumen_container.markdown("---")
                                       
                    elif chunk.get('type') == 'token':
                        # Actualizar resumen en tiempo real
                        resumen_completo = chunk['resumen_parcial']
                        tokens_generados = chunk['tokens_generados']
                        tokens_por_segundo = chunk.get('tokens_por_segundo', 0)
                        
                        # Mostrar con cursor parpadeante
                        resumen_container.markdown(
                            f'<div class="resultado-box">{resumen_completo}<span style="animation: blink 1s infinite;">▌</span></div>',
                            unsafe_allow_html=True
                        )
                        
                        # Métricas en tiempo real
                        palabras = len(resumen_completo.split())
                        caracteres = len(resumen_completo)
                        
                        with metrics_container.container():
                            st.markdown("#### 📊 Métricas en Tiempo Real")
                            col1, col2, col3, col4 = st.columns(4)  # ← Cambiar a 4 columnas
                            
                            with col1:
                                st.metric("Palabras", palabras)
                            
                            with col2:
                                st.metric("Caracteres", caracteres)
                            
                            with col3:
                                st.metric("Tokens", tokens_generados)
                            
                            with col4:
                                if tokens_por_segundo >= 20:
                                    delta_color = "normal"
                                    emoji = "🚀"
                                elif tokens_por_segundo >= 10:
                                    delta_color = "normal"
                                    emoji = "⚡"
                                else:
                                    delta_color = "normal"
                                    emoji = "🐌"
                                
                                st.metric(
                                    f"{emoji} Tok/s", 
                                    f"{tokens_por_segundo:.1f}",
                                    delta=None,
                                    help="Tokens generados por segundo (velocidad de generación)"
                                )
                
                    elif chunk.get('type') == 'final':
                        # Finalizar
                        resumen_completo = chunk['resumen']
                        tokens_generados = chunk['tokens_generados']
                        tokens_por_segundo_final = chunk.get('tokens_por_segundo', 0) 
                        tiempo_total = chunk.get('tiempo_total', 0)
                        tiempo_generacion = chunk.get('tiempo_generacion', 0)





                # Header final
                if metadata:
                    header_container.markdown(f"""
                    ### 🏟️ {equipo_local} vs {equipo_visitante}
                    **Jornada {jornada}** | Eventos: {metadata['num_eventos']} | ✅ Completado en {tiempo_total:.1f}s
                    """)

                # Resumen final (sin cursor)
                resumen_container.markdown(
                    f'<div class="resultado-box">{resumen_completo}</div>',
                    unsafe_allow_html=True
                )

                # Métricas finales (actualizadas)
                with metrics_container.container():
                    st.markdown("---")
                    st.markdown("#### 📊 Métricas Finales")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    palabras = len(resumen_completo.split())
                    caracteres = len(resumen_completo)
                    
                    with col1:
                        st.metric("Palabras", palabras)
                    
                    with col2:
                        st.metric("Caracteres", caracteres)
                    
                    with col3:
                        st.metric("Tokens", tokens_generados)
                    
                    with col4:
                        # Performance según velocidad
                        if tokens_por_segundo_final >= 15:
                            performance = "🚀 Excelente"
                        elif tokens_por_segundo_final >= 8:
                            performance = "⚡ Muy Bueno"
                        elif tokens_por_segundo_final >= 4:
                            performance = "✅ Bueno"
                        else:
                            performance = "🐌 Lento"
                        
                        st.metric(
                            "Velocidad", 
                            f"{tokens_por_segundo_final:.1f} tok/s",
                            delta=performance,
                            help=f"Tiempo total: {tiempo_total:.1f}s | Generación: {tiempo_generacion:.1f}s"
                        )
                
                # Descarga
                with download_container.container():
                    st.markdown("---")
                    
                    #st.download_button(
                    #    label="💾 Descargar Resumen",
                    #    data=resumen_completo,
                    #    file_name=f"resumen_{match_id}_{equipo_local}_vs_{equipo_visitante}.txt",
                    #    mime="text/plain"
                    #)

                    st.download_button(
                        label="💾 Descargar Resumen",
                        data=resumen_completo,
                        file_name=f"resumen_{match_id}_{equipo_local}_vs_{equipo_visitante}_{idioma_seleccionado}.txt",
                        mime="text/plain"
                    )
            
            except Exception as e:
                st.error(f"❌ Error generando resumen: {e}")
                import traceback
                with st.expander("Ver Traceback"):
                    st.code(traceback.format_exc())
        
        else:
            # Modo normal (sin streaming) - similar pero sin actualizaciones en tiempo real
            with st.spinner('🤖 Generando resumen...'):
                # ... código modo normal ...
                pass
    
    else:
        # Mensaje inicial
        st.info("""
        💡 **Cómo funciona:**
        
        1. ✅ Selecciona **jornada** y **partido**
        2. 🚀 Si no está indexado, usa **"Indexar Ahora"** (~30s)
        3. 🌊 Activa **Streaming** para ver generación en tiempo real
        4. 📝 Click en **"Generar Resumen"**
        
        ⏱️ **Tiempos:** Indexación ~30s | Generación ~40s
        """)
    
    # ========================================================================
    # INFORMACIÓN ADICIONAL
    # ========================================================================
    
    st.markdown("---")
    with st.expander("📝 Información sobre Resumen NLP"):

        st.markdown("""
        ### 📝 Generación de Resúmenes
        
        **Tecnología:**
        - Modelo: Qwen2.5:32b (LLM multilingüe)
        - Temperatura: 0.7 (creatividad moderada)
        - RAG: Recuperación desde ChromaDB
        
        **Proceso:**
        1. Recupera eventos del partido (ChromaDB)
        2. Construye contexto completo
        3. Prompt optimizado para crónicas deportivas
        4. Generación con restricciones (sin alucinaciones)
        5. Validación de calidad
        
        **Calidad:**
        - ✅ 300-400 palabras (rango óptimo)
        - ✅ Estructura narrativa (intro/desarrollo/conclusión)
        - ✅ 0% alucinaciones (solo eventos reales)
        - ✅ Tono profesional
        
        **Modos:**
        - **Normal:** Resumen completo al final
        - **Streaming:** Generación en tiempo real (recomendado)
        """)