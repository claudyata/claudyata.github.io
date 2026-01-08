"""
Tab de Monitoreo GPU y Sistema
Gestión de recursos, tegrastats, CUDA, y costes energéticos
Optimizado para Jetson AGX Orin 64GB

Autor: Pedro José García Fernández
Fecha: 2 Enero 2025
"""

import streamlit as st
import subprocess
import os
import re
import time
import tempfile
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import json
import threading
from pathlib import Path
from io import BytesIO


# ============================================================================
# CONSTANTES Y UMBRALES PARA JETSON AGX ORIN 64GB
# ============================================================================

# RAM Sistema (64GB total)
RAM_WARNING_THRESHOLD = 80    # 80% = ~51GB usado
RAM_CRITICAL_THRESHOLD = 90   # 90% = ~58GB usado

# CUDA Memory (comparte los 64GB con RAM)
CUDA_LOW_THRESHOLD = 10       # < 10GB libre
CUDA_CRITICAL_THRESHOLD = 5   # < 5GB libre

# GPU Usage
GPU_NORMAL = 50               # < 50%
GPU_MEDIUM = 80               # 50-80%

# Temperatura (Jetson AGX Orin specs)
TEMP_NORMAL = 70              # < 70°C
TEMP_ELEVATED = 85            # 70-85°C
TEMP_HIGH = 95                # > 85°C (throttling probable)

# Potencia (modos Jetson AGX Orin)
POWER_MODES = {
    '15W': (0, 20),
    '30W': (20, 40),
    '50W': (40, 55),
    '60W (MAXN)': (55, 200)
}

# Huella de carbono (España 2024)
KG_CO2_PER_KWH = 0.25  # kg CO2 por kWh (mix eléctrico español)


# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def get_jetson_model():
    """Detecta el modelo de Jetson"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip()
            return model
    except:
        return "Jetson (modelo desconocido)"

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
        'power_total_mw': 0
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
    
    # Potencia Total del Sistema
    power_total_match = re.search(r'VIN_SYS_5V0\s+(\d+)mW', line)
    if power_total_match:
        metrics['power_total_mw'] = int(power_total_match.group(1))
    
    return metrics


def calcular_coste_y_huella(power_w, duracion_segundos, precio_kwh):
    """
    Calcula coste energético y huella de carbono
    
    Args:
        power_w: Potencia en Watts
        duracion_segundos: Duración del experimento en segundos
        precio_kwh: Precio por kWh
        
    Returns:
        dict con coste_euros y co2_kg
    """
    # Convertir a horas
    duracion_horas = duracion_segundos / 3600
    
    # Calcular kWh consumidos
    kwh_consumidos = (power_w / 1000) * duracion_horas
    
    # Calcular coste
    coste_euros = kwh_consumidos * precio_kwh
    
    # Calcular CO2
    co2_kg = kwh_consumidos * KG_CO2_PER_KWH
    
    return {
        'kwh': kwh_consumidos,
        'coste': coste_euros,
        'co2_kg': co2_kg,
        'duracion_h': duracion_horas
    }


@st.cache_resource
def get_gpu_monitor_state():
    """Estado compartido para monitoreo GPU"""
    return {
        'monitoring': False,
        'log_file': None,
        'start_time': None,
        'thread': None
    }


# ============================================================================
# FUNCIÓN PRINCIPAL DEL TAB
# ============================================================================

def render(ctx):
    """
    Renderiza el tab de monitoreo GPU
    
    Args:
        ctx: Contexto con rag_client
    """
    
    # ========================================================================
    # INICIALIZACIÓN DE SESSION STATE (AÑADIR ESTO)
    # ========================================================================
    
    # Inicializar variables de session_state si no existen
    if 'tegra_data' not in st.session_state:
        st.session_state.tegra_data = None
    
    if 'tegra_error' not in st.session_state:
        st.session_state.tegra_error = None
    
    if 'ram_data' not in st.session_state:
        st.session_state.ram_data = None
    
    if 'cuda_data' not in st.session_state:
        st.session_state.cuda_data = None
    
    if 'ollama_status' not in st.session_state:
        st.session_state.ollama_status = None
    
    if 'last_system_check' not in st.session_state:
        st.session_state.last_system_check = None

    # ========================================================================
    # INICIALIZACIÓN
    # ========================================================================
    
    rag_client = ctx["rag_client"]

    st.header("🎮 Monitoreo GPU y Gestión de Memoria")
    
    # Obtener estado
    gpu_state = get_gpu_monitor_state()
    
    # ========================================================================
    # DETECTAR Y MOSTRAR MODELO JETSON
    # ========================================================================
    
    jetson_model = get_jetson_model()
    
    col_model, col_refresh_main = st.columns([3, 1])
    
    with col_model:
        st.info(f"🤖 **{jetson_model}**")
    
    with col_refresh_main:
        if st.button("🔄 Actualizar Todo", key="refresh_all_main"):
            st.cache_resource.clear()
            st.rerun()
    
    # Specs del AGX Orin 64GB
    if "AGX Orin" in jetson_model:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("RAM Total", "64 GB", help="Memoria unificada CPU+GPU")
        
        with col2:
            st.metric("GPU Cores", "2048", help="NVIDIA Ampere")
        
        with col3:
            st.metric("CPU Cores", "12", help="ARM Cortex-A78AE")
        
        with col4:
            st.metric("TDP Max", "60W", help="Modo MAXN")
    
    # ========================================================================
    # ESTADO ACTUAL DEL SISTEMA
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📊 Estado Actual del Sistema")

    # Botón para refrescar
    col_refresh, col_auto = st.columns([1, 4])
    
    with col_refresh:
        refresh_btn = st.button("🔄 Refrescar", key="refresh_system_state")
    
    with col_auto:
        auto_refresh = st.checkbox(
            "🔄 Auto-refresh (cada 5s)",
            value=False,
            key="auto_refresh_estado",
            help="Actualiza automáticamente cada 5 segundos"
        )

    # Obtener estado en tiempo real
    if refresh_btn or auto_refresh or 'last_system_check' not in st.session_state:
        st.session_state.last_system_check = datetime.now()
        
        # ====================================================================
        # 1. MEMORIA RAM
        # ====================================================================
        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                # Parsear línea Mem
                mem_line = lines[1].split()
                ram_total = int(mem_line[1])
                ram_used = int(mem_line[2])
                ram_free = int(mem_line[3])
                ram_percent = (ram_used / ram_total) * 100
                
                st.session_state.ram_data = {
                    'total': ram_total,
                    'used': ram_used,
                    'free': ram_free,
                    'percent': ram_percent
                }
        except:
            st.session_state.ram_data = None
        
        # ====================================================================
        # 2. GPU via Tegrastats
        # ====================================================================
        try:
            # Crear archivo temporal para output
            temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log')
            temp_path = temp_file.name
            temp_file.close()
            
            # Iniciar tegrastats en background (solo 1 muestra)
            process = subprocess.Popen(
                ['tegrastats', '--interval', '500'],
                stdout=open(temp_path, 'w'),
                stderr=subprocess.DEVNULL
            )
            
            # Esperar 1.5 segundos (suficiente para 2-3 muestras)
            time.sleep(1.5)
            
            # Matar proceso
            process.terminate()
            process.wait(timeout=1)
            
            # Leer output
            with open(temp_path, 'r') as f:
                lines = f.readlines()
            
            # Limpiar archivo temporal
            os.unlink(temp_path)
            
            # Parsear última línea válida
            if lines:
                # Buscar última línea con datos (no vacía)
                ultima_linea = None
                for line in reversed(lines):
                    if 'RAM' in line and 'CPU' in line:
                        ultima_linea = line.strip()
                        break
                
                if ultima_linea:
                    # Usar función compartida
                    metrics = parse_tegrastats_line(ultima_linea)
                    st.session_state.tegra_data = metrics
                    st.session_state.tegra_error = None
                    st.session_state.ultima_linea_tegra = ultima_linea
                else:
                    st.session_state.tegra_data = None
                    st.session_state.tegra_error = "No se encontraron líneas válidas en output"
            else:
                st.session_state.tegra_data = None
                st.session_state.tegra_error = "Output vacío de tegrastats"

        except Exception as e:
            st.session_state.tegra_data = None
            st.session_state.tegra_error = f"Error: {str(e)}"
        
        # ====================================================================
        # 3. CUDA Memory
        # ====================================================================
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(0) / 1e9
                reserved = torch.cuda.memory_reserved(0) / 1e9
                total = torch.cuda.get_device_properties(0).total_memory / 1e9
                free = total - reserved
                
                st.session_state.cuda_data = {
                    'allocated': allocated,
                    'reserved': reserved,
                    'total': total,
                    'free': free,
                    'percent': (allocated / total) * 100
                }
            else:
                st.session_state.cuda_data = None
        except:
            st.session_state.cuda_data = None
        
        # ====================================================================
        # 4. Ollama Status
        # ====================================================================
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'ollama'],
                capture_output=True,
                text=True
            )
            ollama_active = result.stdout.strip() == 'active'
            st.session_state.ollama_status = ollama_active
        except:
            st.session_state.ollama_status = None

    # ========================================================================
    # MOSTRAR DATOS
    # ========================================================================

    # Timestamp
    #st.caption(f"🕐 Última actualización: {st.session_state.last_system_check.strftime('%H:%M:%S')}")
    if st.session_state.last_system_check:
        st.caption(f"🕐 Última actualización: {st.session_state.last_system_check.strftime('%H:%M:%S')}")
    else:
        st.caption("🕐 Presiona 'Refrescar' para obtener datos")

    # ====================================================================
    # FILA 1: MÉTRICAS PRINCIPALES
    # ====================================================================

    col1, col2, col3, col4 = st.columns(4)

    # GPU
    with col1:
        if st.session_state.tegra_data:
            gpu_usage = st.session_state.tegra_data['gpu_usage']
            
            if gpu_usage < GPU_NORMAL:
                delta_text = "Normal"
                delta_color = "normal"
            elif gpu_usage < GPU_MEDIUM:
                delta_text = "Medio"
                delta_color = "normal"
            else:
                delta_text = "Alto"
                delta_color = "inverse"
            
            st.metric(
                "🎮 GPU Usage",
                f"{gpu_usage}%",
                delta=delta_text,
                delta_color=delta_color,
                help="Uso de la GPU (GR3D_FREQ)"
            )
        else:
            st.metric("🎮 GPU Usage", "N/A")

    # CPU
    with col2:
        if st.session_state.tegra_data:
            cpu_avg = st.session_state.tegra_data['cpu_avg']
            st.metric(
                "💻 CPU Promedio",
                f"{cpu_avg:.1f}%",
                help="Promedio de uso de los 12 cores"
            )
        else:
            st.metric("💻 CPU", "N/A")

    # Temperatura
    with col3:
        if st.session_state.tegra_data:
            temp_tj = st.session_state.tegra_data['temp_tj']
            
            if temp_tj < TEMP_NORMAL:
                delta_text = "Normal"
                delta_color = "normal"
            elif temp_tj < TEMP_ELEVATED:
                delta_text = "Elevada"
                delta_color = "off"
            else:
                delta_text = "⚠️ Alta"
                delta_color = "inverse"
            
            st.metric(
                "🌡️ Temp Junction",
                f"{temp_tj:.1f}°C",
                delta=delta_text,
                delta_color=delta_color,
                help="Temperatura del chip (tj@XXC)"
            )
        else:
            st.metric("🌡️ Temperatura", "N/A")

    # Potencia
    with col4:
        if st.session_state.tegra_data:
            power_w = st.session_state.tegra_data['power_mw'] / 1000
            st.metric(
                "⚡ Potencia GPU",
                f"{power_w:.1f}W",
                help="VDD_GPU_SOC: GPU + CPU del SOC"
            )
        else:
            st.metric("⚡ Potencia", "N/A")

    # ====================================================================
    # FILA 2: MEMORIA (64GB UNIFICADA)
    # ====================================================================

    st.markdown("#### 💾 Memoria Unificada (64GB)")
    
    st.info("ℹ️ Jetson AGX Orin usa memoria unificada: CPU y GPU comparten los 64GB")

    col1, col2 = st.columns(2)

    # RAM Sistema
    with col1:
        if st.session_state.ram_data:
            ram = st.session_state.ram_data
            
            st.markdown("**🧠 RAM Sistema**")
            
            # Progress bar
            progress_value = ram['percent'] / 100
            st.progress(progress_value)
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Usado", f"{ram['used']/1024:.1f} GB")
            with col_b:
                st.metric("Total", f"{ram['total']/1024:.1f} GB")
            with col_c:
                st.metric("Uso", f"{ram['percent']:.1f}%")
            
            # Advertencias ajustadas para 64GB
            if ram['percent'] > RAM_CRITICAL_THRESHOLD:
                st.error(f"🔴 RAM crítica (>{RAM_CRITICAL_THRESHOLD}%) - limpieza urgente")
            elif ram['percent'] > RAM_WARNING_THRESHOLD:
                st.warning(f"⚠️ RAM alta (>{RAM_WARNING_THRESHOLD}%) - considera limpiar memoria")
            elif ram['percent'] > 70:
                st.info("💡 RAM moderada (>70%)")
        else:
            st.info("RAM no disponible")

    # CUDA Memory
    with col2:
        if st.session_state.cuda_data:
            cuda = st.session_state.cuda_data
            
            st.markdown("**🔥 CUDA Memory (compartida)**")
            
            # Progress bar
            progress_value = cuda['percent'] / 100
            st.progress(progress_value)
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Allocated", f"{cuda['allocated']:.1f} GB")
            with col_b:
                st.metric("Reserved", f"{cuda['reserved']:.1f} GB")
            with col_c:
                st.metric("Free", f"{cuda['free']:.1f} GB")
            
            # Advertencias ajustadas para 64GB
            if cuda['free'] < CUDA_CRITICAL_THRESHOLD:
                st.error(f"🔴 CUDA Memory crítica (<{CUDA_CRITICAL_THRESHOLD}GB libre)")
            elif cuda['free'] < CUDA_LOW_THRESHOLD:
                st.warning(f"⚠️ CUDA Memory baja (<{CUDA_LOW_THRESHOLD}GB libre)")
            elif cuda['free'] < 20:
                st.info("💡 CUDA Memory moderada (<20GB libre)")
            
            # Mostrar uso combinado
            if st.session_state.ram_data:
                total_used = ram['used']/1024
                combined_percent = (total_used / 64) * 100
                st.caption(f"📊 Uso combinado RAM+GPU: {combined_percent:.1f}% de 64GB")
        else:
            st.info("CUDA no disponible (ejecuta código PyTorch para inicializar)")

    # ====================================================================
    # FILA 3: SERVICIOS
    # ====================================================================

    st.markdown("#### 🔧 Servicios")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.ollama_status is not None:
            if st.session_state.ollama_status:
                st.success("🟢 Ollama Activo")
            else:
                st.error("🔴 Ollama Inactivo")
                if st.button("🔄 Reiniciar Ollama", key="quick_restart_ollama"):
                    with st.spinner("Reiniciando..."):
                        subprocess.run(['sudo', 'systemctl', 'restart', 'ollama'])
                        time.sleep(3)
                        st.rerun()
        else:
            st.warning("⚠️ Estado desconocido")

    with col2:
        # Verificar RAG Client
        try:
            if rag_client:
                stats = rag_client.get_stats()
                st.success(f"🟢 RAG Client ({stats['total_eventos']} eventos)")
            else:
                st.warning("⚠️ RAG Client no inicializado")
        except:
            st.error("🔴 RAG Client Error")

    with col3:
        # ChromaDB
        try:
            if rag_client:
                stats = rag_client.get_stats()
                st.success(f"🟢 ChromaDB ({stats['total_partidos']} partidos)")
            else:
                st.warning("⚠️ ChromaDB no disponible")
        except:
            st.error("🔴 ChromaDB Error")

    # ====================================================================
    # FILA 4: COSTE ENERGÉTICO Y PROYECCIÓN
    # ====================================================================

    st.markdown("---")
    st.markdown("### 💰 Análisis de Coste Energético")

    # Configuración
    col_config1, col_config2 = st.columns(2)

    with col_config1:
        precio_kwh = st.number_input(
            "💶 Precio kWh (€):",
            min_value=0.01,
            max_value=1.0,
            value=0.25,
            step=0.01,
            help="Precio promedio en España: ~0.25€/kWh"
        )

    with col_config2:
        # Detectar consumo real si está disponible
        if st.session_state.tegra_data and st.session_state.tegra_data.get('power_total_mw', 0) > 0:
            consumo_real_w = st.session_state.tegra_data['power_total_mw'] / 1000
            consumo_actual = consumo_real_w
            fuente = "Medido (VIN_SYS_5V0)"
            help_text = f"✅ Medido en tiempo real: {consumo_real_w:.2f}W"
        else:
            # Estimar basado en SOC
            if st.session_state.tegra_data:
                power_soc_w = st.session_state.tegra_data['power_mw'] / 1000
                consumo_actual = power_soc_w + 4  # SOC + overhead (RAM, SSD, Red)
                fuente = "Estimado (SOC + overhead)"
                help_text = f"⚠️ Estimado: {power_soc_w:.1f}W (SOC) + 4W (sistema)"
            else:
                consumo_actual = 8
                fuente = "Estimado (idle típico)"
                help_text = "⚠️ Valor por defecto"
        
        st.metric(
            "⚡ Consumo Actual",
            f"{consumo_actual:.1f}W",
            delta=fuente,
            delta_color="off",
            help=help_text
        )

    # ====================================================================
    # PROYECCIÓN DE COSTES SI SIGUE ASÍ
    # ====================================================================

    st.markdown("---")
    st.markdown(f"**📊 Proyección si el sistema sigue a {consumo_actual:.1f}W:**")

    # Calcular proyecciones
    kwh_hora = consumo_actual / 1000
    coste_hora = kwh_hora * precio_kwh
    
    # Día
    kwh_dia = kwh_hora * 24
    coste_dia = coste_hora * 24
    co2_dia = kwh_dia * KG_CO2_PER_KWH
    
    # Mes
    kwh_mes = kwh_dia * 30
    coste_mes = coste_dia * 30
    co2_mes = kwh_mes * KG_CO2_PER_KWH
    
    # Año
    kwh_ano = kwh_dia * 365
    coste_ano = coste_dia * 365
    co2_ano = kwh_ano * KG_CO2_PER_KWH

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📅 Día (24h)**")
        st.metric("Consumo", f"{kwh_dia:.2f} kWh")
        st.metric("Coste", f"{coste_dia:.3f} €")
        st.metric("CO₂", f"{co2_dia:.2f} kg")

    with col2:
        st.markdown("**📅 Mes (30 días)**")
        st.metric("Consumo", f"{kwh_mes:.1f} kWh")
        st.metric("Coste", f"{coste_mes:.2f} €")
        st.metric("CO₂", f"{co2_mes:.2f} kg")

    with col3:
        st.markdown("**📅 Año (365 días)**")
        st.metric("Consumo", f"{kwh_ano:.1f} kWh")
        st.metric("Coste", f"{coste_ano:.2f} €")
        st.metric("CO₂", f"{co2_ano/1000:.3f} t")

    # ====================================================================
    # TABLA DE ESCENARIOS
    # ====================================================================

    st.markdown("---")
    st.markdown("**📊 Escenarios de Uso (Jetson AGX Orin 64GB):**")

    escenarios_data = {
        'Escenario': [
            '💤 Idle 24/7',
            '📊 Uso ligero',
            '🔥 Inferencia RAG',
            '⚡ Carga máxima'
        ],
        'Consumo (W)': [8, 20, 40, 55],
        'RAM (GB)': [6, 12, 32, 56],
        'GPU (%)': ['0', '5-15', '70-85', '95-100'],
        'Coste/Hora (€)': [],
        'Coste/Día (€)': [],
        'Coste/Mes (€)': []
    }

    for consumo in escenarios_data['Consumo (W)']:
        kwh = consumo / 1000
        coste_h = kwh * precio_kwh
        escenarios_data['Coste/Hora (€)'].append(f"{coste_h:.4f}")
        escenarios_data['Coste/Día (€)'].append(f"{coste_h * 24:.3f}")
        escenarios_data['Coste/Mes (€)'].append(f"{coste_h * 24 * 30:.2f}")

    df_escenarios = pd.DataFrame(escenarios_data)
    st.dataframe(df_escenarios, use_container_width=True, hide_index=True)

    # ====================================================================
    # COSTE ESTIMADO DEL TFG
    # ====================================================================

    st.markdown("---")
    st.markdown("**💰 Coste Estimado del TFG:**")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Conservador: 20h idle + 4h activo
        kwh_idle = (8 / 1000) * 20
        kwh_activo = (40 / 1000) * 4
        kwh_dia_cons = kwh_idle + kwh_activo
        coste_dia_cons = kwh_dia_cons * precio_kwh
        co2_dia_cons = kwh_dia_cons * KG_CO2_PER_KWH
        
        st.info(f"""
        **Escenario Conservador**
        
        - Idle 20h/día: 8W
        - Uso activo 4h/día: 40W
        
        **Coste:**
        - Día: {coste_dia_cons:.3f}€
        - Mes: {coste_dia_cons * 30:.2f}€
        - Año: {coste_dia_cons * 365:.2f}€
        
        **Huella CO₂:**
        - Día: {co2_dia_cons:.2f} kg
        - Año: {co2_dia_cons * 365:.2f} kg
        """)

    with col2:
        # Moderado: 16h idle + 8h activo
        kwh_idle = (8 / 1000) * 16
        kwh_activo = (40 / 1000) * 8
        kwh_dia_mod = kwh_idle + kwh_activo
        coste_dia_mod = kwh_dia_mod * precio_kwh
        co2_dia_mod = kwh_dia_mod * KG_CO2_PER_KWH
        
        st.info(f"""
        **Escenario Moderado**
        
        - Idle 16h/día: 8W
        - Uso activo 8h/día: 40W
        
        **Coste:**
        - Día: {coste_dia_mod:.3f}€
        - Mes: {coste_dia_mod * 30:.2f}€
        - Año: {coste_dia_mod * 365:.2f}€
        
        **Huella CO₂:**
        - Día: {co2_dia_mod:.2f} kg
        - Año: {co2_dia_mod * 365:.2f} kg
        """)

    with col3:
        # Intensivo: 12h idle + 12h activo
        kwh_idle = (8 / 1000) * 12
        kwh_activo = (40 / 1000) * 12
        kwh_dia_int = kwh_idle + kwh_activo
        coste_dia_int = kwh_dia_int * precio_kwh
        co2_dia_int = kwh_dia_int * KG_CO2_PER_KWH
        
        st.info(f"""
        **Escenario Intensivo**
        
        - Idle 12h/día: 8W
        - Uso activo 12h/día: 40W
        
        **Coste:**
        - Día: {coste_dia_int:.3f}€
        - Mes: {coste_dia_int * 30:.2f}€
        - Año: {coste_dia_int * 365:.2f}€
        
        **Huella CO₂:**
        - Día: {co2_dia_int:.2f} kg
        - Año: {co2_dia_int * 365:.2f} kg
        """)

    # ========================================================================
    # SECCIÓN 1: CONTROL DE MONITOREO
    # ========================================================================
    
    st.markdown("---")
    st.subheader("📊 Control de Monitoreo Tegrastats")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        intervalo_ms = st.number_input(
            "Intervalo (ms):",
            min_value=100,
            max_value=2000,
            value=500,
            step=100,
            help="Frecuencia de muestreo de tegrastats"
        )
    
    with col2:
        if not gpu_state['monitoring']:
            if st.button("🟢 Iniciar Monitoreo", type="primary", key="start_monitor"):
                # Limpiar procesos anteriores
                subprocess.run("pkill -f tegrastats 2>/dev/null", shell=True)
                time.sleep(1)
                
                # Crear directorio logs
                log_dir = "./logs/gpu_monitoring"
                Path(log_dir).mkdir(parents=True, exist_ok=True)
                
                # Timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = f"{log_dir}/tegrastats_{timestamp}.log"
                
                # Iniciar tegrastats
                cmd = f"tegrastats --interval {intervalo_ms} > {log_file} 2>&1 &"
                subprocess.Popen(cmd, shell=True, start_new_session=True)
                
                # Actualizar estado
                gpu_state['monitoring'] = True
                gpu_state['log_file'] = log_file
                gpu_state['start_time'] = datetime.now()
                
                st.success(f"✅ Monitoreo iniciado: {log_file}")
                st.rerun()
        else:
            st.info(f"🟢 Monitoreo activo desde {gpu_state['start_time'].strftime('%H:%M:%S')}")
    
    with col3:
        if gpu_state['monitoring']:
            if st.button("🔴 Detener Monitoreo", type="secondary", key="stop_monitor"):
                # Detener tegrastats
                subprocess.run("pkill -f tegrastats", shell=True)
                time.sleep(1)
                
                # Actualizar estado
                gpu_state['monitoring'] = False
                
                st.success("✅ Monitoreo detenido")
                st.rerun()
    
    st.markdown("---")
    
    # ========================================================================
    # SECCIÓN 2: LOGS EN TIEMPO REAL
    # ========================================================================
    
    if gpu_state['monitoring'] and gpu_state['log_file']:
        st.subheader("📜 Logs en Tiempo Real")
        
        # Placeholder para logs
        log_placeholder = st.empty()
        
        # Botón para refrescar
        col1, col2 = st.columns([1, 4])
        with col1:
            auto_refresh_logs = st.checkbox("Auto-refresh", value=True, key="auto_refresh_logs")
        
        # Leer últimas líneas del log
        try:
            if Path(gpu_state['log_file']).exists():
                with open(gpu_state['log_file'], 'r') as f:
                    lines = f.readlines()
                
                # Mostrar últimas 10 líneas
                recent_lines = lines[-10:] if len(lines) > 10 else lines
                
                log_text = "```\n"
                for line in recent_lines:
                    log_text += line
                log_text += "```"
                
                log_placeholder.markdown(log_text)
                
                # Info
                duracion = (datetime.now() - gpu_state['start_time']).total_seconds()
                st.caption(f"📊 {len(lines)} muestras | ⏱️ {duracion:.0f}s | 📁 {Path(gpu_state['log_file']).stat().st_size / 1024:.1f} KB")
                
                # Auto-refresh
                if auto_refresh_logs:
                    time.sleep(2)
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error leyendo log: {e}")
    
    else:
        st.info("💡 Inicia el monitoreo para ver logs en tiempo real")
    
    st.markdown("---")
    
    # ========================================================================
    # SECCIÓN 3: ESTADÍSTICAS Y GRÁFICAS CON COSTE
    # ========================================================================

    st.subheader("📈 Análisis de Estadísticas y Sostenibilidad")

    col1, col2 = st.columns([1, 3])

    with col1:
        # Selector de log a analizar
        log_dir = "./logs/gpu_monitoring"
        if Path(log_dir).exists():
            log_files = sorted(Path(log_dir).glob("tegrastats_*.log"), reverse=True)
            
            if log_files:
                log_options = {f.name: str(f) for f in log_files[:10]}  # Últimos 10
                
                selected_log_name = st.selectbox(
                    "Seleccionar log:",
                    options=list(log_options.keys()),
                    key="select_log_analysis"
                )
                
                selected_log = log_options[selected_log_name]
                
                analizar_btn = st.button("📊 Analizar", type="primary", key="analyze_log")
            else:
                st.warning("No hay logs disponibles")
                analizar_btn = False
        else:
            st.warning("Directorio de logs no existe")
            analizar_btn = False

    with col2:
        if analizar_btn and selected_log:
            with st.spinner("🔍 Analizando log..."):
                # Leer log
                with open(selected_log, 'r') as f:
                    lines = f.readlines()
                
                # Parsear datos
                gpu_usage = []
                ram_usage = []
                cpu_usage = []
                temperatures = []
                power = []
                
                for line in lines:
                    metrics = parse_tegrastats_line(line)
                    
                    # Solo añadir si tiene datos válidos
                    if metrics['gpu_usage'] > 0 or metrics['ram_total'] > 0:
                        gpu_usage.append(metrics['gpu_usage'])
                        
                        if metrics['ram_total'] > 0:
                            ram_percent = (metrics['ram_used'] / metrics['ram_total']) * 100
                            ram_usage.append(ram_percent)
                        
                        cpu_usage.append(metrics['cpu_avg'])
                        temperatures.append(metrics['temp_tj'])
                        power.append(metrics['power_mw'])
                
                # Mostrar métricas
                if gpu_usage or ram_usage:
                    
                    # Calcular duracion del experimento
                    duracion_muestras = len(power)
                    intervalo_segundos = 0.5  # 500ms
                    duracion_total_segundos = duracion_muestras * intervalo_segundos
                    duracion_minutos = duracion_total_segundos / 60
                    
                    # Potencia promedio
                    avg_power_mw = sum(power) / len(power) if power else 0
                    avg_power_w = avg_power_mw / 1000
                    
                    # ✅ CAMBIO PRINCIPAL: Calcular coste si se MANTIENE esta potencia continua
                    # No repetir el experimento, sino mantener la carga
                    
                    # 12 horas continuas a esta potencia
                    duracion_12h_segundos = 12 * 3600
                    resultado_12h = calcular_coste_y_huella(avg_power_w, duracion_12h_segundos, precio_kwh)
                    
                    # 24 horas continuas a esta potencia
                    duracion_24h_segundos = 24 * 3600
                    resultado_24h = calcular_coste_y_huella(avg_power_w, duracion_24h_segundos, precio_kwh)
                    
                    # Coste del experimento actual (lo que realmente ocurrió)
                    resultado_experimento = calcular_coste_y_huella(avg_power_w, duracion_total_segundos, precio_kwh)
                    
                    st.markdown("### 💰 Coste y Sostenibilidad del Experimento")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "⏱️ Duración Real",
                            f"{duracion_minutos:.1f} min",
                            help=f"{duracion_total_segundos:.0f} segundos de monitoreo"
                        )
                    
                    with col2:
                        st.metric(
                            "⚡ Potencia Promedio",
                            f"{avg_power_w:.1f}W",
                            help=f"Basado en {len(power)} muestras"
                        )
                    
                    with col3:
                        st.metric(
                            "💰 Coste Real",
                            f"{resultado_experimento['coste']:.4f}€",
                            help=f"Del experimento de {duracion_minutos:.1f} min"
                        )
                    
                    with col4:
                        st.metric(
                            "🌱 CO₂ Real",
                            f"{resultado_experimento['co2_kg']:.3f} kg",
                            help=f"Huella del experimento real"
                        )
                    
                    # Proyección si SE MANTIENE esta carga continua
                    st.markdown("---")
                    st.markdown(f"**📊 Proyección si MANTIENES esta carga ({avg_power_w:.1f}W) de forma continua:**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"""
                        **Escenario 12h/día continuas**
                        
                        Si mantienes GPU a {avg_power_w:.1f}W durante 12h/día:
                        
                        **Por día:**
                        - Consumo: {resultado_12h['kwh']:.3f} kWh
                        - Coste: {resultado_12h['coste']:.3f}€
                        - CO₂: {resultado_12h['co2_kg']:.3f} kg
                        
                        **Por mes (30 días):**
                        - Consumo: {resultado_12h['kwh'] * 30:.2f} kWh
                        - Coste: {resultado_12h['coste'] * 30:.2f}€
                        - CO₂: {resultado_12h['co2_kg'] * 30:.2f} kg
                        
                        **Por año:**
                        - Consumo: {resultado_12h['kwh'] * 365:.1f} kWh
                        - Coste: {resultado_12h['coste'] * 365:.2f}€
                        - CO₂: {resultado_12h['co2_kg'] * 365 / 1000:.3f} toneladas
                        """)
                    
                    with col2:
                        st.warning(f"""
                        **Escenario 24h/día continuas**
                        
                        Si mantienes GPU a {avg_power_w:.1f}W durante 24h/día:
                        
                        **Por día:**
                        - Consumo: {resultado_24h['kwh']:.3f} kWh
                        - Coste: {resultado_24h['coste']:.3f}€
                        - CO₂: {resultado_24h['co2_kg']:.3f} kg
                        
                        **Por mes (30 días):**
                        - Consumo: {resultado_24h['kwh'] * 30:.2f} kWh
                        - Coste: {resultado_24h['coste'] * 30:.2f}€
                        - CO₂: {resultado_24h['co2_kg'] * 30:.2f} kg
                        
                        **Por año:**
                        - Consumo: {resultado_24h['kwh'] * 365:.1f} kWh
                        - Coste: {resultado_24h['coste'] * 365:.2f}€
                        - CO₂: {resultado_24h['co2_kg'] * 365 / 1000:.3f} toneladas
                        """)
                    
                    # Comparativa con idle
                    st.markdown("---")
                    st.markdown("**💡 Comparativa con Idle:**")
                    
                    # Calcular idle (8W)
                    idle_12h = calcular_coste_y_huella(8, duracion_12h_segundos, precio_kwh)
                    idle_24h = calcular_coste_y_huella(8, duracion_24h_segundos, precio_kwh)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Incremento 12h vs Idle",
                            f"+{(resultado_12h['coste'] - idle_12h['coste']) * 30:.2f}€/mes",
                            delta=f"{((avg_power_w - 8) / 8 * 100):.0f}% más consumo"
                        )
                    
                    with col2:
                        st.metric(
                            "Incremento 24h vs Idle",
                            f"+{(resultado_24h['coste'] - idle_24h['coste']) * 30:.2f}€/mes",
                            delta=f"{((avg_power_w - 8) / 8 * 100):.0f}% más consumo"
                        )
                    
                    with col3:
                        # Calcular "eficiencia": trabajo útil (GPU usage) vs consumo extra
                        gpu_avg = sum(gpu_usage) / len(gpu_usage) if gpu_usage else 0
                        eficiencia = (gpu_avg / 100) / ((avg_power_w - 8) / 8) if avg_power_w > 8 else 0
                        
                        st.metric(
                            "Eficiencia Energética",
                            f"{eficiencia:.2f}",
                            help="GPU Usage / Incremento de potencia vs idle"
                        )
                    
                    # Métricas generales del experimento
                    st.markdown("---")
                    st.markdown("### 📊 Métricas del Experimento")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if gpu_usage:
                            st.metric(
                                "GPU Promedio",
                                f"{sum(gpu_usage)/len(gpu_usage):.1f}%",
                                delta=f"Max: {max(gpu_usage)}%"
                            )
                    
                    with col2:
                        if ram_usage:
                            st.metric(
                                "RAM Promedio",
                                f"{sum(ram_usage)/len(ram_usage):.1f}%",
                                delta=f"Max: {max(ram_usage):.1f}%"
                            )
                    
                    with col3:
                        if temperatures:
                            st.metric(
                                "Temp Promedio",
                                f"{sum(temperatures)/len(temperatures):.1f}°C",
                                delta=f"Max: {max(temperatures):.1f}°C"
                            )
                    
                    with col4:
                        max_w = max(power) / 1000
                        st.metric(
                            "Potencia Máxima",
                            f"{max_w:.1f}W",
                            delta=f"+{max_w - avg_power_w:.1f}W vs promedio"
                        )
                    
                    # Gráficas
                    st.markdown("---")
                    st.markdown("### 📊 Gráficas del Experimento")
                    
                    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
                    
                    # GPU
                    if gpu_usage:
                        time_axis = np.arange(len(gpu_usage)) * 0.5  # 500ms interval
                        ax1.plot(time_axis, gpu_usage, color='#2E86AB', linewidth=2)
                        ax1.fill_between(time_axis, gpu_usage, alpha=0.3, color='#2E86AB')
                        ax1.set_title('GPU Usage (%)', fontweight='bold')
                        ax1.set_xlabel('Tiempo (s)')
                        ax1.set_ylabel('Uso (%)')
                        ax1.grid(alpha=0.3)
                        ax1.set_ylim(0, 100)
                    
                    # RAM
                    if ram_usage:
                        time_axis = np.arange(len(ram_usage)) * 0.5
                        ax2.plot(time_axis, ram_usage, color='#A23B72', linewidth=2)
                        ax2.fill_between(time_axis, ram_usage, alpha=0.3, color='#A23B72')
                        ax2.set_title('RAM Usage (%)', fontweight='bold')
                        ax2.set_xlabel('Tiempo (s)')
                        ax2.set_ylabel('Uso (%)')
                        ax2.grid(alpha=0.3)
                        ax2.set_ylim(0, 100)
                    
                    # Temperatura
                    if temperatures:
                        time_axis = np.arange(len(temperatures)) * 0.5
                        ax3.plot(time_axis, temperatures, color='#F18F01', linewidth=2)
                        ax3.fill_between(time_axis, temperatures, alpha=0.3, color='#F18F01')
                        ax3.set_title('Temperatura Junction (°C)', fontweight='bold')
                        ax3.set_xlabel('Tiempo (s)')
                        ax3.set_ylabel('Temperatura (°C)')
                        ax3.grid(alpha=0.3)
                        ax3.axhline(y=85, color='red', linestyle='--', alpha=0.5, label='Límite 85°C')
                        ax3.legend()
                    
                    # Potencia
                    if power:
                        time_axis = np.arange(len(power)) * 0.5
                        power_w = [p/1000 for p in power]
                        ax4.plot(time_axis, power_w, color='#06A77D', linewidth=2)
                        ax4.fill_between(time_axis, power_w, alpha=0.3, color='#06A77D')
                        ax4.axhline(y=avg_power_w, color='red', linestyle='--', alpha=0.7, 
                                label=f'Promedio: {avg_power_w:.1f}W')
                        ax4.set_title('Potencia GPU (W)', fontweight='bold')
                        ax4.set_xlabel('Tiempo (s)')
                        ax4.set_ylabel('Potencia (W)')
                        ax4.grid(alpha=0.3)
                        ax4.legend()
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Guardar gráfica
                    fig_path = f"./logs/gpu_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
                    
                    with open(fig_path, 'rb') as f:
                        st.download_button(
                            label="💾 Descargar Gráfica",
                            data=f,
                            file_name=f"gpu_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                            mime="image/png"
                        )
                
                else:
                    st.warning("No se pudieron extraer métricas del log")
    
    # ========================================================================
    # SECCIÓN 4: LIMPIEZA DE MEMORIA
    # ========================================================================
    
    st.subheader("🧹 Gestión de Memoria")

    # Limpieza completa
    st.markdown("---")
    st.markdown("#### Limpieza Completa (GPU + Ollama + System Cache)")
    
    if st.button("🔥 Limpieza Completa", type="primary", key="full_cleanup"):
        with st.spinner("Ejecutando limpieza completa..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 1. Python GC
                status_text.text("1/5 Liberando memoria Python...")
                import gc
                collected = gc.collect()
                progress_bar.progress(20)
                
                # 2. CUDA
                status_text.text("2/5 Limpiando CUDA cache...")
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                progress_bar.progress(40)
                
                # 3. Detener Ollama
                status_text.text("3/5 Deteniendo Ollama...")
                subprocess.run(['sudo', 'systemctl', 'stop', 'ollama'], 
                             capture_output=True)
                subprocess.run(['sudo', 'pkill', '-9', '-f', 'ollama'], 
                             capture_output=True)
                time.sleep(2)
                progress_bar.progress(60)
                
                # 4. System cache
                status_text.text("4/5 Limpiando system cache...")
                subprocess.run(['sync'], check=True)
                
                # Limpieza agresiva (echo 3 = todo)
                subprocess.run(['sudo', 'bash', '-c', 'echo 3 > /proc/sys/vm/drop_caches'],
                             capture_output=True, text=True)
                
                progress_bar.progress(80)
                
                # 5. Reiniciar Ollama
                status_text.text("5/5 Reiniciando Ollama...")
                subprocess.run(['sudo', 'systemctl', 'start', 'ollama'], 
                             capture_output=True, text=True)
                time.sleep(5)
                progress_bar.progress(100)
                
                status_text.empty()
                st.success("✅ Limpieza completa ejecutada correctamente")
                
                # Botón para refrescar estado
                if st.button("🔄 Actualizar Estado", key="refresh_after_cleanup"):
                    st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error durante limpieza: {e}")

    # ====================================================================
    # DETALLES EXPANDIBLES
    # ====================================================================

    st.markdown("---")
    
    with st.expander("🔍 Ver Detalles Técnicos"):
        
        # Tegrastats raw
        if st.session_state.tegra_data:
            st.markdown("**✅ Tegrastats Data:**")
            
            # Crear copia con valores formateados
            data_display = st.session_state.tegra_data.copy()
            
            # Añadir valores calculados
            data_display['_power_soc_w'] = f"{data_display['power_mw'] / 1000:.2f} W"
            data_display['_power_total_w'] = f"{data_display['power_total_mw'] / 1000:.2f} W"
            data_display['_ram_percent'] = f"{(data_display['ram_used'] / data_display['ram_total'] * 100):.1f}%" if data_display['ram_total'] > 0 else "N/A"
            
            st.json(data_display)
            
            # Mostrar línea raw de tegrastats
            if st.checkbox("Ver línea raw de tegrastats", key="show_raw_tegra"):
                try:
                    if hasattr(st.session_state, 'ultima_linea_tegra'):
                        st.code(st.session_state.ultima_linea_tegra, language=None)
                    else:
                        st.info("Línea raw no disponible")
                except:
                    st.info("Línea raw no disponible")
        
        else:
            st.markdown("**❌ Tegrastats No Disponible**")
            
            if hasattr(st.session_state, 'tegra_error') and st.session_state.tegra_error:
                st.error(f"Error: {st.session_state.tegra_error}")
        
        # CUDA details
        if st.session_state.cuda_data:
            st.markdown("---")
            st.markdown("**🔥 CUDA Memory Details:**")
            st.json(st.session_state.cuda_data)
        
        # RAM details
        if st.session_state.ram_data:
            st.markdown("---")
            st.markdown("**🧠 RAM Details:**")
            st.json(st.session_state.ram_data)
        
        # Raw free output
        st.markdown("---")
        st.markdown("**📋 Free Command Output:**")
        result = subprocess.run(['free', '-h'], capture_output=True, text=True)
        st.code(result.stdout, language=None)
    
    # ====================================================================
    # AUTO-REFRESH DEL ESTADO PRINCIPAL
    # ====================================================================
    
    if auto_refresh:
        time.sleep(5)
        st.rerun()