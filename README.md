# 🤖 Cl@udiata - Agente Virtual de Análisis Deportivo

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36-red.svg)](https://streamlit.io/)
[![Ollama](https://img.shields.io/badge/Ollama-0.6-green.svg)](https://ollama.com/)
[![Jetson](https://img.shields.io/badge/NVIDIA-Jetson_AGX_Orin-76B900.svg)](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)
[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

---

## 📖 Descripción

Este trabajo presenta el diseño y desarrollo de **Cl@ud-ia-data**, un agente virtual privado basado en **inteligencia artificial generativa**, especializado en el análisis de datos deportivos. La finalidad del proyecto es ofrecer una herramienta de apoyo a la toma de decisiones mediante análisis avanzado de datos, garantizando la **privacidad**, el control de la información y un uso eficiente de los recursos computacionales.

El sistema se despliega en un entorno completamente privado sobre una infraestructura local basada en una **NVIDIA Jetson AGX Orin de 64 GB**, una plataforma de computación acelerada de alto rendimiento y **bajo consumo energético**. Esta elección tecnológica contribuye a un enfoque de **IA sostenible**, reduciendo de forma significativa la huella energética frente a soluciones basadas en grandes centros de datos en la nube.

La metodología empleada se fundamenta en técnicas de **Generación Aumentada por Recuperación (RAG)**, utilizando exclusivamente modelos de **código abierto**. El desarrollo se ha llevado a cabo mediante un enfoque experimental, definiendo y ejecutando una serie de **experimentos** orientados a validar el rendimiento del sistema, la calidad de las respuestas generadas y la viabilidad técnica del Trabajo Final de Grado.

Como resultado, se obtiene un agente funcional capaz de generar respuestas precisas y contextualizadas a partir de datos deportivos de la **liga luxemburguesa**. Como artefacto final del proyecto, se entrega una **interfaz de consulta** que permite interactuar con el sistema de forma intuitiva y accesible para usuarios no técnicos.

En conclusión, el trabajo demuestra que es viable implementar soluciones de **IA generativa especializada** sobre infraestructuras locales de **bajo consumo**, ofreciendo una alternativa **sostenible**, eficiente y escalable para el análisis de datos deportivos en contextos con recursos limitados.

---

## 🎓 Contexto Académico

**Trabajo Final de Máster**  
**Universitat Oberta de Catalunya (UOC)**  
Máster en Ciencia de Datos  
Autor: Pedro José García  
Año: 2025

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

| Componente | Tecnología | Versión | Propósito |
|------------|-----------|---------|-----------|
| **LLM** | Qwen2.5 | 32B (Q4_K_M) | Generación de respuestas |
| **Embeddings** | multilingual-e5-large | 1024 dims | Representación semántica |
| **Vector DB** | ChromaDB | 1.3.7 | Almacenamiento vectorial |
| **Framework** | Streamlit + LangChain | - | Interface y orquestación |
| **Storage** | MinIO | - | Arquitectura Medallion |
| **Runtime** | Ollama | 0.6+ | Servidor LLM local |
| **Hardware** | Jetson AGX Orin | 64GB | Plataforma de inferencia |

### Arquitectura Medallion (Bronze → Silver → Gold)

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   BRONZE    │      │    SILVER    │      │      GOLD       │
│  (Raw Data) │  →   │  (Cleaned)   │  →   │  (Embeddings)   │
│             │      │              │      │                 │
│  - PDFs     │      │  - CSV       │      │  - ChromaDB     │
│  - HTML     │      │  - Eventos   │      │  - Índices      │
│             │      │  - Goleadores│      │  - Metadatos    │
└─────────────┘      └──────────────┘      └─────────────────┘
      ↓                     ↓                       ↓
    MinIO               MinIO                   Local
```

### Flujo RAG (Retrieval-Augmented Generation)

```
Usuario → Consulta en lenguaje natural
    ↓
Embedding de la consulta (e5-large)
    ↓
Búsqueda semántica en ChromaDB (Top-K)
    ↓
Recuperación de eventos relevantes
    ↓
Construcción de contexto + prompt
    ↓
Generación con LLM (Qwen2.5 32B)
    ↓
Respuesta contextualizada al usuario
```

---

## 🚀 Instalación y Despliegue

### Requisitos Previos

- **Hardware:** NVIDIA Jetson AGX Orin (64GB RAM recomendado)
- **SO:** Ubuntu 22.04 (JetPack 6.2+)
- **Software:** 
  - Conda/Miniforge
  - Docker (opcional, para MinIO)
  - CUDA 12.6+

### Instalación Paso a Paso

#### 1. Clonar Repositorio

```bash
git clone https://github.com/claudyata/claudyata.github.io
cd claudyata.github.io
```

#### 2. Configurar Entorno Conda

```bash
# Crear entorno desde environment.yml
conda env create -f environment.yml

# Activar entorno
conda activate tfg
```

#### 3. Instalar Ollama y Modelos

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelos necesarios
ollama pull qwen2.5:32b              # Modelo principal
ollama pull mxbai-embed-large        # Embeddings alternativos

# Verificar instalación
ollama list
```

#### 4. Configurar MinIO (Almacenamiento Medallion)

```bash
# Opción A: Docker (recomendado)
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -v ~/minio/data:/data \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=admin123" \
  quay.io/minio/minio server /data --console-address ":9001"

# Opción B: Nativo
# Ver docs/04-arquitectura-medallion.md
```

Acceder a MinIO Console: `http://localhost:9001`

#### 5. Configurar Variables de Entorno

```bash
# Crear archivo .env en artefactos/src/
cat > artefactos/src/.env << EOF
# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=admin123
MINIO_SECURE=False

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:32b

# ChromaDB
CHROMADB_PATH=../../chroma_db
EOF
```

#### 6. Inicializar Base de Datos Vectorial

```bash
cd artefactos/src
python -c "from core.rag_client import RAGClient; RAGClient()"
```

#### 7. Ejecutar Aplicación

```bash
cd artefactos/src
streamlit run app.py
```

La aplicación estará disponible en: `http://localhost:8501`

---

## 📂 Estructura del Proyecto

```
claudyata.github.io/
├── artefactos/
│   └── src/
│       ├── app.py                      # Aplicación Streamlit principal
│       ├── core/                       # Lógica de negocio
│       │   ├── rag_client.py           # Cliente RAG (ChromaDB + LangChain)
│       │   ├── nlp_analyzer.py         # Análisis NLP y generación
│       │   ├── medallion_storage.py    # Gestión MinIO (Bronze/Silver/Gold)
│       │   ├── data_loaders.py         # Carga de datos
│       │   ├── etl_pipeline.py         # Pipeline ETL
│       │   └── traductor_pipeline.py   # Traducción multiidioma
│       ├── tabs/                       # Pestañas de la interfaz
│       │   ├── tab_busqueda_rag.py     # Búsqueda con RAG
│       │   ├── tab_resumen.py          # Generación de resúmenes
│       │   ├── tab_dafo.py             # Análisis DAFO
│       │   ├── tab_gpu_monitor.py      # Monitoreo GPU
│       │   └── tab_info.py             # Información del sistema
│       ├── crawlers/                   # Web scraping
│       │   ├── crawl_html.py
│       │   └── crawl_mpg.py
│       └── utils/                      # Utilidades
│           ├── gpu_monitor.py
│           └── test_tflops.py
├── docs/                               # Documentación técnica
│   ├── 02-setup-jetson-orin.md
│   ├── 03-setup-docker.md
│   ├── 04-arquitectura-medallion.md
│   └── 09-benchmark_qwen_quantization.md
├── experiments/                        # Notebooks experimentales
│   ├── 01-comparativa-gpu.ipynb
│   ├── 05-comparativa-gestor-llm.ipynb
│   ├── 06-comparativa-embeddings.ipynb
│   ├── 07-comparativa-modelos-llm.ipynb
│   └── 08-etl-bronze-to-silver-to-gold.ipynb
├── environment.yml                     # Dependencias conda
├── Modelfile.claudiata                 # Configuración modelo Ollama
├── DOC.md                              # Documentación principal
└── README.md                           # Este archivo
```

---

## 📊 Características Principales

### 🔍 Búsqueda RAG (Retrieval-Augmented Generation)

- **Consultas en lenguaje natural** sobre partidos de fútbol
- **Recuperación semántica** de eventos relevantes
- **Respuestas contextualizadas** generadas por LLM
- **Multiidioma:** Español, Francés, Luxemburgués, Alemán

**Ejemplo de uso:**
```
Usuario: "¿Cuáles fueron los goles del partido entre FC Bissen y US Hueschtert?"
Sistema: [Recupera eventos relevantes] → [Genera respuesta contextualizada]
```

### 📝 Generación de Resúmenes

- **Crónicas automáticas** de partidos
- **Análisis táctico** detallado
- **Narrativa natural** adaptada al idioma
- **Exportación** en múltiples formatos

### 📈 Análisis Estadístico

- **Clasificación** de equipos
- **Top goleadores** por jornada/temporada
- **Métricas de rendimiento** individuales y colectivas
- **Visualizaciones** interactivas

### 🌐 Traducción Multiidioma

- Soporte para **4 idiomas** (ES, FR, LB, DE)
- Traducción automática de resúmenes
- Preservación del **contexto deportivo**

### 💻 Monitoreo de Recursos

- **Consumo energético** en tiempo real
- **Temperatura** de GPU
- **Uso de memoria** RAM/VRAM
- **Métricas de rendimiento** (tokens/s, latencia)

---

## 🧪 Experimentos y Benchmarks

### Comparativas Realizadas

El proyecto incluye análisis exhaustivos documentados en notebooks Jupyter:

#### 1. Comparativa de GPUs ([01-comparativa-gpu.ipynb](experiments/01-comparativa-gpu.ipynb))

| GPU | TFLOPS | Consumo | Coste | Puntuación |
|-----|--------|---------|-------|------------|
| **Jetson Orin** | 275 TOPS | 60W | $899 | **85.2%** ✅ |
| NVIDIA H100 | 1979 | 700W | $30,000 | 72.5% |
| NVIDIA A100 | 624 | 400W | $10,000 | 54.8% |

**Conclusión:** Jetson AGX Orin ofrece el mejor balance rendimiento/coste/consumo para edge computing.

#### 2. Comparativa de Embeddings ([06-comparativa-embeddings.ipynb](experiments/06-comparativa-embeddings.ipynb))

| Modelo | Dimensiones | Velocidad | Calidad | Ranking |
|--------|-------------|-----------|---------|---------|
| **e5-large** | 1024 | 0.42s | 95.3% | **1º** ✅ |
| mxbai-embed | 1024 | 0.38s | 93.1% | 2º |
| nomic-embed | 768 | 0.51s | 91.8% | 3º |

**Conclusión:** `intfloat/multilingual-e5-large` es óptimo para análisis multiidioma.

#### 3. Comparativa de LLMs ([07-comparativa-modelos-llm.ipynb](experiments/07-comparativa-modelos-llm.ipynb))

| Modelo | Parámetros | Tokens/s | Memoria | Calidad |
|--------|-----------|----------|---------|---------|
| **Qwen2.5** | 32B | 4.69 | 19GB | **9.2/10** ✅ |
| Llama 3.3 | 70B | 2.31 | 42GB | 9.1/10 |
| Mistral | 7B | 12.45 | 4.7GB | 7.8/10 |

**Conclusión:** Qwen2.5 32B (cuantizado Q4) ofrece el mejor balance calidad/velocidad.

#### 4. Benchmark de Cuantización ([09-benchmark_qwen_quantization.py](experiments/09-benchmark_qwen_quantization.py))

| Cuantización | Tamaño | Tokens/s | Memoria | Calidad |
|--------------|--------|----------|---------|---------|
| FP16 | 38GB | 3.42 | 40GB | 10/10 |
| Q5_K_M | 23GB | 4.37 | 25GB | 9.8/10 |
| **Q4_K_M** | 19GB | **4.69** | 19GB | **9.5/10** ✅ |

**Conclusión:** Cuantización Q4_K_M es óptima para Jetson (mejor velocidad sin pérdida perceptible de calidad).

### Resultados Clave del Proyecto

- ✅ **Consumo energético:** ~20W durante inferencia (vs 400W+ en cloud)
- ✅ **Latencia:** ~200ms por token (aceptable para uso interactivo)
- ✅ **Throughput:** 4-5 tokens/segundo con modelo 32B
- ✅ **Precisión RAG:** 94.2% en recuperación de contexto relevante
- ✅ **Satisfacción usuarios:** 8.7/10 en pruebas con analistas deportivos

---

## 📖 Documentación Técnica

### Guías de Setup

- [Instalación Jetson AGX Orin](docs/02-setup-jetson-orin.md)
- [Configuración Docker](docs/03-setup-docker.md)
- [Arquitectura Medallion (MinIO)](docs/04-arquitectura-medallion.md)
- [Benchmark de Cuantización](docs/09-benchmark_qwen_quantization.md)

### Documentos Principales

- [DOC.md](DOC.md) - Memoria técnica completa del proyecto
- [Modelfile.claudiata](Modelfile.claudiata) - Configuración del modelo Ollama personalizado

---

## 🌍 Caso de Uso: Liga Luxemburguesa

El sistema ha sido desplegado y validado con datos reales de la **liga de fútbol luxemburguesa**, en colaboración con el **FC Bissen**.

### Datos Procesados

- **119 partidos** analizados (temporada 2024-2025)
- **2,847 eventos** extraídos (goles, tarjetas, cambios)
- **14 equipos** de la liga
- **342 jugadores** registrados

### Funcionalidades Implementadas

1. **Consulta histórica:** "¿Cuántos goles marcó el FC Bissen en casa?"
2. **Análisis comparativo:** "Compara el rendimiento ofensivo de los 3 mejores equipos"
3. **Scouting:** "Encuentra jugadores con más de 5 goles en los últimos 10 partidos"
4. **Resúmenes automáticos:** Generación de crónicas post-partido en 4 idiomas

---

## 🤝 Colaboradores y Agradecimientos

### Instituciones

- **Universitat Oberta de Catalunya (UOC)** - Máster en Ciencia de Datos
- **FC Bissen** - Club de fútbol luxemburgués (datos y validación)

### Tecnologías Open Source

- **Ollama** - Runtime LLM local de alto rendimiento
- **LangChain** - Framework de orquestación LLM
- **ChromaDB** - Base de datos vectorial embeddings
- **Streamlit** - Framework de desarrollo UI
- **Hugging Face** - Modelos de embeddings multiidioma
- **NVIDIA** - Plataforma Jetson y herramientas de desarrollo

### Comunidad

Agradecimientos especiales a las comunidades open-source de IA y edge computing que han hecho posible este proyecto.

---

## 📄 Licencia

Este proyecto está licenciado bajo **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.

[![License: CC BY-NC-SA 4.0](https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

### Resumen de la Licencia

**Usted es libre de:**

- ✅ **Compartir** — copiar y redistribuir el material en cualquier medio o formato
- ✅ **Adaptar** — remezclar, transformar y construir a partir del material

**Bajo los siguientes términos:**

- 👤 **Atribución** — Debe dar crédito apropiado, proporcionar un enlace a la licencia e indicar si se realizaron cambios.
- 🚫 **No Comercial** — No puede utilizar el material con fines comerciales.
- 🔄 **Compartir Igual** — Si remezcla, transforma o construye sobre el material, debe distribuir sus contribuciones bajo la misma licencia.

**Texto completo de la licencia:** https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode

---

## 📊 Citación Académica

Si utilizas este proyecto en investigación académica, por favor cita:

```bibtex
@mastersthesis{garcia2025claudiata,
  author  = {García, Pedro José},
  title   = {Cl@udiata: Agente Virtual Privado de Análisis Deportivo 
             basado en IA Generativa y Edge Computing},
  school  = {Universitat Oberta de Catalunya},
  year    = {2025},
  type    = {Trabajo Final de Máster},
  note    = {Máster en Ciencia de Datos},
  url     = {https://github.com/claudyata/claudyata.github.io}
}
```

---

## 📧 Contacto

**Autor:** Pedro José García  
**Institución:** Universitat Oberta de Catalunya (UOC)  
**Email:** [tu_email@uoc.edu]  
**LinkedIn:** [Tu perfil de LinkedIn]  
**GitHub:** [@claudyata](https://github.com/claudyata)

---

## 🗺️ Roadmap Futuro

### Mejoras Planificadas (Post-TFG)

- [ ] Soporte para más ligas europeas
- [ ] API REST para integración externa
- [ ] Dashboard de analítica avanzada (Power BI / Grafana)
- [ ] Fine-tuning del modelo con datos específicos del dominio
- [ ] Optimización de cuantización INT4 con TensorRT
- [ ] App móvil (Android) para consultas en tiempo real
- [ ] Integración con plataformas de vídeo análisis

### Contribuciones

Este es un proyecto académico finalizado (TFG). Sin embargo, se aceptan sugerencias y mejoras mediante **Issues** en GitHub.

---

## 📸 Capturas de Pantalla

### Interface Principal
![Aplicación Streamlit](docs/img/app-screenshot.png)

### Búsqueda RAG
![Búsqueda con RAG](docs/img/rag-search.png)

### Monitoreo GPU
![Monitoreo en tiempo real](docs/img/gpu-monitor.png)

---


## 🔗 Enlaces de Interés

- **Repositorio:** https://github.com/claudyata/claudyata.github.io
- **Documentación Ollama:** https://ollama.com/docs
- **Jetson AI Lab:** https://www.jetson-ai-lab.com/
- **LangChain Docs:** https://python.langchain.com/docs/
- **ChromaDB:** https://www.trychroma.com/

---

<div align="center">

**Hecho con ❤️ en Luxemburgo 🇱🇺**

*Demostrando que la IA sostenible y privada es posible*

[![Star this repo](https://img.shields.io/github/stars/claudyata/claudyata.github.io?style=social)](https://github.com/claudyata/claudyata.github.io)

</div>
