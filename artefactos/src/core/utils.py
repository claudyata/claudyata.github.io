# ============================================================================
# IMPORTS
# ============================================================================

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

try:
    from core.config import *
    from core.dependencies import *
    from core.data_loaders import *
    from core.features import *
except ImportError:
    from config import *
    from dependencies import *
    from data_loaders import *
    from features import *

logger = logging.getLogger(__name__)

# ============================================================================
# UTILITIES - Funciones Helper
# ============================================================================

def format_file_size(bytes_size):
    """
    Formatea tamaño de archivo en bytes a formato legible.
    
    Args:
        bytes_size: Tamaño en bytes
    
    Returns:
        String formateado (ej: "2.34 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def format_duration(seconds):
    """
    Formatea duración en segundos a HH:MM:SS.
    
    Args:
        seconds: Duración en segundos
    
    Returns:
        String formateado (ej: "01:23:45")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_timestamp(dt):
    """Formatea datetime a string legible"""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_jornada_label(jornada_num):
    """Retorna label formateado para jornada"""
    return f"Jornada {jornada_num}"


def get_partido_label(row):
    """Retorna label formateado para partido"""
    return f"Partido {row['numero_partido']}: {row['equipo_local']} vs {row['equipo_visitante']}"


def validate_match_id(match_id):
    """
    Valida que el match_id esté en rango válido.
    
    Args:
        match_id: ID a validar
    
    Returns:
        bool
    """
    MATCH_ID_MAX = MATCH_ID_INICIAL + (TOTAL_JORNADAS * PARTIDOS_POR_JORNADA)
    return MATCH_ID_INICIAL <= match_id < MATCH_ID_MAX

def get_pdf_url(storage, partido_id):
    """
    Genera URL presigned del PDF desde BRONCE.
    
    Args:
        storage: Cliente Storage
        partido_id: ID del partido
    
    Returns:
        URL presigned válida por 1 hora o None
    """
    pdf_key = f'{BRONCE_PDF}/2025-2026/feuille_de_match_{partido_id}.pdf'
    
    try:
        # Verificar que existe
        storage.s3.head_object(Bucket=BUCKET_BRONCE, Key=pdf_key)
        
        # Generar URL presigned
        url = storage.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_BRONCE, 'Key': pdf_key},
            ExpiresIn=3600
        )
        return url
    
    except Exception as e:
        logger.debug(f"PDF no encontrado: {partido_id}")
        return None

def parse_tegrastats_line(line):
    """
    Parsea una línea de tegrastats y extrae métricas.
    
    Returns:
        dict con keys: gpu_usage, ram_used, ram_total, cpu_avg, 
                      temp_tj, temp_soc, power_mw, power_total_mw
    """
    metrics = {
        'gpu_usage': 0,
        'ram_used': 0,
        'ram_total': 0,
        'cpu_avg': 0,
        'temp_tj': 0,
        'temp_soc': 0,
        'power_mw': 0,
        'power_total_mw': 0  # ← NUEVO
    }
    
    # GPU
    gpu_match = re.search(r'GR3D_FREQ\s+(\d+)%', line)
    if gpu_match:
        metrics['gpu_usage'] = int(gpu_match.group(1))
    
    # RAM
    ram_match = re.search(r'RAM (\d+)/(\d+)MB', line)
    if ram_match:
        metrics['ram_used'] = int(ram_match.group(1))
        metrics['ram_total'] = int(ram_match.group(2))
    
    # CPU
    cpu_matches = re.findall(r'CPU\s+\[([^\]]+)\]', line)
    if cpu_matches:
        cpu_values = re.findall(r'(\d+)%', cpu_matches[0])
        if cpu_values:
            metrics['cpu_avg'] = sum(int(v) for v in cpu_values) / len(cpu_values)
    
    # Temperatura Junction
    temp_match = re.search(r'tj@([\d.]+)C', line)
    if temp_match:
        metrics['temp_tj'] = float(temp_match.group(1))
    
    # Temperatura SOC
    temp_socs = re.findall(r'soc\d@([\d.]+)C', line)
    if temp_socs:
        metrics['temp_soc'] = sum(float(t) for t in temp_socs) / len(temp_socs)
    
    # Potencia GPU/SOC
    power_match = re.search(r'VDD_GPU_SOC\s+(\d+)mW', line)
    if power_match:
        metrics['power_mw'] = int(power_match.group(1))
    
    # ✅ NUEVO: Potencia Total del Sistema
    power_total_match = re.search(r'VIN_SYS_5V0\s+(\d+)mW', line)
    if power_total_match:
        metrics['power_total_mw'] = int(power_total_match.group(1))
    
    return metrics

__all__ = [
  "get_jornada_label","get_partido_label","validate_match_id",
  "format_file_size","format_duration","format_timestamp", "get_pdf_url", "parse_tegrastats_line"
]