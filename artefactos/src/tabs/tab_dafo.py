"""
Tab de ANÁLISIS DAFO
Genera análisis DAFO táctico del partido usando Qwen2.5 + RAG

Autor: Pedro José García Fernández
"""

import streamlit as st
import pandas as pd
#from core.shared_resources import cargar_equipos_csv

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

import time

# -------------------------------------------------------------------
# Helpers UI
# -------------------------------------------------------------------

def ejecutar_dafo_streaming(nlp_analyzer, match_id, equipo, eventos=None, titulo_equipo="Equipo"):
    """
    Ejecuta analizar_dafo_equipo en modo streaming y lo pinta en Streamlit.
    Métricas: palabras, caracteres, tokens, tok/s
    """
    status = st.empty()
    respuesta_box = st.empty()
    metrics = st.empty()

    respuesta_parcial = ""
    tokens = 0
    dafo_final = None

    t_start = None  # inicio de generación (para tok/s)
    tok_s = 0.0

    try:
        gen = nlp_analyzer.analizar_dafo_equipo(
            match_id=match_id,
            equipo=equipo,
            eventos=eventos,
            verbose=False,
            stream=True
        )

        for chunk in gen:
            ctype = chunk.get("type")

            if ctype == "metadata":
                # Iniciar temporizador aquí (o en primer token)
                t_start = time.time()
                status.info(
                    f"🔍 Analizando {titulo_equipo} | Eventos: {chunk.get('num_eventos','?')} | Generando DAFO..."
                )

            elif ctype == "token":
                if t_start is None:
                    t_start = time.time()

                # Preferir el texto parcial si el backend lo ofrece
                if "respuesta_parcial" in chunk:
                    respuesta_parcial = chunk["respuesta_parcial"]
                else:
                    # fallback: concatenar token si viene suelto
                    token_txt = chunk.get("token", "")
                    respuesta_parcial += token_txt

                # Tokens: si backend lo manda, úsalo
                if "tokens_generados" in chunk:
                    tokens = chunk["tokens_generados"]
                else:
                    # fallback: aproximación (no ideal)
                    tokens = tokens + 1

                # tok/s: usar el backend si existe, si no calcular
                if "tokens_por_segundo" in chunk and chunk["tokens_por_segundo"] is not None:
                    tok_s = float(chunk["tokens_por_segundo"])
                else:
                    elapsed = max(0.001, time.time() - t_start)
                    tok_s = tokens / elapsed

                # Render streaming
                respuesta_box.markdown(
                    f'<div class="resultado-box">{respuesta_parcial}<span style="animation: blink 1s infinite;">▌</span></div>',
                    unsafe_allow_html=True
                )

                # Métricas en tiempo real
                palabras = len(respuesta_parcial.split())
                caracteres = len(respuesta_parcial)

                with metrics.container():
                    st.markdown("#### 📊 Métricas en Tiempo Real")
                    col1, col2, col3, col4 = st.columns(4) 
                    
                    with col1:
                        st.metric("Palabras", palabras)
                    
                    with col2:
                        st.metric("Caracteres", caracteres)
                    
                    with col3:
                        st.metric("Tokens", tokens)
                    
                    with col4:
                        if tok_s >= 20:
                            delta_color = "normal"
                            emoji = "🚀"
                        elif tok_s >= 10:
                            delta_color = "normal"
                            emoji = "⚡"
                        else:
                            delta_color = "normal"
                            emoji = "🐌"

                        st.metric(
                            f"{emoji} Tok/s", 
                            f"{tok_s:.1f}",
                            delta=None,
                            help="Tokens generados por segundo (velocidad de generación)"
                        )

            elif ctype == "final":
                # Finalizar métricas
                if t_start is None:
                    t_start = time.time()

                dafo_final = chunk.get("dafo")

                # Respuesta final (texto raw si viene)
                respuesta_final = (
                    chunk.get("respuesta_raw")
                    or chunk.get("respuesta")
                    or chunk.get("respuesta_parcial")
                    or respuesta_parcial
                )

                # Tokens finales si están
                tokens = chunk.get("tokens_generados", tokens)

                # tok/s final: usar backend si viene, si no calcular
                if "tokens_por_segundo" in chunk and chunk["tokens_por_segundo"] is not None:
                    tok_s = float(chunk["tokens_por_segundo"])
                else:
                    elapsed = max(0.001, time.time() - t_start)
                    tok_s = tokens / elapsed

                status.success("✅ DAFO completado")

                # Pintar final sin cursor
                respuesta_box.markdown(
                    f'<div class="resultado-box">{respuesta_final}</div>',
                    unsafe_allow_html=True
                )

                # Métricas finales
                palabras = len(respuesta_final.split())
                caracteres = len(respuesta_final)

                with metrics.container():
                    st.markdown("#### 📊 Métricas Finales")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Palabras", palabras)
                    with col2:
                        st.metric("Caracteres", caracteres)
                    with col3:
                        st.metric("Tokens", tokens)
                    with col4:
                        # pequeña etiqueta de rendimiento (como en resumen)
                        if tok_s >= 15:
                            etiqueta = "🚀 Excelente"
                        elif tok_s >= 8:
                            etiqueta = "⚡ Muy bueno"
                        elif tok_s >= 4:
                            etiqueta = "✅ Bueno"
                        else:
                            etiqueta = "🐌 Lento"

                        st.metric("Tok/s", f"{tok_s:.1f}", delta=etiqueta)

                break

            elif ctype == "error":
                status.error(f"❌ Error: {chunk.get('error','Error desconocido')}")
                raw = chunk.get("respuesta_raw", "")
                if raw:
                    with st.expander("Ver respuesta raw"):
                        st.code(raw)
                return None

        return dafo_final

    except Exception as e:
        status.error(f"❌ Error ejecutando DAFO: {e}")
        return None

# -------------------------------------------------------------------
# Main render
# -------------------------------------------------------------------

def render(ctx):
    """Renderiza el tab de ANÁLISIS DAFO"""

    st.header("📊 Análisis DAFO Táctico")

    rag_client = ctx["rag_client"]
    nlp_analyzer = ctx["nlp_analyzer"]
    storage = ctx["storage"]

    # ================================================================
    # VERIFICAR PARTIDOS INDEXADOS
    # ================================================================
    partidos_indexados = []
    try:
        if nlp_analyzer and getattr(nlp_analyzer, "rag_client", None):
            partidos_indexados = nlp_analyzer.rag_client.list_available_matches()
    except Exception as e:
        st.warning(f"⚠️ No se pudo verificar ChromaDB: {e}")

    if not partidos_indexados:
        st.error("❌ No hay partidos indexados en ChromaDB.")
        st.info("💡 Indexa un partido desde el tab 'Resumen NLP' y vuelve aquí.")
        st.stop()

    # ================================================================
    # CARGAR EQUIPOS / PARTIDOS DISPONIBLES
    # ================================================================
    df_equipos = cargar_equipos_csv(storage)
    if df_equipos is None:
        st.error("❌ No se pudo cargar el CSV de equipos")
        st.stop()

    df_equipos_disponibles = df_equipos[df_equipos["match_id"].isin(partidos_indexados)]
    if df_equipos_disponibles.empty:
        st.error("❌ Los partidos indexados no coinciden con el CSV de equipos.")
        st.stop()

    # ================================================================
    # SELECTOR DE PARTIDO
    # ================================================================
    st.markdown("---")
    st.markdown("### 📅 Seleccionar Partido")

    jornadas_disponibles = sorted(df_equipos_disponibles["jornada"].unique())

    col1, col2 = st.columns([1, 2])
    with col1:
        jornada_seleccionada = st.selectbox(
            "Jornada:",
            options=jornadas_disponibles,
            format_func=lambda x: f"Jornada {x}",
            key="jornada_dafo",
        )
    with col2:
        partidos_jornada = df_equipos_disponibles[df_equipos_disponibles["jornada"] == jornada_seleccionada]
        st.info(f"📊 {len(partidos_jornada)} partidos disponibles en Jornada {jornada_seleccionada}")

    st.markdown("**Partido:**")
    partidos_opciones = {}
    for _, row in partidos_jornada.iterrows():
        label = f"Partido {row['partido']}: {row['equipo_local']} vs {row['equipo_visitante']}"
        partidos_opciones[label] = {
            "match_id": int(row["match_id"]),
            "jornada": int(row["jornada"]),
            "partido": int(row["partido"]),
            "equipo_local": row["equipo_local"],
            "equipo_visitante": row["equipo_visitante"],
        }

    selected_partido_label = st.selectbox(
        "Seleccionar partido:",
        options=list(partidos_opciones.keys()),
        key="partido_dafo",
    )
    partido_info = partidos_opciones[selected_partido_label]

    # Info rápida
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Match ID", partido_info["match_id"])
    with c2:
        st.metric("Jornada", partido_info["jornada"])
    with c3:
        st.metric("Partido", partido_info["partido"])

    st.markdown(f"### 🏟️ {partido_info['equipo_local']} vs {partido_info['equipo_visitante']}")

    # ================================================================
    # BOTONES DAFO
    # ================================================================
    st.markdown("---")
    st.markdown("### ⚙️ Generar DAFO")

    colS1, colS2, colS3 = st.columns([1, 1, 2])
    with colS1:
        modo_streaming = st.checkbox("🌊 Streaming", value=True, key="dafo_streaming")
    with colS2:
        max_eventos = st.number_input("Max eventos", min_value=50, max_value=400, value=200, step=25, key="dafo_max_eventos")
    with colS3:
        st.caption("Streaming muestra la generación token a token. Limita eventos para evitar prompts demasiado largos.")

    colA, colB, colC = st.columns([1, 1, 1])
    with colA:
        gen_dafo_local_btn = st.button(
            f"🏠 DAFO Local",
            key="btn_dafo_local",
            type="primary"
        )
    with colB:
        gen_dafo_visitante_btn = st.button(
            f"✈️ DAFO Visitante",
            key="btn_dafo_visitante",
            type="primary"
        )
    with colC:
        gen_dafo_ambos_btn = st.button(
            f"⚔️ DAFO Ambos",
            key="btn_dafo_ambos",
            help="Genera DAFO para ambos equipos (puede tardar el doble)."
        )

    match_id = partido_info["match_id"]

    # ================================================================
    # EJECUCIÓN
    # ================================================================
    # (opcional) precargar eventos para no repetir carga si tu analyzer lo soporta
    eventos = None
    try:
        if nlp_analyzer.rag_client:
            eventos = nlp_analyzer.rag_client.get_match_events(match_id)
        if not eventos:
            eventos = nlp_analyzer._load_eventos_from_minio(match_id)
    except Exception:
        eventos = None

    # recorte opcional de eventos (para prompts más pequeños)
    if eventos and isinstance(eventos, list) and len(eventos) > int(max_eventos):
        eventos = eventos[:int(max_eventos)]

    def mostrar_dafo_parseado(nombre, dafo_dict, icono=""):
        if not dafo_dict:
            st.warning("⚠️ No se pudo generar DAFO estructurado.")
            return
        st.markdown(f"## {icono} {nombre}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 💪 Fortalezas")
            for x in dafo_dict.get("fortalezas", []):
                st.markdown(f"- {x}")
            st.markdown("### 🎯 Oportunidades")
            for x in dafo_dict.get("oportunidades", []):
                st.markdown(f"- {x}")
        with col2:
            st.markdown("### ⚠️ Debilidades")
            for x in dafo_dict.get("debilidades", []):
                st.markdown(f"- {x}")
            st.markdown("### 🚨 Amenazas")
            for x in dafo_dict.get("amenazas", []):
                st.markdown(f"- {x}")

    # ------------------------------------------------------------
    # LOCAL
    # ------------------------------------------------------------
    if gen_dafo_local_btn or gen_dafo_ambos_btn:
        st.markdown("---")
        st.markdown(f"### 🏠 DAFO {partido_info['equipo_local']}")

        if modo_streaming:
            dafo_local = ejecutar_dafo_streaming(
                nlp_analyzer,
                match_id=match_id,
                equipo="Local",
                eventos=eventos,
                titulo_equipo=partido_info["equipo_local"]
            )
            mostrar_dafo_parseado(partido_info["equipo_local"], dafo_local, icono="🏠")
        else:
            with st.spinner("🤖 Analizando equipo local..."):
                dafo_data = nlp_analyzer.analizar_dafo_equipo(match_id, "Local", eventos=eventos, verbose=False, stream=False)
            if isinstance(dafo_data, dict) and "error" in dafo_data:
                st.error(f"❌ {dafo_data['error']}")
            else:
                mostrar_dafo_parseado(partido_info["equipo_local"], dafo_data.get("dafo", {}), icono="🏠")

    # ------------------------------------------------------------
    # VISITANTE
    # ------------------------------------------------------------
    if gen_dafo_visitante_btn or gen_dafo_ambos_btn:
        st.markdown("---")
        st.markdown(f"### ✈️ DAFO {partido_info['equipo_visitante']}")

        if modo_streaming:
            dafo_vis = ejecutar_dafo_streaming(
                nlp_analyzer,
                match_id=match_id,
                equipo="Visitante",
                eventos=eventos,
                titulo_equipo=partido_info["equipo_visitante"]
            )
            mostrar_dafo_parseado(partido_info["equipo_visitante"], dafo_vis, icono="✈️")
        else:
            with st.spinner("🤖 Analizando equipo visitante..."):
                dafo_data = nlp_analyzer.analizar_dafo_equipo(match_id, "Visitante", eventos=eventos, verbose=False, stream=False)
            if isinstance(dafo_data, dict) and "error" in dafo_data:
                st.error(f"❌ {dafo_data['error']}")
            else:
                mostrar_dafo_parseado(partido_info["equipo_visitante"], dafo_data.get("dafo", {}), icono="✈️")


    # ================================================================
    # INFORMACIÓN TÉCNICA (estilo lista + reproducible)
    # ================================================================
    st.markdown("---")
    with st.expander("ℹ️ Información Técnica (DAFO)"):
        st.markdown("""
### 📌 ¿Qué aporta el DAFO al proyecto?

Este módulo convierte eventos minuto a minuto (comentarios y acciones) en una **síntesis táctica** con formato **DAFO**:
- **Fortalezas**: patrones positivos observables (control, ocasiones, presión, etc.)
- **Debilidades**: pérdidas recurrentes, desorden defensivo, baja eficacia
- **Oportunidades**: espacios y ajustes explotables (cambios, bandas, balón parado)
- **Amenazas**: riesgos del rival (transiciones, dominio aéreo, ritmo)

### 🔁 Pipeline lógico
1. **Recuperación (RAG)**: eventos del partido (ChromaDB)
2. **Contextualización**: equipo objetivo (Local/Visitante)
3. **Generación (LLM)**: estructura fija (4 bloques DAFO)
4. **Salida**: bullets listos para analista / cuerpo técnico

### ✅ Ventajas del formato DAFO
- Compacto y accionable (orientado a decisiones)
- Fácil de leer en una demo
- Justifica el valor del RAG más allá de “pregunta-respuesta”

### 🧩 Reproducibilidad
- Entrada controlada: match_id + rol (Local/Visitante)
- Salida estructurada: 4 listas (fortalezas/debilidades/oportunidades/amenazas)
- Integrable en informes automáticos futuros (épico fuera de alcance)
        """)
