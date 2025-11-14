# Arquitectura Medallion

Este documento describe la planificación y organización del almacenamiento de datos utilizando la **arquitectura Medallion** (Bronze, Silver, Gold) en nuestro sistema de datos distribuido con **MinIO**.

---

## DWH-30: Almacenamiento de datos en arquitectura Medallion

**Descripción:**  
Como estudiante, quiero que los datos sean almacenados en diferentes capas según la arquitectura Medallion:  
- **Bronze:** Datos crudos, sin procesar, tal como llegan desde las fuentes (pdf, video, html).  
- **Silver:** Datos limpios y transformados, listos para análisis (json, mp4).  
- **Gold:** Datos enriquecidos y agregados, listos para informes y consultas avanzadas (report).

**Objetivo:**  
Mantener los datos organizados en distintas capas de madurez, permitiendo un análisis incremental y controlado, y asegurando que cada etapa del pipeline tenga acceso a los datos correctos sin comprometer la seguridad ni la integridad.

---

## 1. Estructura de almacenamiento

### Bronze (Crudo)

- Contiene datos originales sin procesar.
- Ejemplos:
  - `pdf/` → actas de partidos en PDF  
  - `video/` → vídeos de partidos (Cada partido contiene multiples ts)
  - `html/` → páginas o metadatos HTML

### Silver (Limpiado)

- Contiene datos procesados y estandarizados.
- Ejemplos:
  - `json/` → datos extraídos y normalizados de PDFs o HTML  
  - `video/` → vídeos recodificados o segmentados, cada partido será un mp4

### Gold (Enriquecido)

- Contiene datos agregados y listos para análisis.
- Ejemplos:
  - `reports/` → informes de estadísticas y KPIs

---

## 2. Configuracion MinIO


1. Crear estructura medallón dentro de nuestra Jetson


```bash
# Configura variables
export ENDPOINT="http://192.168.178.84:9000"
export PROFILE="minio"

aws --endpoint-url $ENDPOINT s3 mb s3://bronze --profile $PROFILE
aws --endpoint-url $ENDPOINT s3 mb s3://silver --profile $PROFILE
aws --endpoint-url $ENDPOINT s3 mb s3://gold --profile $PROFILE

# Carpeta Bronze
aws --endpoint-url $ENDPOINT s3api put-object --bucket bronze --key pdf/ --profile $PROFILE
aws --endpoint-url $ENDPOINT s3api put-object --bucket bronze --key video/ --profile $PROFILE
aws --endpoint-url $ENDPOINT s3api put-object --bucket bronze --key html/ --profile $PROFILE
aws --endpoint-url $ENDPOINT s3 ls s3://bronze/ --profile $PROFILE

# Carpeta Silver
aws --endpoint-url $ENDPOINT s3api put-object --bucket silver --key json/ --profile $PROFILE
aws --endpoint-url $ENDPOINT s3api put-object --bucket silver --key video/ --profile $PROFILE
aws --endpoint-url $ENDPOINT s3 ls s3://silver/ --profile $PROFILE

# Carpeta Gold
aws --endpoint-url $ENDPOINT s3api put-object --bucket gold --key reports/ --profile $PROFILE
aws --endpoint-url $ENDPOINT s3 ls s3://gold/ --profile $PROFILE
```

2. Lista todos los buckets en MinIO :

```bash
aws --endpoint-url $ENDPOINT s3 ls --recursive --profile $PROFILE
```

3. Si todo está bien, verás algo como:

```yaml
2025-10-13 11:22:01 bronze
2025-10-13 11:22:01 silver
2025-10-13 11:22:01 gold
```

## 2. Beneficios de la arquitectura Medallion

1. **Control incremental del ciclo de vida de los datos:**  
   Cada capa representa un nivel de madurez, facilitando la trazabilidad y la depuración.

2. **Procesamiento escalable:**  
   Los datos crudos permanecen intactos en Bronze, mientras que Silver y Gold contienen datos preparados para análisis o visualización, permitiendo pipelines eficientes.

3. **Seguridad y organización:**  
   Permite aplicar permisos y accesos diferenciados según la capa, evitando que usuarios modifiquen los datos originales.

4. **Compatibilidad con el agente:**  
   Mantener los datos organizados por capas asegura que el agente pueda acceder de manera eficiente a datos limpios y enriquecidos para generar respuestas precisas.

---

## 3. Recomendaciones

- Usar un **disco dedicado NVMe** para el almacenamiento Bronze, garantizando suficiente capacidad y velocidad para datos crudos.  
- Configurar correctamente los permisos de MinIO para cada capa.  
- Mantener un **pipeline ETL/ELT** que mueva los datos desde Bronze → Silver → Gold de manera controlada y automatizada.  
- Documentar los tamaños y tipos de datos por capa para prever crecimiento y necesidades de almacenamiento futuro.

