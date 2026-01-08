"""
gpu_monitor.py
==============

Sistema de monitoreo GPU con tegrastats para Jetson AGX Orin.
Gestión automática de logs con limpieza y análisis de métricas.

Funcionalidades:
- Monitoreo continuo en background
- Limpieza automática de logs antiguos
- Análisis de métricas (GPU%, RAM, temperaturas, potencia)
- Resúmenes estadísticos

Autor: Pedro José García Fernández
Fecha: 27 Diciembre 2024
Proyecto: Cl@udiata TFG
"""

import subprocess
import time
import os
import glob
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DEFAULT_LOG_DIR = "./log/gpu_monitoring"
DEFAULT_INTERVAL_MS = 500
DEFAULT_KEEP_LOGS = 3


# ============================================================================
# FUNCIONES DE MONITOREO
# ============================================================================

def iniciar_monitoreo_gpu(
    intervalo_ms: int = DEFAULT_INTERVAL_MS,
    log_dir: str = DEFAULT_LOG_DIR,
    mantener_ultimos: int = DEFAULT_KEEP_LOGS
) -> Dict:
    """
    Inicia monitoreo GPU con tegrastats en background.
    Limpia logs antiguos automáticamente.
    
    Args:
        intervalo_ms: Intervalo de muestreo en milisegundos (default: 500)
        log_dir: Directorio donde guardar logs (default: /tmp/gpu_monitoring)
        mantener_ultimos: Número de logs anteriores a mantener (default: 3)
    
    Returns:
        dict: Información del monitoreo
            - 'log_file': Ruta del archivo de log
            - 'timestamp': Timestamp del inicio
            - 'pid': PID del proceso tegrastats
            - 'estado': True si inició correctamente, False si falló
            - 'logs_eliminados': Número de logs antiguos eliminados
    """
    # Silenciar warnings
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    # Crear directorio
    os.makedirs(log_dir, exist_ok=True)
    
    print("=" * 80)
    print("🔧 INICIANDO MONITOREO GPU")
    print("=" * 80)
    
    # === LIMPIAR LOGS ANTIGUOS ===
    print("\n🧹 Limpiando logs antiguos...")
    
    patron_logs = os.path.join(log_dir, "tegrastats_*.log")
    logs_existentes = sorted(glob.glob(patron_logs), reverse=True)
    
    logs_eliminados = 0
    if len(logs_existentes) > mantener_ultimos:
        logs_a_eliminar = logs_existentes[mantener_ultimos:]
        
        print(f"   Encontrados {len(logs_existentes)} logs")
        print(f"   Manteniendo los {mantener_ultimos} más recientes")
        print(f"   Eliminando {len(logs_a_eliminar)} logs antiguos...")
        
        for log in logs_a_eliminar:
            try:
                os.remove(log)
                logs_eliminados += 1
                print(f"   ✅ Eliminado: {os.path.basename(log)}")
            except Exception as e:
                print(f"   ⚠️ Error eliminando {os.path.basename(log)}: {e}")
    else:
        print(f"   Solo hay {len(logs_existentes)} logs, no se elimina nada")
    
    # === LIMPIAR PROCESOS ANTERIORES ===
    print("\n🧹 Limpiando procesos tegrastats anteriores...")
    subprocess.run("pkill -f tegrastats 2>/dev/null", shell=True)
    time.sleep(1)
    
    # === INICIAR NUEVO MONITOREO ===
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/tegrastats_{timestamp}.log"
    
    print(f"\n📊 Configurando monitoreo:")
    print(f"   Intervalo: {intervalo_ms}ms")
    print(f"   Log: {log_file}")
    
    cmd = f"tegrastats --interval {intervalo_ms} > {log_file} 2>&1 &"
    
    subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setpgrp
    )
    
    # Esperar inicio
    time.sleep(2)
    
    # Verificar que está corriendo
    check = subprocess.run(
        "ps aux | grep '[t]egrastats'",
        shell=True,
        capture_output=True,
        text=True
    )
    
    resultado = {
        'log_file': log_file,
        'timestamp': timestamp,
        'pid': None,
        'estado': False,
        'logs_eliminados': logs_eliminados
    }
    
    if check.stdout:
        pid = check.stdout.split()[1]
        resultado['pid'] = pid
        resultado['estado'] = True
        print(f"\n   ✅ Monitoreo iniciado correctamente")
        print(f"   PID: {pid}")
    else:
        print(f"\n   ❌ Error al iniciar monitoreo")
        print(f"   El análisis continuará sin monitoreo de GPU")
    
    print("=" * 80)
    
    return resultado


def detener_monitoreo_gpu(
    info_monitoreo: Optional[Dict] = None,
    mostrar_resumen: bool = True
) -> Dict:
    """
    Detiene monitoreo GPU y opcionalmente muestra resumen.
    
    Args:
        info_monitoreo: Dict retornado por iniciar_monitoreo_gpu() (opcional)
        mostrar_resumen: Si True, muestra info del log generado (default: True)
    
    Returns:
        dict: Información del cierre
            - 'detenido': True si se detuvo correctamente
            - 'lineas_capturadas': Número de líneas en el log
            - 'duracion_segundos': Duración del monitoreo
    """
    print("\n" + "=" * 80)
    print("🛑 DETENIENDO MONITOREO GPU")
    print("=" * 80)
    
    # Detener tegrastats
    print("\n📊 Finalizando tegrastats...")
    subprocess.run("pkill -f tegrastats", shell=True, 
                  capture_output=True, text=True)
    time.sleep(1)
    
    # Verificar que se detuvo
    check = subprocess.run("ps aux | grep '[t]egrastats'", shell=True,
                         capture_output=True, text=True)
    
    resultado = {
        'detenido': len(check.stdout) == 0,
        'lineas_capturadas': 0,
        'duracion_segundos': 0
    }
    
    if resultado['detenido']:
        print("   ✅ Monitoreo detenido correctamente")
    else:
        print("   ⚠️ Advertencia: proceso tegrastats puede seguir corriendo")
    
    # Mostrar resumen si se proporcionó info
    if info_monitoreo and mostrar_resumen:
        log_file = info_monitoreo['log_file']
        
        if os.path.exists(log_file):
            # Contar líneas
            with open(log_file, 'r') as f:
                lineas = f.readlines()
            
            resultado['lineas_capturadas'] = len(lineas)
            
            # Calcular duración
            duracion = len(lineas) * 0.5
            resultado['duracion_segundos'] = duracion
            
            print(f"\n📄 Resumen del log:")
            print(f"   Archivo: {log_file}")
            print(f"   Líneas capturadas: {len(lineas)}")
            print(f"   Duración estimada: {duracion:.1f} segundos")
            print(f"   Tamaño: {os.path.getsize(log_file) / 1024:.1f} KB")
            
            if len(lineas) > 0:
                print(f"\n📋 Primera línea:")
                print(f"   {lineas[0].strip()[:100]}...")
        else:
            print(f"\n   ⚠️ Log no encontrado: {log_file}")
    
    print("=" * 80)
    
    return resultado


def obtener_ultimo_log(log_dir: str = DEFAULT_LOG_DIR) -> Dict:
    """
    Obtiene la ruta del último log de tegrastats creado.
    
    Args:
        log_dir: Directorio donde buscar logs
    
    Returns:
        dict: Información del último log
    """
    patron_logs = os.path.join(log_dir, "tegrastats_*.log")
    logs_existentes = sorted(glob.glob(patron_logs), reverse=True)
    
    resultado = {
        'log_file': None,
        'timestamp': None,
        'existe': False,
        'lineas': 0,
        'tamaño_kb': 0
    }
    
    if not logs_existentes:
        print(f"⚠️ No se encontraron logs en {log_dir}")
        return resultado
    
    ultimo_log = logs_existentes[0]
    basename = os.path.basename(ultimo_log)
    timestamp = basename.replace('tegrastats_', '').replace('.log', '')
    
    if os.path.exists(ultimo_log):
        with open(ultimo_log, 'r') as f:
            lineas = len(f.readlines())
        
        tamaño = os.path.getsize(ultimo_log) / 1024
        
        resultado = {
            'log_file': ultimo_log,
            'timestamp': timestamp,
            'existe': True,
            'lineas': lineas,
            'tamaño_kb': tamaño
        }
        
        print(f"✅ Último log encontrado:")
        print(f"   Archivo: {ultimo_log}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Líneas: {lineas}")
        print(f"   Tamaño: {tamaño:.1f} KB")
    
    return resultado


def listar_logs(log_dir: str = DEFAULT_LOG_DIR, mostrar: int = 5) -> List[Dict]:
    """
    Lista los logs de tegrastats disponibles.
    
    Args:
        log_dir: Directorio donde buscar logs
        mostrar: Número de logs más recientes a mostrar
    
    Returns:
        list: Lista de dicts con info de cada log
    """
    patron_logs = os.path.join(log_dir, "tegrastats_*.log")
    logs_existentes = sorted(glob.glob(patron_logs), reverse=True)
    
    if not logs_existentes:
        print(f"⚠️ No se encontraron logs en {log_dir}")
        return []
    
    print(f"📁 Logs disponibles en {log_dir}:")
    print(f"   Total: {len(logs_existentes)}")
    print(f"   Mostrando los {min(mostrar, len(logs_existentes))} más recientes:\n")
    
    resultado = []
    
    for i, log_path in enumerate(logs_existentes[:mostrar], 1):
        basename = os.path.basename(log_path)
        timestamp = basename.replace('tegrastats_', '').replace('.log', '')
        
        with open(log_path, 'r') as f:
            lineas = len(f.readlines())
        
        tamaño = os.path.getsize(log_path) / 1024
        duracion = lineas * 0.5
        
        info = {
            'log_file': log_path,
            'timestamp': timestamp,
            'lineas': lineas,
            'tamaño_kb': tamaño,
            'duracion_seg': duracion
        }
        
        resultado.append(info)
        
        print(f"   {i}. {basename}")
        print(f"      Timestamp: {timestamp}")
        print(f"      Líneas: {lineas} | Duración: {duracion:.1f}s | Tamaño: {tamaño:.1f}KB\n")
    
    if len(logs_existentes) > mostrar:
        print(f"   ... y {len(logs_existentes) - mostrar} logs más antiguos")
    
    return resultado


# ============================================================================
# ANÁLISIS DE LOGS
# ============================================================================

def analizar_log(log_file: str) -> Dict:
    """
    Analiza un log de tegrastats y extrae estadísticas.
    
    Args:
        log_file: Ruta al archivo de log
    
    Returns:
        dict: Estadísticas extraídas
    """
    if not os.path.exists(log_file):
        return {'error': f'Log no encontrado: {log_file}'}
    
    print(f"\n📊 Analizando log: {os.path.basename(log_file)}")
    print("=" * 80)
    
    with open(log_file, 'r') as f:
        lineas = f.readlines()
    
    # Métricas
    gpu_usage = []
    ram_usage = []
    cpu_usage = []
    temperatures = []
    power = []
    
    for linea in lineas:
        # GPU
        gpu_match = re.search(r'GR3D_FREQ\s+(\d+)%', linea)
        if gpu_match:
            gpu_usage.append(int(gpu_match.group(1)))
        
        # RAM
        ram_match = re.search(r'RAM (\d+)/(\d+)MB', linea)
        if ram_match:
            ram_usado = int(ram_match.group(1))
            ram_total = int(ram_match.group(2))
            ram_usage.append((ram_usado / ram_total) * 100)
        
        # CPU (promedio de cores)
        cpu_matches = re.findall(r'(\d+)%', linea)
        if cpu_matches and len(cpu_matches) > 4:  # Típicamente ~12 cores
            cpu_avg = sum(int(x) for x in cpu_matches[:12]) / 12
            cpu_usage.append(cpu_avg)
        
        # Temperatura (junction)
        temp_match = re.search(r'tj@([\d.]+)C', linea)
        if temp_match:
            temperatures.append(float(temp_match.group(1)))
        
        # Potencia
        power_match = re.search(r'VDD_GPU_SOC\s+(\d+)mW', linea)
        if power_match:
            power.append(int(power_match.group(1)))
    
    # Calcular estadísticas
    stats = {
        'duracion_segundos': len(lineas) * 0.5,
        'muestras': len(lineas),
        'gpu': {
            'promedio': sum(gpu_usage) / len(gpu_usage) if gpu_usage else 0,
            'max': max(gpu_usage) if gpu_usage else 0,
            'min': min(gpu_usage) if gpu_usage else 0
        },
        'ram': {
            'promedio': sum(ram_usage) / len(ram_usage) if ram_usage else 0,
            'max': max(ram_usage) if ram_usage else 0,
            'min': min(ram_usage) if ram_usage else 0
        },
        'cpu': {
            'promedio': sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
            'max': max(cpu_usage) if cpu_usage else 0,
            'min': min(cpu_usage) if cpu_usage else 0
        },
        'temperatura': {
            'promedio': sum(temperatures) / len(temperatures) if temperatures else 0,
            'max': max(temperatures) if temperatures else 0,
            'min': min(temperatures) if temperatures else 0
        },
        'potencia_mw': {
            'promedio': sum(power) / len(power) if power else 0,
            'max': max(power) if power else 0,
            'min': min(power) if power else 0
        }
    }
    
    # Mostrar resumen
    print(f"\n⏱️  Duración: {stats['duracion_segundos']:.1f}s ({stats['muestras']} muestras)")
    print(f"\n🎮 GPU:")
    print(f"   Promedio: {stats['gpu']['promedio']:.1f}%")
    print(f"   Max: {stats['gpu']['max']}% | Min: {stats['gpu']['min']}%")
    
    print(f"\n🧠 RAM:")
    print(f"   Promedio: {stats['ram']['promedio']:.1f}%")
    print(f"   Max: {stats['ram']['max']:.1f}% | Min: {stats['ram']['min']:.1f}%")
    
    print(f"\n💻 CPU:")
    print(f"   Promedio: {stats['cpu']['promedio']:.1f}%")
    print(f"   Max: {stats['cpu']['max']:.1f}% | Min: {stats['cpu']['min']:.1f}%")
    
    print(f"\n🌡️  Temperatura:")
    print(f"   Promedio: {stats['temperatura']['promedio']:.1f}°C")
    print(f"   Max: {stats['temperatura']['max']:.1f}°C | Min: {stats['temperatura']['min']:.1f}°C")
    
    print(f"\n⚡ Potencia GPU:")
    print(f"   Promedio: {stats['potencia_mw']['promedio']:.0f}mW ({stats['potencia_mw']['promedio']/1000:.2f}W)")
    print(f"   Max: {stats['potencia_mw']['max']}mW ({stats['potencia_mw']['max']/1000:.2f}W)")
    
    print("=" * 80)
    
    return stats


# ============================================================================
# MAIN - MENÚ INTERACTIVO
# ============================================================================

def main():
    """Menú interactivo para gestión de monitoreo GPU"""
    
    print("=" * 80)
    print("🎮 GPU MONITOR - Jetson AGX Orin")
    print("=" * 80)
    
    while True:
        print("\n📋 MENÚ:")
        print("   1. Iniciar monitoreo")
        print("   2. Detener monitoreo")
        print("   3. Listar logs")
        print("   4. Analizar último log")
        print("   5. Analizar log específico")
        print("   6. Limpiar logs antiguos")
        print("   7. Estado actual (snapshot)")
        print("   0. Salir")
        
        opcion = input("\nSelecciona opción: ").strip()
        
        if opcion == '1':
            # Iniciar monitoreo
            intervalo = input("Intervalo en ms (default 500): ").strip()
            intervalo = int(intervalo) if intervalo else 500
            
            info = iniciar_monitoreo_gpu(intervalo_ms=intervalo)
            print(f"\n💡 Log guardándose en: {info['log_file']}")
            print("   Presiona 2 para detener cuando termines tu tarea")
        
        elif opcion == '2':
            # Detener monitoreo
            ultimo = obtener_ultimo_log()
            if ultimo['existe']:
                detener_monitoreo_gpu(info_monitoreo={'log_file': ultimo['log_file']})
            else:
                detener_monitoreo_gpu()
        
        elif opcion == '3':
            # Listar logs
            num = input("¿Cuántos mostrar? (default 5): ").strip()
            num = int(num) if num else 5
            listar_logs(mostrar=num)
        
        elif opcion == '4':
            # Analizar último
            ultimo = obtener_ultimo_log()
            if ultimo['existe']:
                analizar_log(ultimo['log_file'])
            else:
                print("❌ No hay logs disponibles")
        
        elif opcion == '5':
            # Analizar específico
            logs = listar_logs(mostrar=10)
            if logs:
                idx = input("\nNúmero de log a analizar (1-N): ").strip()
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(logs):
                        analizar_log(logs[idx]['log_file'])
                    else:
                        print("❌ Índice inválido")
                except ValueError:
                    print("❌ Entrada inválida")
        
        elif opcion == '6':
            # Limpiar logs
            mantener = input("¿Cuántos logs mantener? (default 3): ").strip()
            mantener = int(mantener) if mantener else 3
            
            patron_logs = os.path.join(DEFAULT_LOG_DIR, "tegrastats_*.log")
            logs_existentes = sorted(glob.glob(patron_logs), reverse=True)
            
            if len(logs_existentes) > mantener:
                logs_a_eliminar = logs_existentes[mantener:]
                print(f"\n🗑️  Eliminando {len(logs_a_eliminar)} logs...")
                for log in logs_a_eliminar:
                    os.remove(log)
                    print(f"   ✅ {os.path.basename(log)}")
                print(f"\n✅ Limpieza completada")
            else:
                print(f"✅ Solo hay {len(logs_existentes)} logs, nada que eliminar")
        
        elif opcion == '7':
            # Estado actual
            print("\n📊 Capturando snapshot (2 segundos)...")
            info = iniciar_monitoreo_gpu(mantener_ultimos=100)  # No eliminar nada
            time.sleep(2)
            detener_monitoreo_gpu(info, mostrar_resumen=False)
            
            if info['estado']:
                analizar_log(info['log_file'])
        
        elif opcion == '0':
            print("\n👋 Saliendo...")
            break
        
        else:
            print("❌ Opción inválida")


if __name__ == "__main__":
    main()