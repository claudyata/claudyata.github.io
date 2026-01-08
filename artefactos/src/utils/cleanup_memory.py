"""
cleanup_memory.py
=================

Script para limpiar memoria GPU/RAM en Jetson AGX Orin.
Ejecutar antes de pipelines pesados (traducción, RAG).

Autor: Pedro José García Fernández
Fecha: 27 Diciembre 2024
Proyecto: Cl@udiata TFG


(uoc) claudia@ubuntu:~/claudia-data-tfg/scripts/rag_system$ ps aux --sort=-%mem | head -20 | grep oll
ollama    103137  6.2 33.5 68251556 21602544 ?   Sl   11:36   0:18 /usr/local/bin/ollama runner --model /usr/share/ollama/.ollama/models/blobs/sha256-eabc98a9bcbfce7fd70f3e07de599f8fda98120fefed5881934161ede8bd1a41 --port 35751
ollama    102839  0.1  0.2 2521028 144364 ?      Ssl  11:17   0:02 /usr/local/bin/ollama serve
(uoc) claudia@ubuntu:~/claudia-data-tfg/scripts/rag_system$ ollama ps
NAME           ID              SIZE     PROCESSOR    CONTEXT    UNTIL
qwen2.5:32b    9f13ba1299af    20 GB    100% GPU     4096       About a minute from now
(uoc) claudia@ubuntu:~/claudia-data-tfg/scripts/rag_system$ free -h
               total        used        free      shared  buff/cache   available
Mem:            61Gi        30Gi       8,9Gi        36Mi        21Gi        30Gi
Swap:           30Gi       354Mi        30Gi

(uoc) claudia@ubuntu:~/claudia-data-tfg/scripts/rag_system$ sudo systemctl restart ollama
(uoc) claudia@ubuntu:~/claudia-data-tfg/scripts/rag_system$ sudo sh -c "sync; echo 3 > /proc/sys/vm/drop_caches"

"""

import subprocess
import gc
import time
import sys
import torch
import re
from datetime import datetime

def limpiar_gpu_completo():
    """Limpia GPU + reinicia Ollama"""
    print("=" * 80)
    print("🔥 LIMPIEZA COMPLETA GPU + OLLAMA")
    print("=" * 80)
    
    # 1. Python garbage collector
    print("\n1️⃣ Liberando memoria Python...")
    collected = gc.collect()
    print(f"   ✅ {collected} objetos liberados")
    
    # 2. Limpiar CUDA si está disponible
    try:
        import torch
        if torch.cuda.is_available():
            print("\n2️⃣ Limpiando CUDA cache...")
            before = torch.cuda.memory_allocated(0) / 1e9
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            after = torch.cuda.memory_allocated(0) / 1e9
            print(f"   ✅ CUDA: {before:.2f}GB → {after:.2f}GB")
    except ImportError:
        print("\n2️⃣ PyTorch no disponible, saltando CUDA")
    
    # 3. Detener Ollama
    print("\n3️⃣ Deteniendo Ollama...")
    subprocess.run(['pkill', '-f', 'ollama'], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL)
    time.sleep(2)
    print("   ✅ Ollama detenido")
    
    # 4. Verificar GPU libre
    print("\n4️⃣ Verificando GPU...")
    result = subprocess.run(['nvidia-smi'], 
                           capture_output=True, 
                           text=True)
    if 'ollama' in result.stdout.lower() or 'python' in result.stdout.lower():
        print("   ⚠️  Aún hay procesos en GPU")
    else:
        print("   ✅ GPU libre")
    
    # 5. Reiniciar Ollama
    print("\n5️⃣ Reiniciando Ollama...")
    subprocess.Popen(['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
    time.sleep(5)
    print("   ✅ Ollama reiniciado")
    
    # 6. Verificar Ollama
    try:
        from ollama import Client
        client = Client(host="http://192.168.1.22:11434")
        response = client.list()
        print(f"\n6️⃣ Ollama OK: {len(response.models)} modelos disponibles")
    except Exception as e:
        print(f"\n6️⃣ ⚠️  Ollama error: {e}")
        print("   💡 Espera 10s y reintenta")
    
    print("\n" + "=" * 80)
    print("✅ Limpieza completada")
    print("💡 Espera 10 segundos antes de ejecutar código pesado")
    print("=" * 80)

def ver_memoria_rapido():
    """
    Muestra estado de memoria RAM y GPU usando tegrastats (Jetson-optimizado)
    """
    print("=" * 80)
    print("💾 ESTADO DE MEMORIA (Jetson AGX Orin)")
    print("=" * 80)
    
    # Memoria RAM con free
    print("\n🧠 RAM (free -h):")
    print("-" * 80)
    result = subprocess.run(['free', '-h'], capture_output=True, text=True)
    print(result.stdout)
    
    # Tegrastats (snapshot único)
    print("\n🎮 GPU + SOC (tegrastats):")
    print("-" * 80)
    
    try:
        # Ejecutar tegrastats por 1 segundo
        result = subprocess.run(['tegrastats', '--interval', '500'], 
                               capture_output=True, text=True, timeout=2)
        
        lines = result.stdout.strip().split('\n')
        if lines:
            ultima_linea = lines[-1]  # Última medición
            
            # Parsear tegrastats (formato Jetson AGX Orin)
            print(f"Timestamp: {datetime.now().strftime('%H:%M:%S')}\n")
            
            # RAM
            ram_match = re.search(r'RAM (\d+)/(\d+)MB', ultima_linea)
            if ram_match:
                ram_used = int(ram_match.group(1))
                ram_total = int(ram_match.group(2))
                ram_percent = (ram_used / ram_total) * 100
                print(f"📊 RAM Sistema:")
                print(f"   Usado: {ram_used}MB / {ram_total}MB ({ram_percent:.1f}%)")
                print(f"   Disponible: {ram_total - ram_used}MB")
            
            # GPU
            gpu_match = re.search(r'GR3D_FREQ\s+(\d+)%', ultima_linea)
            if gpu_match:
                gpu_util = int(gpu_match.group(1))
                print(f"\n🎮 GPU (GR3D):")
                print(f"   Uso: {gpu_util}%")
            
            # CPU
            cpu_matches = re.findall(r'CPU\s+\[([^\]]+)\]', ultima_linea)
            if cpu_matches:
                cpu_values = re.findall(r'(\d+)%', cpu_matches[0])
                if cpu_values:
                    cpu_avg = sum(int(v) for v in cpu_values) / len(cpu_values)
                    print(f"\n💻 CPU:")
                    print(f"   Uso promedio: {cpu_avg:.1f}%")
                    print(f"   Cores: {', '.join(cpu_values)}%")
            
            # Potencia
            power_match = re.search(r'VDD_GPU_SOC\s+(\d+)mW', ultima_linea)
            if power_match:
                power_mw = int(power_match.group(1))
                print(f"\n⚡ Potencia GPU:")
                print(f"   Consumo: {power_mw}mW ({power_mw/1000:.2f}W)")
            
            # Temperaturas
            print(f"\n🌡️  Temperaturas:")
            
            # CPU/Junction
            temp_tj = re.search(r'tj@([\d.]+)C', ultima_linea)
            if temp_tj:
                print(f"   CPU/Junction: {temp_tj.group(1)}°C")
            
            # SOC
            temp_socs = re.findall(r'soc\d@([\d.]+)C', ultima_linea)
            if temp_socs:
                soc_avg = sum(float(t) for t in temp_socs) / len(temp_socs)
                print(f"   SOC promedio: {soc_avg:.1f}°C")
    
    except subprocess.TimeoutExpired:
        print("⚠️  tegrastats timeout (normal)")
    except Exception as e:
        print(f"⚠️  Error ejecutando tegrastats: {e}")
        print("   Asegúrate de tener permisos: sudo usermod -aG video $USER")
    
    # CUDA Memory desde PyTorch
    if torch.cuda.is_available():
        print("\n🔥 CUDA Memory (PyTorch):")
        print("-" * 80)
        
        for i in range(torch.cuda.device_count()):
            allocated = torch.cuda.memory_allocated(i) / 1e9
            reserved = torch.cuda.memory_reserved(i) / 1e9
            total = torch.cuda.get_device_properties(i).total_memory / 1e9
            free = total - reserved
            
            print(f"GPU {i} ({torch.cuda.get_device_name(i)}):")
            print(f"   Allocated: {allocated:.2f} GB ({allocated/total*100:.1f}%)")
            print(f"   Reserved:  {reserved:.2f} GB ({reserved/total*100:.1f}%)")
            print(f"   Total:     {total:.2f} GB")
            print(f"   Free:      {free:.2f} GB ({free/total*100:.1f}%)")
            
            # Advertencia si poca memoria
            if free < 5:
                print(f"   ⚠️  ADVERTENCIA: Solo {free:.1f}GB libres!")
            print()
    
    print("=" * 80)

def ver_memoria_rapido_():
    """Vista rápida de memoria"""
    print("\n📊 Estado Memoria:")
    
    # RAM
    result = subprocess.run(['free', '-h'], capture_output=True, text=True)
    lines = result.stdout.split('\n')[1:2]
    for line in lines:
        print(f"   {line}")
    
    # GPU
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0) / 1e9
            total = torch.cuda.get_device_properties(0).total_memory / 1e9
            free = total - allocated
            print(f"\n   GPU: {allocated:.1f}GB usado / {total:.1f}GB total")
            print(f"        {free:.1f}GB libres ({free/total*100:.1f}%)")
    except:
        pass


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpiar memoria Jetson')
    parser.add_argument('--quick', action='store_true', 
                       help='Solo ver estado, no limpiar')
    args = parser.parse_args()
    
    if args.quick:
        ver_memoria_rapido()
    else:
        limpiar_gpu_completo()
        ver_memoria_rapido()