# Diseño de la tarea: INFRA-20 — Configurar entorno de trabajo

Este documento describe la tarea **[INFRA-20]** dentro del proyecto **Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva**.  
Incluye la descripción, objetivos, planificación, recursos, análisis, riesgos y resultados esperados para que otros estudiantes puedan reproducir el trabajo en su entorno.

---

## Tabla de contenidos
1. [Descripción y Objetivo](#1-descripción-y-objetivo)  
2. [Requisitos / Contexto](#2-requisitos--contexto)  
3. [Procedimiento de instalación y configuración](#3-procedimiento-de-instalación-y-configuración)  
4. [Resultados esperados / Outputs](#4-resultados-esperados--outputs)  
5. [Validación del entorno (Checkpoints)](#5-validación-del-entorno-checkpoints)  
6. [Riesgos / Bloqueos](#6-riesgos--bloqueos)  
7. [Conclusión](#7-conclusión)  
8. [Referencias](#8-referencias)

---

## 1. Descripción y Objetivo

## Descripción
Como estudiante, quiero instalar y configurar un entorno Linux compatible (**JetPack, CUDA, TensorRT**) que permita desarrollar y desplegar proyectos de ciencia de datos modernos, garantizando la ejecución eficiente del agente generativo **Cl@udiata** en el **NVIDIA Jetson AGX Orin Developer Kit**.

## Objetivo
Asegurar que el entorno esté correctamente configurado para soportar todas las herramientas necesarias del proyecto, incluyendo bibliotecas de IA, frameworks de visión por computadora y módulos de análisis de datos.

---

## 2. Requisitos / Contexto

El entorno se ha diseñado para cumplir los siguientes requisitos:

- Compatibilidad con **arquitectura ARM64 (aarch64)** de los dispositivos Jetson.
- Soporte nativo para:
  - **CUDA Toolkit**
  - **TensorRT**
  - **cuDNN**
  - **PyTorch o TensorFlow con CUDA**
- Capacidad para ejecutar modelos ligeros (LLaMA-2, Whisper, Yolov8 INT8).
- Instalación de herramientas de desarrollo:
  - Linux (Ubuntu 22.04 o L4T)
  - SSH, Git, VSCode Remote Development
- Uso eficiente de recursos y bajo consumo energético.

---

## 3. Procedimiento de instalación y configuración

El entorno base del **Jetson AGX Orin** se configura mediante el sistema **JetPack SDK**, el cual incluye las siguientes herramientas esenciales:

| Componente | Descripción | Versión recomendada |
|-------------|--------------|---------------------|
| **Ubuntu for Jetson** | Sistema operativo Linux optimizado para ARM64 | 22.04 LTS |
| **CUDA Toolkit** | Plataforma para computación paralela en GPU | 12.6 |
| **cuDNN** | Librerías de redes neuronales optimizadas para CUDA | 9.16 |
| **TensorRT** | Framework para optimización e inferencia de modelos IA | 10.0 |
| **DeepStream SDK** | Análisis de vídeo y flujos multimedia en tiempo real | 7.0 |
| **Jetson SDK Components** | Drivers, API y herramientas de desarrollo para Edge AI | Incluido en JetPack 6.2 |

Estas herramientas aseguran la compatibilidad total con bibliotecas de IA como **PyTorch**, **TensorFlow**, **OpenCV** y **Transformers** (Hugging Face).

### 3.1 Flashing de la Jetson AGX Orin

- Instalar **SDK Manager** en el host Ubuntu:
  - `sudo apt-get update`
  - `sudo apt-get -y install sdkmanager`
- Poner la Jetson en **modo Recovery**:
  - Apagar el dispositivo.
  - Conectar cable USB-C al puerto Recovery / Flash.
  - Mantener presionado "Force Recovery" y presionar "Power" durante 2 segundos.
  - Soltar ambos botones.
- Abrir **SDK Manager**:
  - `sdkmanager`
- Seguir los pasos dentro del SDK Manager:

| Flasheo del sistema operativo | Imagenes |
|-------------------------------|----------|
| Iniciar sesión con una cuenta de desarrollador de NVIDIA. | <img src="./../../img/jetpack-login.png" width="300"> <img src="./../../img/jetpack-login-2.png" width="300"> |
| STEP 1: Product: Jetson (Jetson AGX Orin [64GB developer kit version]) | <img src="./../../img/jetpack-0.png" width="300"> |
| STEP 1: SDK Version: JetPack 6.2.1 (rev. 1) (Pulse Continuar) | <img src="./../../img/jetpack-2.png" width="300"> <img src="./../../img/jetpack-3.png" width="300"> |
| STEP 2: Selecciona todos las opciones: CUDA, NvSci, Computer Vision, Developer Tools | <img src="./../../img/jetpack-4.png" width="300"> |
| STEP 3: IP: Automático, Usuario: claudia, Storage Device NVMe (Pulse Flash) | <img src="./../../img/jetpack-5.png" width="300"> <img src="./../../img/jetpack-7.png" width="300"> |
| STEP 4: Jetson reiniciará automáticamente con JetPack instalado (Pulse Finish) | <img src="./../../img/jetpack-8.png" width="300"> <img src="./../../img/jetpack-7.png" width="300"> |

### 3.2 Actualización del sistema y herramientas esenciales

Actualizar el Jetson y ejecutar los **CUDA Samples** asegura que el sistema está correctamente configurado, los drivers CUDA funcionan y el dispositivo puede ejecutar kernels y medir el rendimiento de memoria de forma confiable. Esto es crítico antes de iniciar proyectos de IA y visión por computador, garantizando estabilidad y rendimiento. Es por ello que se recomienda ejecutar los siguentes pasos.

- `sudo apt-get update`
- `sudo apt-get upgrade -y`
- `sudo apt install -y git cmake build-essential`
- Configurar PyPI Jetson para instalar paquetes:
  - `pip config set global.index-url https://pypi.jetson-ai-lab.io/jp6/cu126`

### 3.3 Instalación de CUDA Toolkit y Samples

- Descargar e instalar CUDA:
  - `wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/arm64/cuda-ubuntu2204.pin`
  - `sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600`
  - `wget https://developer.download.nvidia.com/compute/cuda/12.6.0/local_installers/cuda-tegra-repo-ubuntu2204-12-6-local_12.6.0-1_arm64.deb`
  - `sudo dpkg -i cuda-tegra-repo-ubuntu2204-12-6-local_12.6.0-1_arm64.deb`
  - `sudo cp /var/cuda-tegra-repo-ubuntu2204-12-6-local/cuda-*-keyring.gpg /usr/share/keyrings/`
  - `sudo apt-get update`
  - `sudo apt-get -y install cuda-toolkit-12-6 cuda-compat-12-6`

- Descargar e instalar cuDNN:
  - `wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/arm64/cuda-ubuntu2204.pin`
  - `wget https://developer.download.nvidia.com/compute/cudnn/9.16.0/local_installers/cudnn-local-tegra-repo-ubuntu2204-9.16.0_1.0-1_arm64.deb`
  - `sudo dpkg -i cudnn-local-tegra-repo-ubuntu2204-9.16.0_1.0-1_arm64.deb`
  - `sudo cp /var/cudnn-local-tegra-repo-ubuntu2204-9.16.0/cudnn-*-keyring.gpg /usr/share/keyrings/`
  - `sudo apt-get update`
  - `sudo apt-get -y install cudnn`

- Descargar **CUDA Samples**:
  - `cd /usr/local`
  - `sudo git clone --branch v12.8 https://github.com/NVIDIA/cuda-samples.git`
  - `sudo chown -R $USER:$USER cuda-samples`

- Crear carpeta de compilación y construir **CUDA Samples**:
  - `cd cuda-samples`
  - Cambia todos los CMakeLists.txt con set(CMAKE_CUDA_ARCHITECTURES 89)
     - `vi CMakeLists.txt`
  - `mkdir build_utils && cd build_utils`
  - `cmake ../Samples/1_Utilities -DCMAKE_CUDA_ARCHITECTURES=89`
  - `make -j$(nproc)`
---

## 4. Resultados esperados / Outputs

- Jetson AGX Orin con JetPack 6.2.1 correctamente flasheado.
- CUDA Toolkit 12.6 instalado y funcionando.
- cuDNN 9.16.0 instalado y funcionando.
- CUDA Samples compilados y ejecutándose con resultados `PASS`.
- Acceso a herramientas de desarrollo: VSCode, Chromium, Cursor IDE.

---

## 5. Validación del entorno (Checkpoints)

- Comprobar versión de CUDA:
  - `nvcc --version`

```yaml
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2024 NVIDIA Corporation
Built on Wed_Aug_14_10:14:07_PDT_2024
Cuda compilation tools, release 12.6, V12.6.68
Build cuda_12.6.r12.6/compiler.34714021_0
```
- Comprobar versión de Python:
  - `python3 --version`
```yaml
Python 3.12.12
```
- Comprobar versión de Python:
  - `dpkg -l | grep tensorrt`

```yaml
ii  tensorrt                                   10.3.0.30-1+cuda12.5                        arm64        Meta package for TensorRT
ii  tensorrt-libs                              10.3.0.30-1+cuda12.5                        arm64        Meta package for TensorRT runtime libraries
```
- Comprobar estado GPU:
  - `nvidia-smi`

```yaml
Mon Nov 17 14:16:04 2025
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 540.4.0                Driver Version: 540.4.0      CUDA Version: 12.6     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
```
- Ejecutar `deviceQuery` y `bandwidthTest` para validar CUDA.

  - `/usr/local/cuda-samples/build_utils/deviceQuery/deviceQuery`

```yaml
/usr/local/cuda-samples/build_utils/deviceQuery/deviceQuery Starting...

 CUDA Device Query (Runtime API) version (CUDART static linking)

Detected 1 CUDA Capable device(s)

Device 0: "Orin"
  CUDA Driver Version / Runtime Version          12.6 / 12.6
  CUDA Capability Major/Minor version number:    8.7
  Total amount of global memory:                 62841 MBytes (65893269504 bytes)
  (008) Multiprocessors, (128) CUDA Cores/MP:    1024 CUDA Cores
  GPU Max Clock rate:                            1300 MHz (1.30 GHz)
  Memory Clock rate:                             612 Mhz
  Memory Bus Width:                              256-bit
  L2 Cache Size:                                 4194304 bytes
  Maximum Texture Dimension Size (x,y,z)         1D=(131072), 2D=(131072, 65536), 3D=(16384, 16384, 16384)
  Maximum Layered 1D Texture Size, (num) layers  1D=(32768), 2048 layers
  Maximum Layered 2D Texture Size, (num) layers  2D=(32768, 32768), 2048 layers
  Total amount of constant memory:               65536 bytes
  Total amount of shared memory per block:       49152 bytes
  Total shared memory per multiprocessor:        167936 bytes
  Total number of registers available per block: 65536
  Warp size:                                     32
  Maximum number of threads per multiprocessor:  1536
  Maximum number of threads per block:           1024
  Max dimension size of a thread block (x,y,z): (1024, 1024, 64)
  Max dimension size of a grid size    (x,y,z): (2147483647, 65535, 65535)
  Maximum memory pitch:                          2147483647 bytes
  Texture alignment:                             512 bytes
  Concurrent copy and kernel execution:          Yes with 2 copy engine(s)
  Run time limit on kernels:                     No
  Integrated GPU sharing Host Memory:            Yes
  Support host page-locked memory mapping:       Yes
  Alignment requirement for Surfaces:            Yes
  Device has ECC support:                        Disabled
  Device supports Unified Addressing (UVA):      Yes
  Device supports Managed Memory:                Yes
  Device supports Compute Preemption:            Yes
  Supports Cooperative Kernel Launch:            Yes
  Supports MultiDevice Co-op Kernel Launch:      Yes
  Device PCI Domain ID / Bus ID / location ID:   0 / 0 / 0
  Compute Mode:
     < Default (multiple host threads can use ::cudaSetDevice() with device simultaneously) >

deviceQuery, CUDA Driver = CUDART, CUDA Driver Version = 12.6, CUDA Runtime Version = 12.6, NumDevs = 1
Result = PASS
```
- Ejecutar test de ancho de banda:
  - `/usr/local/cuda-samples/build_utils/bandwidthTest/bandwidthTest`
```yaml
[CUDA Bandwidth Test] - Starting...
Running on...

 Device 0: Orin
 Quick Mode

 Host to Device Bandwidth, 1 Device(s)
 PINNED Memory Transfers
   Transfer Size (Bytes)        Bandwidth(GB/s)
   32000000                     15.6

 Device to Host Bandwidth, 1 Device(s)
 PINNED Memory Transfers
   Transfer Size (Bytes)        Bandwidth(GB/s)
   32000000                     14.8

 Device to Device Bandwidth, 1 Device(s)
 PINNED Memory Transfers
   Transfer Size (Bytes)        Bandwidth(GB/s)
   32000000                     67.0

Result = PASS
```
---

## 6. Riesgos / Bloqueos


| ID  | Riesgo | Consecuencia | Prob. | Imp. | Nivel | Plan de mitigación |
|-----|--------|--------------|-------|------|--------|----------------------|
| R1  | Flash incorrecto del Jetson | Dispositivo inutilizable hasta repetir el proceso | Media | Alta | 🔴 Alta | Seguir estrictamente la guía de NVIDIA para flashing; usar SDK Manager oficial |
| R2  | Incompatibilidad de frameworks RAG/MCP con Jetson | Limitaciones en funcionalidades o errores de ejecución | Media | Alta | 🔴 Alta | Usar alternativas nativas NVIDIA (NVIDIA Container Runtime, PyTorch Jetson, CUDA, TensorRT, `jetson-containers`) |
| R3  | Incompatibilidad entre versiones CUDA / JetPack / TensorRT | Fallos en compilación o ejecución de modelos | Alta | Alta | 🔴 Alta | Verificar la matriz de compatibilidad oficial antes de instalar; mantener la versión JetPack recomendada |
| R4  | Fallos al compilar CUDA Samples | Falta de validación del entorno CUDA | Media | Media | 🟠 Media | Ajustar `CMAKE_CUDA_ARCHITECTURES` al SM del Jetson AGX Nano/Orin; instalar dependencias necesarias |
| R5  | Problemas de rendimiento por drivers no actualizados | Bajo rendimiento en IA y aceleración hardware | Media | Media | 🟠 Media | Actualizar JetPack a la última versión compatible; validar con `tegrastats` y TensorRT |
| R6  | Ruptura del entorno por instalar paquetes no soportados | Inestabilidad del sistema | Baja | Alta | 🟠 Media | Instalar solo paquetes del repositorio Jetson o contenedores NVIDIA preconfigurados |

---

## 7. Conclusión

Este procedimiento asegura que el Jetson AGX Orin esté actualizado, con un entorno de desarrollo completo y pruebas de hardware CUDA validadas. La correcta configuración permite ejecutar proyectos de IA, visión por computador y RAG de manera confiable.

---

## 8. Referencias

### Jetson / CUDA (Instalación / Documentación / Samples)
- [Jetson Orin Setup Scripts (jetsonhacks)](https://github.com/jetsonhacks/jetson-orin-setup)
- [CUDA 12.6.0 Jetson Ubuntu 22.04 (aarch64)](https://developer.nvidia.com/cuda-12-6-0-download-archive?target_os=Linux&target_arch=aarch64-jetson&Compilation=Native&Distribution=Ubuntu&target_version=22.04&target_type=deb_local)
- [Guía de instalación CUDA Linux](https://docs.nvidia.com/cuda/cuda-installation-guide-linux)
- [CUDA for Tegra Application Note](https://docs.nvidia.com/cuda/cuda-for-tegra-appnote/index.html#upgradable-package-for-jetson)
- [CUDA Samples v12.8 (GitHub)](https://github.com/NVIDIA/cuda-samples/tree/v12.8)
- [Listado oficial de GPUs CUDA](https://developer.nvidia.com/cuda-gpus)

### cuDNN
- [Descarga cuDNN para Jetson (aarch64)](https://developer.nvidia.com/cudnn-downloads?target_os=Linux&target_arch=aarch64-jetson&Compilation=Native&Distribution=Ubuntu&target_version=22.04&target_type=deb_local)
- [Archivo histórico de cuDNN](https://developer.nvidia.com/rdp/cudnn-archive)
- [Matriz de compatibilidad cuDNN Backend API](https://docs.nvidia.com/deeplearning/cudnn/backend/latest/reference/support-matrix.html)

### Otros / Resolución de problemas
- [Foro NVIDIA: TensorRT y Drive SDK](https://forums.developer.nvidia.com/t/resolved-problem-using-tensorrt-from-drive-sdk/60720)
