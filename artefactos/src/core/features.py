import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
import logging
import json
import subprocess
import tempfile
import os
import time
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import re
logger = logging.getLogger(__name__)




try:
    from core.config import *
    from core.dependencies import *
    from core.data_loaders import *
    from core.utils import *
except ImportError:
    from config import *
    from dependencies import *
    from data_loaders import *
    from utils import *

# ============================================================================
# Fuinionalidades
# ============================================================================

def indexar_partido_on_demand(match_id, nlp_analyzer, idioma_traduccion='en', progress_callback=None):
    """
    Indexa un partido específico en ChromaDB con traducción a idioma especificado
    
    Args:
        match_id: ID del partido a indexar
        nlp_analyzer: NLPAnalyzer con rag_client y métodos de traducción
        idioma_traduccion: Idioma para vectores ('en' recomendado, 'es', 'pt', etc.)
        progress_callback: Función para actualizar progreso (opcional)
    
    Returns:
        tuple: (exito: bool, mensaje: str, num_eventos: int)
    """
    try:
        import pandas as pd
        import json
        from io import BytesIO
        
        # Callback helper
        def update_progress(step, progress):
            if progress_callback:
                progress_callback(step, progress)
        
        # Verificar que tenemos RAG client
        if not nlp_analyzer.rag_client:
            return False, "RAG Client no disponible", 0
        
        # ====================================================================
        # PASO 1: CARGAR EVENTOS DESDE PLATA
        # ====================================================================
        
        update_progress("📦 Cargando eventos desde PLATA...", 10)
        
        response = nlp_analyzer.storage.s3.get_object(
            Bucket='plata',
            Key='eventos/2025-2026/eventos_consolidado.json'
        )
        
        eventos_todos = json.loads(response['Body'].read().decode('utf-8'))
        eventos_partido = [e for e in eventos_todos if e.get('match_id') == match_id]
        
        if not eventos_partido:
            return False, f"No se encontraron eventos para Match {match_id} en PLATA", 0
        
        update_progress(f"✅ {len(eventos_partido)} eventos encontrados", 20)
        
        # ====================================================================
        # PASO 2: TRADUCIR EVENTOS AL IDIOMA ESPECIFICADO
        # ====================================================================
        
        update_progress(f"🌍 Traduciendo a {idioma_traduccion.upper()}...", 30)
        
        eventos_traducidos = []
        total_eventos = len(eventos_partido)
        
        for idx, evento in enumerate(eventos_partido):
            # Actualizar progreso cada 10 eventos
            if idx % 10 == 0:
                progreso = 30 + int((idx / total_eventos) * 30)  # 30% a 60%
                update_progress(f"🌍 Traduciendo evento {idx+1}/{total_eventos}...", progreso)
            
            evento_copy = evento.copy()
            
            # Determinar texto fuente
            if idioma_traduccion == 'en':
                # Para inglés, preferir texto_en si existe
                texto_fuente = evento.get('texto_en') or evento.get('texto_es') or evento.get('texto', '')
                
                # Si no hay texto_en, traducir
                if not evento.get('texto_en') and texto_fuente:
                    try:
                        texto_traducido = nlp_analyzer._traducir_texto(texto_fuente, idioma_destino='en')
                        evento_copy['texto_vector'] = texto_traducido
                    except Exception as e:
                        logger.warning(f"⚠️ Error traduciendo evento {idx}: {e}")
                        evento_copy['texto_vector'] = texto_fuente
                else:
                    evento_copy['texto_vector'] = texto_fuente
            
            elif idioma_traduccion == 'es':
                # Para español, usar texto_es o texto original
                evento_copy['texto_vector'] = evento.get('texto_es') or evento.get('texto', '')
            
            elif idioma_traduccion == 'pt':
                # Para portugués, traducir si no existe
                texto_pt = evento.get('texto_pt')
                if texto_pt:
                    evento_copy['texto_vector'] = texto_pt
                else:
                    texto_fuente = evento.get('texto_es') or evento.get('texto', '')
                    try:
                        evento_copy['texto_vector'] = nlp_analyzer._traducir_texto(texto_fuente, idioma_destino='pt')
                    except:
                        evento_copy['texto_vector'] = texto_fuente
            
            else:
                # Otros idiomas: intentar campo específico o traducir
                campo_idioma = f'texto_{idioma_traduccion}'
                if evento.get(campo_idioma):
                    evento_copy['texto_vector'] = evento[campo_idioma]
                else:
                    texto_fuente = evento.get('texto_es') or evento.get('texto', '')
                    try:
                        evento_copy['texto_vector'] = nlp_analyzer._traducir_texto(texto_fuente, idioma_destino=idioma_traduccion)
                    except:
                        evento_copy['texto_vector'] = texto_fuente
            
            eventos_traducidos.append(evento_copy)
        
        update_progress(f"✅ Traducción completada", 60)
        
        # ====================================================================
        # PASO 3: PREPARAR DOCUMENTOS PARA CHROMADB
        # ====================================================================
        
        update_progress("🔄 Preparando documentos...", 70)
        
        documentos = []
        metadatas = []
        ids = []
        
        for i, evento in enumerate(eventos_traducidos):
            texto = evento.get('texto_vector', '')
            
            if not texto:
                continue
            
            doc_id = f"match_{match_id}_evento_{i}_{idioma_traduccion}"
            
            metadata = {
                'match_id': match_id,
                'minuto': evento.get('minuto', 0),
                'minuto_exacto': evento.get('minuto_exacto', 0),
                'equipo': evento.get('equipo', 'Desconocido'),
                'periodo': evento.get('periodo', 1),
                'jornada': evento.get('jornada', 0),
                'partido': evento.get('partido', 0),
                'idioma_vector': idioma_traduccion,
                'texto_original': evento.get('texto', '')[:100]  # Primeros 100 chars para referencia
            }
            
            documentos.append(texto)
            metadatas.append(metadata)
            ids.append(doc_id)
        
        if not documentos:
            return False, "No se encontraron eventos con texto válido", 0
        
        update_progress(f"✅ {len(documentos)} documentos preparados", 80)
        
        # ====================================================================
        # PASO 4: INDEXAR EN CHROMADB
        # ====================================================================
        
        update_progress("🗄️ Indexando en ChromaDB...", 90)
        
        vectorstore = nlp_analyzer.rag_client.vectorstore
        
        vectorstore.add_texts(
            texts=documentos,
            metadatas=metadatas,
            ids=ids
        )
        
        update_progress(f"✅ Indexación completada ({idioma_traduccion.upper()})", 100)
        
        return True, f"Match {match_id} indexado en {idioma_traduccion.upper()} ({len(documentos)} eventos)", len(documentos)
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        
        logger.error(f"❌ Error en indexación:")
        logger.error(error_detail)
        
        return False, f"Error: {str(e)}", 0

def crear_vectorstore_equipos(equipos_unicos, rag_client):
    """
    Crea un vector store temporal con nombres de equipos.
    
    Args:
        equipos_unicos: Set de nombres únicos
        rag_client: Cliente RAG
    
    Returns:
        ChromaDB collection temporal
    """
    from langchain_community.vectorstores import Chroma
    import uuid
    
    embeddings = rag_client.embeddings
    temp_collection = f"equipos_temp_{uuid.uuid4().hex[:8]}"
    
    # Convertir a documentos
    textos = list(equipos_unicos)
    metadatas = [{'nombre_original': nombre} for nombre in textos]
    
    # Crear vectorstore
    vectorstore = Chroma.from_texts(
        texts=textos,
        embedding=embeddings,
        metadatas=metadatas,
        collection_name=temp_collection,
        #persist_directory="/tmp/chroma_temp_equipos"
        persist_directory=None
    )
    
    return vectorstore

def buscar_acta_por_equipos(match_id, partido_info, indice_actas, ollama_client):
    """
    Busca el acta correspondiente usando matching LLM.
    
    Args:
        match_id: ID del match
        partido_info: Row del CSV
        indice_actas: Índice de actas
        ollama_client: Cliente Ollama
    
    Returns:
        (acta, key) o (None, None)
    """
    equipo_local_csv = partido_info['equipo_local']
    equipo_visitante_csv = partido_info['equipo_visitante']
    
    nombres_candidatos = list(indice_actas['equipos_unicos'])
    
    # Matching para ambos equipos
    match_local = match_equipo_con_llm(
        equipo_local_csv,
        nombres_candidatos,
        ollama_client
    )
    
    match_visitante = match_equipo_con_llm(
        equipo_visitante_csv,
        nombres_candidatos,
        ollama_client
    )
    
    # Buscar acta con ambos equipos
    for acta_info in indice_actas['actas']:
        if (acta_info['local'] == match_local and 
            acta_info['visitante'] == match_visitante):
            return acta_info['acta'], acta_info['key']
    
    # Fallback: buscar solo por local
    if match_local:
        for acta_info in indice_actas['actas']:
            if acta_info['local'] == match_local:
                return acta_info['acta'], acta_info['key']
    
    return None, None

def ejecutar_query_sugerida(query_text, match_id, idioma, modo_streaming, rag_client):
    """
    Ejecuta una query sugerida con o sin streaming
    """
    
    if modo_streaming:
        # Contenedores
        status_container = st.empty()
        respuesta_container = st.empty()
        
        try:
            status_container.info("🤖 Consultando...")
            
            resultado_stream = rag_client.query_stream(
                query_text,
                match_id=match_id,
                language=idioma,
                verbose=True
            )
            
            respuesta_parcial = ""
            
            for chunk in resultado_stream:
                if chunk['type'] == 'token':
                    respuesta_parcial = chunk['answer_partial']
                    
                    respuesta_container.markdown(
                        f'<div class="resultado-box">{respuesta_parcial}<span style="animation: blink 1s infinite;">▌</span></div>',
                        unsafe_allow_html=True
                    )
                
                elif chunk['type'] == 'complete':
                    respuesta_final = chunk['answer']
                    
                    status_container.empty()
                    respuesta_container.markdown(
                        f'<div class="resultado-box">{respuesta_final}</div>',
                        unsafe_allow_html=True
                    )
        
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    else:
        # Modo normal
        with st.spinner('🤖 Consultando...'):
            try:
                resultado = rag_client.query(query_text, match_id=match_id, language=idioma, verbose=False)
                
                st.markdown(
                    f'<div class="resultado-box">{resultado["answer"]}</div>',
                    unsafe_allow_html=True
                )
            
            except Exception as e:
                st.error(f"❌ Error: {e}")

def calcular_jornada_partido(match_id):
    """
    Calcula jornada y partido desde match_id.
    
    Args:
        match_id: ID del partido (10890-11017)
    
    Returns:
        (jornada, partido)
    
    Example:
        >>> calcular_jornada_partido(10890)
        (1, 1)
        >>> calcular_jornada_partido(10897)
        (1, 8)
        >>> calcular_jornada_partido(10898)
        (2, 1)
    """
    offset = match_id - MATCH_ID_INICIAL
    jornada = (offset // PARTIDOS_POR_JORNADA) + 1
    partido = (offset % PARTIDOS_POR_JORNADA) + 1
    
    return jornada, partido

__all__ = [
  "crear_vectorstore_equipos", "buscar_acta_por_equipos","ejecutar_query_sugerida","calcular_jornada_partido","indexar_partido_on_demand"
]