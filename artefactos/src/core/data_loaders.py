
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
    from core.utils import *
    from core.features import *
except ImportError:
    from config import *
    from dependencies import *
    from utils import *
    from features import *


# ============================================================================
# DATA LOADERS - Funciones de Carga de Datos (Cacheadas)
# ============================================================================

@st.cache_data
def cargar_equipos_csv(_storage):
    """
    Carga CSV de equipos desde PLATA.
    
    Args:
        _storage: Cliente MedallionStorage (no se hashea por el _)
    
    Returns:
        DataFrame con equipos o None si error
    """
    try:
        response = _storage.s3.get_object(
            Bucket=BUCKET_PLATA,
            Key='equipos/2025-2026.csv'
        )
        
        df = pd.read_csv(BytesIO(response['Body'].read()))
        logger.info(f"✅ Equipos cargados: {len(df)} registros")
        return df
    
    except Exception as e:
        logger.error(f"❌ Error cargando equipos: {e}")
        return None


@st.cache_data
def cargar_indice_actas(_storage):
    """
    Carga todas las actas y crea un índice de equipos.
    
    Returns:
        Dict: {
            'actas': [...],  # Lista de actas con metadata
            'equipos_unicos': set([...])  # Nombres únicos
        }
    """
    try:
        response = _storage.s3.list_objects_v2(
            Bucket=BUCKET_PLATA,
            Prefix='actas/2025-2026/'
        )
        
        actas_index = []
        equipos_set = set()
        
        for obj in response.get('Contents', []):
            key = obj['Key']
            
            if key.endswith('.json'):
                # Cargar acta
                acta_response = _storage.s3.get_object(
                    Bucket=BUCKET_PLATA,
                    Key=key
                )
                
                acta = json.loads(acta_response['Body'].read().decode('utf-8'))
                
                # Extraer nombres
                local = acta.get('local', '')
                visitante = acta.get('visitante', '')
                
                actas_index.append({
                    'key': key,
                    'id': acta.get('id'),
                    'local': local,
                    'visitante': visitante,
                    'fecha': acta.get('fecha'),
                    'jornada': acta.get('jornada'),
                    'acta': acta
                })
                
                if local:
                    equipos_set.add(local)
                if visitante:
                    equipos_set.add(visitante)
        
        logger.info(f"✅ Índice actas: {len(actas_index)} actas, {len(equipos_set)} equipos")
        
        return {
            'actas': actas_index,
            'equipos_unicos': equipos_set
        }
    
    except Exception as e:
        logger.error(f"❌ Error cargando índice actas: {e}")
        return {'actas': [], 'equipos_unicos': set()}


@st.cache_data
def cargar_acta_json(_storage, partido_id):
    """
    Carga un acta JSON específica desde PLATA.
    
    Args:
        _storage: Cliente Storage
        partido_id: ID del partido
    
    Returns:
        Dict con acta o None
    """
    try:
        response = _storage.s3.list_objects_v2(
            Bucket=BUCKET_PLATA,
            Prefix='actas/2025-2026/'
        )
        
        # Buscar archivo que contenga el ID
        for obj in response.get('Contents', []):
            if str(partido_id) in obj['Key'] and obj['Key'].endswith('.json'):
                acta_response = _storage.s3.get_object(
                    Bucket=BUCKET_PLATA,
                    Key=obj['Key']
                )
                
                acta = json.loads(acta_response['Body'].read().decode('utf-8'))
                return acta
        
        return None
    
    except Exception as e:
        logger.error(f"❌ Error cargando acta {partido_id}: {e}")
        return None


@st.cache_data
def cargar_goleadores_csv(_storage):
    """Carga CSV de goleadores desde PLATA"""
    try:
        response = _storage.s3.get_object(
            Bucket=BUCKET_PLATA,
            Key='goleadores/2025-2026.csv'
        )
        
        df = pd.read_csv(BytesIO(response['Body'].read()))
        logger.info(f"✅ Goleadores cargados: {len(df)} registros")
        return df
    
    except Exception as e:
        logger.error(f"❌ Error cargando goleadores: {e}")
        return None


@st.cache_data
def cargar_tarjetas_csv(_storage):
    """Carga CSV de tarjetas desde PLATA (si existe)"""
    try:
        response = _storage.s3.get_object(
            Bucket=BUCKET_PLATA,
            Key='tarjetas/2025-2026.csv'
        )
        
        df = pd.read_csv(BytesIO(response['Body'].read()))
        logger.info(f"✅ Tarjetas cargadas: {len(df)} registros")
        return df
    
    except Exception as e:
        # Si no existe, devolver None
        return None


@st.cache_data
def load_partidos_disponibles(_nlp_analyzer):
    """Carga lista de partidos disponibles"""
    return _nlp_analyzer.listar_partidos_disponibles()


@st.cache_data
def load_match_info(_nlp_analyzer, match_id):
    """Carga información de un partido específico"""
    return _nlp_analyzer._load_match_info(match_id)

@st.cache_data
def match_equipo_con_rag(nombre_csv, nombres_candidatos, _rag_client):
    """
    Usa embeddings semánticos para matching de equipos.
    
    Args:
        nombre_csv: Nombre del equipo desde CSV
        nombres_candidatos: Lista de nombres candidatos
        _rag_client: Cliente RAG
    
    Returns:
        Dict con mejor match y score o None
    """
    if not nombres_candidatos:
        return None
    
    try:
        # Crear vectorstore temporal
        vectorstore = crear_vectorstore_equipos(set(nombres_candidatos), _rag_client)
        
        # Buscar similares
        results = vectorstore.similarity_search_with_score(nombre_csv, k=3)
        
        # Limpiar
        try:
            vectorstore.delete_collection()
        except:
            pass
        
        if results:
            mejor_match = results[0]
            documento = mejor_match[0]
            score = mejor_match[1]
            
            # Score bajo = más similar (distancia coseno)
            if score < 0.5:
                return {
                    'nombre': documento.metadata['nombre_original'],
                    'score': score,
                    'top3': [
                        {'nombre': r[0].metadata['nombre_original'], 'score': r[1]}
                        for r in results[:3]
                    ]
                }
        
        return None
    
    except Exception as e:
        logger.error(f"Error en matching RAG: {e}")
        return None

__all__ = [
  "cargar_equipos_csv","cargar_indice_actas","cargar_acta_json","cargar_goleadores_csv",
  "cargar_tarjetas_csv","load_partidos_disponibles","load_match_info","match_equipo_con_rag",
]