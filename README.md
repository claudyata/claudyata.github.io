# 🤖 Cl@udiata - Agente de Análisis Deportivo

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36-red.svg)](https://streamlit.io/)
[![Ollama](https://img.shields.io/badge/Ollama-0.6-green.svg)](https://ollama.com/)
[![Jetson](https://img.shields.io/badge/NVIDIA-Jetson_AGX_Orin-76B900.svg)](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)

## 📖 Descripción

Agente conversacional basado en LLMs para análisis táctico y estadístico de partidos de fútbol luxemburgués. Desplegado en NVIDIA Jetson AGX Orin con arquitectura RAG (Retrieval-Augmented Generation) y almacenamiento Medallion.

**TFG - Universitat Oberta de Catalunya (UOC)**  
Máster en Ciencia de Datos  
Autor: Pedro José García

---

## 🏗️ Arquitectura

### Stack Tecnológico
- **LLM Runtime:** Ollama (Qwen2.5 32B cuantizado Q4_K_M)
- **Embeddings:** intfloat/multilingual-e5-large (1024 dims)
- **Vector DB:** ChromaDB 1.3.7
- **Framework:** Streamlit + LangChain
- **Storage:** MinIO (arquitectura Medallion: Bronze/Silver/Gold)
- **Hardware:** Jetson AGX Orin 64GB (~20W consumo)

### Arquitectura Medallion
```
Bronze (Raw)    →    Silver (Clean)    →    Gold (Processed)
   PDFs         →    CSV estructurado  →    Embeddings + Análisis
```

---

## 🚀 Instalación

### Requisitos
- NVIDIA Jetson AGX Orin (JetPack 6.2.1)
- Conda/Miniforge
- MinIO Server
- Ollama

### Setup

1. **Clonar repositorio:**
```bash
git clone https://github.com/claudyata/claudyata.github.io
cd claudyata.github.io
```

2. **Crear entorno conda:**
```bash
conda env create -f environment.yml
conda activate tfg
```

3. **Instalar Ollama y modelos:**
```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelos
ollama pull qwen2.5:32b
ollama pull mxbai-embed-large
```

4. **Configurar MinIO:**
```bash
# Ver docs/04-arquitectura-medallion.md
```

5. **Ejecutar aplicación:**
```bash
cd artefactos/src
streamlit run app.py
```

---

## 📂 Estructura del Proyecto

```
.
├── artefactos/
│   └── src/
│       ├── app.py              # Aplicación Streamlit principal
│       ├── core/               # Lógica de negocio
│       │   ├── rag_client.py   # Cliente RAG
│       │   ├── nlp_analyzer.py # Análisis NLP
│       │   └── medallion_storage.py
│       └── tabs/               # Pestañas de la UI
├── docs/                       # Documentación técnica
├── experiments/                # Notebooks experimentales
├── environment.yml             # Dependencias conda
├── Modelfile.claudiata         # Configuración modelo Ollama
└── DOC.md                      # Documentación principal

```

---

## 📊 Características Principales

### 🔍 Búsqueda RAG
- Consultas en lenguaje natural sobre partidos
- Recuperación semántica de eventos relevantes
- Respuestas contextualizadas con LLM

### 📝 Generación de Resúmenes
- Crónicas automáticas de partidos
- Multiidioma (Español, Francés, Luxemburgués, Alemán)
- Análisis táctico detallado

### 📈 Estadísticas
- Clasificación de equipos
- Top goleadores
- Análisis de rendimiento

### 💻 Monitoreo GPU
- Consumo energético en tiempo real
- Métricas de temperatura y uso
- Optimización de recursos

---

## 🧪 Experimentos y Benchmarks

### Comparativas Realizadas
- **GPUs:** Jetson Orin vs A100 vs H100 (docs/experiments/01-comparativa-gpu.ipynb)
- **Embeddings:** e5-large vs nomic-embed vs mxbai (06-comparativa-embeddings.ipynb)
- **LLMs:** Qwen2.5 vs Llama 3.3 vs Mistral (07-comparativa-modelos-llm.ipynb)
- **Cuantización:** FP16 vs Q4 vs Q5 vs Q8 (09-benchmark_qwen_quantization.py)

### Resultados Clave
- **Cuantización óptima:** Q4_K_M (19GB, 4.69 t/s)
- **Consumo promedio:** ~20W durante inferencia
- **Latencia:** ~200ms por token
- **Embedding:** e5-large (mejor balance velocidad/calidad)

---

## 📖 Documentación

- [Setup Jetson Orin](docs/02-setup-jetson-orin.md)
- [Arquitectura Medallion](docs/04-arquitectura-medallion.md)
- [Benchmark Cuantización](docs/09-benchmark_qwen_quantization.md)
- [Documento Principal](DOC.md)

---

## 🤝 Contribuciones

Este es un proyecto académico (TFG). Para consultas o sugerencias:
- 📧 Email: [tu_email@ejemplo.com]
- 💼 LinkedIn: [Tu LinkedIn]

---

## 📄 Licencia

Este proyecto está bajo licencia [Especificar Licencia].

---

## 🙏 Agradecimientos

- **UOC** - Universitat Oberta de Catalunya
- **FC Bissen** - Club de fútbol luxemburgués
- **Comunidad Ollama** - Runtime LLM open-source
- **NVIDIA** - Plataforma Jetson

---

## 📊 Citas

Si utilizas este proyecto en investigación académica, por favor cita:

```bibtex
@mastersthesis{garcia2025claudiata,
  author  = {García, Pedro José},
  title   = {Cl@udiata: Agente Conversacional para Análisis Deportivo en Edge Computing},
  school  = {Universitat Oberta de Catalunya},
  year    = {2025},
  type    = {Trabajo Final de Máster}
}
```

---

**Hecho con ❤️ en Luxemburgo 🇱🇺**
