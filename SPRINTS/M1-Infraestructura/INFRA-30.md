# Diseño de la tarea: INFRA-30 — Configuración Docker con GPU

Este documento describe la tarea **[INFRA-30]** dentro del proyecto **Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva**.  
Incluye la descripción, objetivos, procedimientos, verificación y resultados esperados para que otros estudiantes puedan reproducir el trabajo en su entorno.

---

## Tabla de contenidos
1. [Descripción y Objetivo](#1-descripción-y-objetivo)  
2. [Requisitos / Contexto](#2-requisitos--contexto)  
3. [Procedimiento de instalación y configuración](#3-procedimiento-de-instalación-y-configuración)  
4. [Validación del entorno (Checkpoints)](#4-validación-del-entorno-checkpoints)  
5. [Riesgos / Bloqueos](#5-riesgos--bloqueos)  
6. [Conclusión](#6-conclusión)  
7. [Referencias](#7-referencias)

---

## 1. Descripción y Objetivo

**Descripción:**  
Como estudiante, quiero que Docker esté configurado con el uso de GPU para facilitar el desarrollo y la ejecución de todas las tareas del TFG y del agente, utilizando JetPack 6.x en Jetson.

**Objetivo:**  
Permitir que los procesos en Python aprovechen la GPU, mejorando el rendimiento y reduciendo los tiempos de procesamiento de grandes volúmenes de datos.

---
 Diseño de la tarea: INFRA-30 — Configuración Docker con GPU

Este documento describe la tarea INFRA-30 dentro del proyecto Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva  
Incluye la descripción, objetivos, procedimientos, verificación y resultados esperados para que otros estudiantes puedan reproducir el trabajo en su entorno

---

## 2. Requisitos / Contexto

- Jetson con JetPack 6.x instalado (L4T R36.x)  
- Acceso a internet para descargar paquetes y herramientas  
- Usuario con permisos para instalar paquetes y ejecutar Docker (sudo)  
- CUDA Toolkit y cuDNN previamente instalados  
- Conocimiento básico de terminal Linux y comandos Docker

---

## 3. Procedimiento de instalación y configuración

### 3.1 Instalar Docker y NVIDIA Container Toolkit

- Actualizar paquetes
 - `sudo apt update`

- Instalar NVIDIA Container Toolkit y curl
 - `sudo apt install -y nvidia-container-toolkit curl`

- Instalar Docker
 - `curl -fsSL https://get.docker.com | sh`

- Activar Docker al iniciar
 - `sudo systemctl --now enable docker`

### 3.2 Configurar NVIDIA runtime para Docker

- Configurar runtime de NVIDIA
 - `sudo nvidia-ctk runtime configure --runtime=docker`

- Reiniciar Docker
 - `sudo systemctl restart docker`

- Agregar usuario al grupo docker
 - `sudo usermod -aG docker $USER`
 - `newgrp docker`

Esto permite que Docker use la GPU de manera nativa

### 3.3 Añadir NVIDIA runtime por defecto en Docker

- Editar archivo de configuración de Docker
 - `sudo nano /etc/docker/daemon.json`

- Insertar las siguientes líneas
```yaml
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  },
  "default-runtime": "nvidia"
}
```
- Reiniciar Docker
 - `sudo systemctl daemon-reload`
 - `sudo systemctl restart docker`

### 3.4 Probar instalación y GPU en Docker

- Verificar versión de Docker  
 - `docker --version`

- Docker debería mostrar algo como: Docker version 24.0.5, build ...

- Verificar acceso a GPU desde contenedor oficial CUDA  
Ejecutar: `docker run --rm --gpus all nvcr.io/nvidia/l4t-base:r36.2.1 nvidia-smi`  

- Ejecutar contenedor de prueba  
`docker run --rm hello-world`  
Debería mostrar el mensaje de prueba de Docker

---

### 3.5 Instalar jetson-containers


- Clonar e instalar utilidades de jetson-containers:
  - `git clone https://github.com/dusty-nv/jetson-containers`
  - `bash jetson-containers/install.sh`
- El script pedirá tu contraseña sudo, instalará dependencias de Python y añadirá herramientas al PATH mediante enlaces simbólicos en /usr/local/bin
  - `jetson-containers --help`

```yaml
jetson-containers > Invalid command

   * build [PACKAGES]
   * run OPTIONS [CONTAINER:TAG] CMD
   * list [PACKAGES|*
   * show [PACKAGES]*
   * autotag [CONTAINER]
   * update (runs git pull)
   * db   (sync database)
   * root (prints repo path)
   * data (prints data path)

Run "jetson-containers <CMD> --help" for more info.
```

## 4. Validación del entorno (Checkpoints)

- Docker reconoce GPU correctamente (nvidia-smi dentro del contenedor)  
- Contenedor base con CUDA y Python funcionando  
- Usuario puede ejecutar contenedores sin sudo  
- Frameworks como PyTorch o TensorFlow detectan GPU dentro del contenedor

---

## 5. Riesgos / Bloqueos

ID  | Riesgo | Consecuencia | Probabilidad | Impacto | Nivel | Plan de mitigación
R1  | Docker no detecta GPU | Python no puede usar aceleración | Media | Alta | Alta | Ejecutar nvidia-ctk runtime configure y reiniciar Docker
R2  | Versiones incompatibles CUDA / cuDNN | Errores al ejecutar frameworks | Media | Media | Media | Usar imágenes Docker oficiales de NVIDIA con versiones compatibles
R3  | Permisos insuficientes de usuario | No se pueden ejecutar contenedores | Alta | Media | Media | Agregar usuario al grupo docker o usar sudo

---

## 6. Conclusión

Configurar Docker con GPU en Jetson permite que los pipelines de Python y ML aprovechen aceleración por hardware, asegurando eficiencia, reproducibilidad y compatibilidad con frameworks como PyTorch, TensorFlow o LLaMA CPP

---

## 7. Referencias

### Jetson / CUDA (Instalación / Documentación / Samples)
- [Jetson Orin Setup Scripts (JetsonHacks)](https://github.com/jetsonhacks/jetson-orin-setup)
- [NVIDIA Container Toolkit Install Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [Jetson Containers (Dusty-NV)](https://github.com/dusty-nv/jetson-containers/)


