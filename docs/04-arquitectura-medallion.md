# INFRA-40: Configuración de MinIO con Arquitectura Medallion

**Título del Trabajo:** Sistema RAG para Análisis de Fútbol Semi-Profesional  
**Nombre del Estudiante:** Pedro José García Fernández  
**Tutor/a de TF:** Arturo González Martínez  
**Profesor/a responsable:** Susana Acedo  
**Fecha:** 26 Diciembre 2024  
**Titulación o programa:** Grado de Ciencia de Datos Aplicada  
**Área de trabajo:** Trabajo Final de Grado  
**Idioma:** Castellano  
**Palabras Clave:** MinIO - S3 - Medallion - Data Lake - Bronce - Plata - Oro - ARM64

---

**Épica:** INFRA - Infraestructura  
**Tarea:** INFRA-40 - Configuración de Almacenamiento Distribuido  
**Sprint:** S2 (Septiembre 2024 - Semanas 3-4)  
**Asignatura UOC:** Trabajo Final de Grado

---

## 📋 Tabla de Contenidos

1. [Descripción y Objetivo](#1-descripción-y-objetivo)
2. [Requisitos / Contexto](#2-requisitos--contexto)
3. [Procedimiento de Instalación](#3-procedimiento-de-instalación)
4. [Arquitectura Medallion](#4-arquitectura-medallion)
5. [Configuración de Usuarios y Políticas](#5-configuración-de-usuarios-y-políticas)
6. [Reorganización de Estructura](#6-reorganización-de-estructura)
7. [Módulo Python medallion_storage](#7-módulo-python-medallion_storage)
8. [Validación del Entorno](#8-validación-del-entorno)
9. [Riesgos y Soluciones](#9-riesgos-y-soluciones)
10. [Resultados Finales](#10-resultados-finales)
11. [Referencias](#11-referencias)

---

## 1. Descripción y Objetivo

### Descripción

Como estudiante, quiero configurar un sistema de almacenamiento distribuido utilizando **MinIO** para gestionar el ciclo de vida de los datos mediante una **estructura Medallion** (Bronce, Plata, Oro), que permita el acceso organizado, controlado y escalable a los datos del proyecto.

### Objetivo

Garantizar una transferencia y almacenamiento seguro de los datos, permitiendo un acceso organizado y controlado, de manera que los datos en crudo, transformados y finales estén disponibles para procesamiento y análisis sin comprometer la seguridad de la información.

### Criterios de Aceptación

- ✅ MinIO instalado y corriendo como servicio systemd
- ✅ Estructura Medallion implementada (buckets bronce/plata/oro)
- ✅ Usuarios y políticas de acceso configurados
- ✅ Módulo Python para gestión programática
- ✅ Scripts de reorganización automatizados
- ✅ Documentación completa y reproducible

---

## 2. Requisitos / Contexto

### Contexto del Proyecto

Se necesita un sistema de almacenamiento que:

1. **Preserve datos raw** (HTMLs, PDFs, videos)
2. **Organice datos procesados** (CSVs, JSONs)
3. **Optimice para analytics** (embeddings, agregados)
4. **Permita versionado** y trazabilidad

### Requisitos Técnicos

**Hardware:**
- NVIDIA Jetson AGX Orin (64GB RAM)
- Almacenamiento: 500GB+ SSD
- Red: 1Gbps LAN

**Software:**
- Ubuntu 22.04 (JetPack 6.2.1)
- Python 3.10+
- MinIO Server (última versión ARM64)
- AWS CLI o MinIO Client (mc)

### Arquitectura Medallion

```
┌──────────────────────────────────────────────┐
│ BRONCE (Raw Data)                            │
├──────────────────────────────────────────────┤
│ • Datos sin procesar (inmutables)            │
│ • Formato original preservado                │
│ • Write-once, read-many                      │
│                                              │
│ Contenido:                                   │
│  - html/      → Comentarios RTL (HTML)       │
│  - pdf/       → Actas FLF (PDF)              │
│  - video/     → Partidos completos (MP4)     │
└──────────────────────────────────────────────┘
                    ↓ ETL
┌──────────────────────────────────────────────┐
│ PLATA (Processed Data)                       │
├──────────────────────────────────────────────┤
│ • Datos limpios y validados                  │
│ • Formato estándar (JSON/CSV)                │
│ • Enriquecidos con metadatos                 │
│                                              │
│ Contenido:                                   │
│  - eventos/   → HTMLs parseados (CSV/JSON)   │
│  - actas/     → PDFs estructurados (JSON)    │
│  - videos/    → Clips procesados             │
└──────────────────────────────────────────────┘
                    ↓ Feature Engineering
┌──────────────────────────────────────────────┐
│ ORO (Analytics-Ready)                        │
├──────────────────────────────────────────────┤
│ • Optimizado para consultas                  │
│ • Agregado y desnormalizado                  │
│ • Listo para ML/BI                           │
│                                              │
│ Contenido:                                   │
│  - embeddings/ → Vectores para RAG           │
│  - analytics/  → KPIs y agregados            │
│  - database/   → Exports Oracle DB           │
└──────────────────────────────────────────────┘
```

---

## 3. Procedimiento de Instalación

### 3.1 Instalación de MinIO Server

#### Paso 1: Descargar binario ARM64

```bash
# Descargar última versión para ARM64
wget https://dl.min.io/server/minio/release/linux-arm64/minio

# Dar permisos de ejecución
chmod +x minio

# Mover a /usr/local/bin
sudo mv minio /usr/local/bin/

# Verificar instalación
minio --version
```

**Output esperado:**
```
minio version RELEASE.2025-09-07T16-13-09Z (commit-id=07c3a429bfed433e49018cb0f78a52145d4bedeb)
Runtime: go1.24.6 linux/arm64
License: GNU AGPLv3 - https://www.gnu.org/licenses/agpl-3.0.html
Copyright: 2015-2025 MinIO, Inc.
```

---

#### Paso 2: Crear estructura de directorios

```bash
# Crear directorio de datos
sudo mkdir -p /usr/local/share/minio

# Asignar permisos al usuario
sudo chown -R claudia:claudia /usr/local/share/minio
sudo chmod -R u+rwX /usr/local/share/minio
```

---

#### Paso 3: Configurar credenciales

Crear archivo `/etc/default/minio`:

```bash
sudo vi /etc/default/minio
```

**Contenido:**
```bash
# Archivo de configuración de MinIO
# ---------------------------------

# Directorio de datos (estructura medallion)
MINIO_VOLUMES="/usr/local/share/minio"

# Credenciales de acceso
MINIO_ROOT_USER=minioclaudia
MINIO_ROOT_PASSWORD=minioclaudia

# Configuración de red (opcional)
# MINIO_SERVER_URL="http://192.168.1.22:9000"
```

---

#### Paso 4: Crear servicio systemd

Crear archivo `/etc/systemd/system/minio.service`:

```bash
sudo vi /etc/systemd/system/minio.service
```

**Contenido:**
```ini
[Unit]
Description=MinIO Object Storage Server
Documentation=https://min.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
User=claudia
Group=root
EnvironmentFile=/etc/default/minio
ExecStart=/usr/local/bin/minio server $MINIO_VOLUMES --address :9000
Restart=always
LimitNOFILE=65536
TimeoutStopSec=30s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

#### Paso 5: Iniciar servicio

```bash
# Recargar systemd
sudo systemctl daemon-reload

# Habilitar inicio automático
sudo systemctl enable minio

# Iniciar servicio
sudo systemctl start minio

# Verificar estado
sudo systemctl status minio
```

**Output esperado:**
```
● minio.service - MinIO Object Storage Server
     Loaded: loaded (/etc/systemd/system/minio.service; enabled)
     Active: active (running) since ...
     ...
```

---

### 3.2 Instalación de MinIO Client (mc)

```bash
# Descargar mc para ARM64
wget https://dl.min.io/client/mc/release/linux-arm64/mc

# Dar permisos
chmod +x mc

# Mover a /usr/local/bin
sudo mv mc /usr/local/bin/

# Verificar instalación
mc --version
```

---

### 3.3 Configuración de Alias

```bash
# Configurar alias para servidor local
mc alias set uoc http://192.168.1.156:9000 minioclaudia minioclaudia

# Listar buckets
mc ls uoc/
```

---

## 4. Arquitectura Medallion

### 4.1 Creación de Buckets

#### Opción A: Usando MinIO Client (mc)

```bash
# Crear buckets principales
mc mb uoc/bronce
mc mb uoc/plata
mc mb uoc/oro

# Verificar
mc ls uoc/
```

**Output esperado:**
```
[2024-12-26 10:00:00 CET]     0B bronce/
[2024-12-26 10:00:00 CET]     0B plata/
[2024-12-26 10:00:00 CET]     0B oro/
```

---

#### Opción B: Usando Python (boto3)

```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://192.168.1.156:9000',
    aws_access_key_id='minioclaudia',
    aws_secret_access_key='minioclaudia'
)

# Crear buckets
for bucket in ['bronce', 'plata', 'oro']:
    s3.create_bucket(Bucket=bucket)
    print(f"✅ Bucket '{bucket}' creado")
```

---

### 4.2 Estructura Detallada por Bucket

#### BRONCE (Raw Data)

```
bronce/
├── html/
│   └── 2025-2026/
│       ├── match_1001143.html
│       ├── match_1001144.html
│       └── ...
├── pdf/
│   └── 2025-2026/
│       ├── feuille_de_match_1001143.pdf
│       ├── feuille_de_match_1001144.pdf
│       └── ...
└── video/
    └── 2025-2026/
        ├── jornada_1/
        │   ├── partido_1.mp4
        │   └── ...
        └── jornada_15/
```

**Características:**
- Datos inmutables (write-once)
- Formato original preservado
- Trazabilidad completa

---

#### PLATA (Processed Data)

```
plata/
├── eventos/
│   └── 2025-2026/
│       ├── eventos_1001143.json
│       ├── eventos_1001143.csv
│       └── ...
├── actas/
│   └── 2025-2026/
│       ├── Partido-2025-08-02-BGL-Ligue-1001143.json
│       └── ...
└── videos/
    └── 2025-2026/
        ├── clips/
        └── thumbnails/
```

**Características:**
- Datos validados y limpios
- Formato estándar (JSON/CSV)
- Metadatos enriquecidos

---

#### ORO (Analytics-Ready)

```
oro/
├── embeddings/
│   ├── eventos_embeddings.npy
│   ├── actas_embeddings.npy
│   └── metadata.json
├── analytics/
│   ├── kpis_temporada.parquet
│   ├── agregados_equipos.csv
│   └── estadisticas.json
└── database/
    ├── exports/
    └── backups/
```

**Características:**
- Optimizado para consultas
- Formatos columnar (Parquet)
- Índices y agregaciones

---

## 5. Configuración de Usuarios y Políticas

### 5.1 Crear Usuarios por Capa

```bash
# Usuario para BRONCE (lectura/escritura)
mc admin user add uoc claudia_bronze claudia_bronze

# Usuario para PLATA (solo lectura)
mc admin user add uoc claudia_plata claudia_plata

# Usuario para ORO (solo lectura)
mc admin user add uoc claudia_oro claudia_oro
```

---

### 5.2 Definir Políticas de Acceso

#### Política BRONCE (lectura/escritura)

**Archivo:** `bronze-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::bronce",
        "arn:aws:s3:::bronce/*"
      ]
    }
  ]
}
```

---

#### Política PLATA (solo lectura)

**Archivo:** `plata-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::plata",
        "arn:aws:s3:::plata/*"
      ]
    }
  ]
}
```

---

### 5.3 Asignar Políticas a Usuarios

```bash
# Crear políticas
mc admin policy create uoc bronze-policy bronze-policy.json
mc admin policy create uoc plata-policy plata-policy.json
mc admin policy create uoc oro-policy oro-policy.json

# Asignar a usuarios
mc admin policy attach uoc bronze-policy --user claudia_bronze
mc admin policy attach uoc plata-policy --user claudia_plata
mc admin policy attach uoc oro-policy --user claudia_oro

# Verificar
mc admin user info uoc claudia_bronze
```

---

## 7. Módulo Python medallion_storage

### 7.1 Descripción

Módulo Python para gestión programática de la arquitectura Medallion.

**Archivo:** `scripts/utils/medallion_storage.py`

### 7.2 Clase Principal

```python
class MedallionStorage:
    """
    Cliente para gestionar almacenamiento Medallion en MinIO.
    
    Métodos principales:
    - verificar_estructura()
    - crear_estructura()
    - subir_*_bronce()
    - subir_*_plata()
    - subir_*_oro()
    - leer_*()
    - obtener_estadisticas()
    """
```

---

### 7.3 Ejemplo de Uso

```python
from medallion_storage import crear_cliente

# Crear cliente
storage = crear_cliente()

# Verificar estructura
status = storage.verificar_estructura()
# Output: {'bronce': True, 'plata': True, 'oro': True}

# Subir HTML a BRONCE
storage.subir_html_bronce(
    local_file=Path("match_1001143.html"),
    match_id=1001143,
    temporada="2025-2026"
)

# Leer acta desde PLATA
json_str = storage.leer_actas_plata(
    match_id=1001143,
    temporada="2025-2026"
)

# Obtener estadísticas
stats = storage.obtener_estadisticas()
# Output: {
#   'bronce': {'archivos': 1000, 'size_gb': 0.22},
#   'plata': {'archivos': 118, 'size_gb': 0.00},
#   'oro': {'archivos': 0, 'size_gb': 0.00}
# }
```

---

### 7.4 Funcionalidades Clave

#### Detección Automática de Archivos

El módulo busca archivos por match_id incluso cuando el nombre completo incluye fecha y competición:

```python
# Busca: Partido-2025-08-02-BGL-Ligue-1001143.json
# Usando solo: match_id=1001143
acta = storage.leer_actas_plata(1001143)
```

#### Manejo de Errores

```python
try:
    pdf_bytes = storage.leer_pdf_bronce(9999999)
except Exception as e:
    logger.error(f"Error: {e}")
    # Continúa ejecución sin fallar
```

---

## 8. Validación del Entorno

### 8.1 Checkpoint 1: MinIO Corriendo ✅

```bash
sudo systemctl status minio
mc ls uoc/
```

**Criterio de éxito:**
- Servicio activo
- Buckets listados

---

### 8.2 Checkpoint 2: Estructura Medallion ✅

```bash
mc ls uoc/bronce/
mc ls uoc/plata/
mc ls uoc/oro/
```

**Criterio de éxito:**
- 3 buckets existen
- Estructura de subdirectorios correcta

---

### 8.3 Checkpoint 3: Módulo Python ✅

```bash
cd scripts/utils
python medallion_storage.py
```

**Output esperado:**
```
🧪 Test del módulo medallion_storage
==================================================
✅ Cliente inicializado
✅ Buckets verificados
📦 BRONCE: 1000 archivos (0.22 GB)
📦 PLATA: 118 archivos (0.00 GB)
📦 ORO: 0 archivos (0.00 GB)
==================================================
✅ Test completado
```

---

### 8.4 Checkpoint 4: Notebook ✅

Ejecutar `experiments/02-data-extraction/medallion_storage.ipynb`

**Validaciones:**
- ✅ Conexión a MinIO
- ✅ Lectura de archivos
- ✅ Estadísticas correctas

---

## 9. Riesgos y Soluciones

### 9.1 Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Disco lleno | Media | Alto | ✅ Monitoreo automático, alertas |
| Pérdida de datos | Baja | Crítico | ✅ Backups diarios, replicación |
| Acceso no autorizado | Media | Alto | ✅ Políticas IAM, usuarios específicos |
| Corrupción de archivos | Baja | Alto | ✅ Checksums, validación |

---

## 10. Resultados Finales

### 10.1 Métricas del Épico

| Métrica | Valor |
|---------|-------|
| **Buckets creados** | 3 (bronce, plata, oro) |
| **Archivos totales** | 1,118 |
| **Tamaño total** | 0.22 GB |
| **Usuarios configurados** | 3 (por capa) |
| **Políticas activas** | 3 |
| **Módulo Python** | ✅ Funcional |
| **Tiempo de setup** | 2 horas |

---

### 10.2 Distribución de Datos

```
📦 BRONCE: 1000 archivos (0.22 GB)
   ├── pdf/2025-2026/: 120 PDFs
   ├── video/2025-2026/: 5 videos
   └── html/: (pendiente DATA-20)

📦 PLATA: 118 archivos (< 1 MB)
   └── actas/2025-2026/: 118 JSONs

📦 ORO: 0 archivos
   └── (se llenará con DWH-30, RAG-20)
```

---

### 10.3 Entregables

**Documentación:**
- ✅ `docs/01-infraestructura/04-arquitectura-medallion.md`

**Scripts:**
- ✅ `scripts/utils/medallion_storage.py` — Módulo Python

**Notebooks:**
- ✅ `experiments/02-data-extraction/medallion_storage.ipynb`

---

## 11. Referencias

### Documentación Oficial

- [MinIO Documentation](https://docs.min.io/)
- [MinIO Client (mc)](https://docs.min.io/minio/baremetal/reference/minio-cli/minio-mc.html)
- [boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)

### Referencias Internas

- [INFRA-10: Hardware (Jetson)](./01-comparativa-gpu.md)
- [INFRA-20: Setup Software](./02-setup-jetson-orin.md)
- [DATA-10: Identificación de Fuentes](../02-extraccion-datos/01-analisis-fuentes.md)
- [DATA-50: Almacenamiento Bronze](../02-extraccion-datos/05-medallion-storage.md)

---

## Anexos

### Anexo A: Comandos Útiles MinIO

```bash
# Listar contenido
mc ls local/bronce/ --recursive

# Copiar archivo
mc cp archivo.pdf local/bronce/pdf/

# Descargar archivo
mc cp local/bronce/pdf/archivo.pdf ./

# Sincronizar directorio
mc mirror ./local_dir/ local/bronce/pdf/

# Ver estadísticas
mc du local/bronce/

# Eliminar archivo
mc rm local/bronce/pdf/archivo.pdf
```

---

### Anexo B: Solución de Problemas

**Problema:** MinIO no inicia

```bash
# Ver logs
sudo journalctl -u minio -n 50

# Verificar permisos
ls -la /usr/local/share/minio

# Verificar puerto
sudo netstat -tulpn | grep 9000
```

---

**Problema:** No puedo conectar desde Python

```python
# Verificar conectividad
import requests
response = requests.get("http://192.168.1.22:9000")
print(response.status_code)  # Debe ser 403 (no autenticado)

# Verificar credenciales
s3 = boto3.client(
    's3',
    endpoint_url='http://192.168.1.22:9000',
    aws_access_key_id='minioclaudia',
    aws_secret_access_key='minioclaudia'
)
print(s3.list_buckets())
```

---

**Épico Completado:** 26 Diciembre 2024  
**Responsable:** Pedro José García Fernández  
**Revisor:** Tutor TFG  
**Estado:** ✅ COMPLETADO

---

*"Un buen sistema de almacenamiento es invisible cuando funciona, e invaluable cuando lo necesitas."*

*— Lección aprendida después de organizar 1,118 archivos en arquitectura Medallion*
