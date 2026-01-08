"""
traductor_pipeline.py
===========================
Pipeline ETL: PLATA → ORO con traducción multilingüe y vectorización

CONFIGURACIÓN ACTUALIZADA para proyecto claudia-data-tfg:
- MinIO: 192.168.1.22:9000
- Credenciales: *** / ***
- Buckets: bronce, plata, oro
- Ollama: 192.168.1.22:11434

Funcionalidades:
- Traducción luxemburgués → español + inglés (Qwen2.5:32B)
- Generación de embeddings para RAG
- Índice vectorial ChromaDB
- Agregaciones estadísticas
- Validación calidad traducciones

Autor: Pedro José García Fernández
Fecha: 2025-12-26
Sesión: DWH-11
"""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import re
from io import BytesIO

try:
    from core.config import *
except ImportError as e:
    from config import *

# Ollama para traducción
try:
    from ollama import Client as OllamaClient
except ImportError:
    print("⚠️  Instalar: pip install ollama")
    OllamaClient = None

# Sentence Transformers para embeddings
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("⚠️  Instalar: pip install sentence-transformers")
    SentenceTransformer = None

import chromadb
from chromadb.config import Settings
print(f"✅ ChromaDB {chromadb.__version__} importado correctamente")

# MinIO (boto3)
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("⚠️  Instalar: pip install boto3")
    boto3 = None

# Configuración logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

@dataclass
class OroConfig:
    """Configuración pipeline ORO"""
      
    # Procesamiento
    batch_size: int = 200  # Eventos por batch
    max_retries: int = 3
    
    # Idiomas
    source_language: str = "luxembourgish"
    target_languages: List[str] = None
    
    def __post_init__(self):
        if self.target_languages is None:
            self.target_languages = ["spanish", "english"]


# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class EventoTraducido:
    """Evento con traducciones y embedding"""
    
    # Campos originales
    match_id: int
    jornada: int
    partido: int
    minuto: str
    minuto_base: int
    minuto_adicional: int
    minuto_exacto: int
    equipo: str
    periodo: str
    
    # Textos
    texto_lb: str  # Original luxemburgués
    texto_es: str  # Traducción español
    texto_en: str  # Traducción inglés
    
    # Embedding
    embedding: List[float]
    
    # Metadata
    timestamp_traduccion: str
    modelo_traduccion: str
    modelo_embedding: str
    calidad_traduccion: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario"""
        return asdict(self)
    
    def to_chroma_document(self) -> Tuple[str, Dict, List[float]]:
        """
        Formatea para ChromaDB
        
        Returns:
            Tuple (document, metadata, embedding)
        """
        doc_id = f"match_{self.match_id}_min_{self.minuto_exacto}_{self.equipo}"
        
        metadata = {
            "match_id": self.match_id,
            "jornada": self.jornada,
            "partido": self.partido,
            "minuto": self.minuto,
            "minuto_exacto": self.minuto_exacto,
            "equipo": self.equipo,
            "periodo": self.periodo,
            "texto_lb": self.texto_lb,
            "texto_es": self.texto_es,
            "texto_en": self.texto_en,
            "timestamp": self.timestamp_traduccion
        }
        
        return doc_id, metadata, self.embedding


@dataclass
class EstadisticasEquipo:
    """Estadísticas agregadas de equipo"""
    
    equipo: str
    partidos_jugados: int
    partidos_ganados: int
    partidos_empatados: int
    partidos_perdidos: int
    goles_favor: int
    goles_contra: int
    diferencia_goles: int
    puntos: int
    racha: str  # "VEVDD" últimos 5
    
    # Métricas narrativa
    eventos_totales: int
    eventos_promedio: float
    intensidad_90_plus: float  # % eventos en tiempo añadido
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EstadisticasGoleador:
    """Estadísticas agregadas de goleador"""
    
    jugador: str
    equipo: str
    goles_totales: int
    goles_local: int
    goles_visitante: int
    minuto_promedio: float
    goles_primera_mitad: int
    goles_segunda_mitad: int
    goles_tiempo_anadido: int
    hat_tricks: int
    dobletes: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# PIPELINE TRADUCCIÓN
# ============================================================================

class TraductorPipeline:
    """Pipeline ETL: PLATA → ORO con traducción y vectorización"""
    
    def __init__(self, config: OroConfig = None):
        """
        Inicializa pipeline
        
        Args:
            config: Configuración (usa defaults si None)
        """
        self.config = config or OroConfig()
        
        # Clientes
        self.minio_client = self._init_minio()
        self.ollama_client = self._init_ollama()
        self.embedder = self._init_embedder()
        self.chroma_client = self._init_chromadb()
        
        # Colección ChromaDB
        self.collection = None
        
        logger.info("✅ TraductorPipeline inicializado")
    
    def _init_minio(self):
        """Inicializa cliente MinIO usando boto3"""
        if boto3 is None:
            raise ImportError("Instalar: pip install boto3")
        
        client = boto3.client(
            's3',
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY
        )
        
        logger.info(f"✅ MinIO conectado: {MINIO_HOST}")
        logger.info(f"   Buckets: {BUCKET_PLATA} → {BUCKET_ORO}")
        return client
    
    def _init_ollama(self) -> OllamaClient:
        """Inicializa cliente Ollama"""
        if OllamaClient is None:
            raise ImportError("Instalar: pip install ollama")
        
        client = OllamaClient(host=OLLAMA_HOST)
        
        # Verificar modelo disponible
        try:

            response = client.list()
            model_names = [m.model for m in response.models]

            if OLLAMA_MODEL not in model_names:
                logger.warning(f"⚠️  Modelo {OLLAMA_MODEL} no encontrado")
                logger.info(f"Modelos disponibles: {model_names}")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo verificar modelos Ollama: {e}")
        
        logger.info(f"✅ Ollama conectado: {OLLAMA_HOST}")
        logger.info(f"📦 Modelo: {OLLAMA_MODEL}")
        return client
    
    def _init_embedder(self) -> SentenceTransformer:
        """Inicializa modelo embeddings"""
        if SentenceTransformer is None:
            raise ImportError("Instalar: pip install sentence-transformers")
        
        model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"✅ Embedder cargado: {EMBEDDING_MODEL}")
        logger.info(f"📐 Dimensiones: {EMBEDDING_DIMENSIONS}")
        return model
    
    def _init_chromadb(self):
        """Inicializa cliente ChromaDB"""
        if chromadb is None:
            raise ImportError("Instalar: pip install chromadb")
        
        # Crear directorio si no existe
        Path(CHROMADB_PATH).mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=CHROMADB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info(f"✅ ChromaDB inicializado: {CHROMADB_PATH}")
        return client
    
    # ========================================================================
    # TRADUCCIÓN
    # ========================================================================
    
    def translate_text(
        self,
        texto: str,
        target_language: str,
        retries: int = 0
    ) -> str:
        """
        Traduce texto luxemburgués a idioma objetivo
        
        Args:
            texto: Texto en luxemburgués
            target_language: 'spanish' o 'english'
            retries: Intentos previos
            
        Returns:
            Texto traducido
        """
        try:
            # Prompt específico por idioma
            if target_language == "spanish":
                prompt = f"""Traduce el siguiente texto del luxemburgués al español.
Mantén el tono deportivo y la emoción del comentario original.
No añadas explicaciones, solo proporciona la traducción.

Texto luxemburgués: {texto}

Traducción al español:"""
            
            elif target_language == "english":
                prompt = f"""Translate the following text from Luxembourgish to English.
Maintain the sports tone and excitement of the original commentary.
Do not add explanations, just provide the translation.

Luxembourgish text: {texto}

English translation:"""
            
            else:
                raise ValueError(f"Idioma no soportado: {target_language}")
            
            # Llamada a Ollama
            response = self.ollama_client.generate(
                model=OLLAMA_MODEL,
                prompt=prompt,
                options={
                    "temperature": OLLAMA_TEMPERATURE,
                    "num_predict": 500  # Máximo tokens
                }
            )
            
            traduccion = response['response'].strip()
            
            # Validar no vacío
            if not traduccion:
                raise ValueError("Traducción vacía")
            
            return traduccion
        
        except Exception as e:
            if retries < self.config.max_retries:
                logger.warning(f"⚠️  Error traducción (intento {retries+1}): {e}")
                return self.translate_text(texto, target_language, retries + 1)
            else:
                logger.error(f"❌ Error traducción tras {self.config.max_retries} intentos: {e}")
                return f"[ERROR TRADUCCIÓN: {target_language}]"
    
    def translate_event(self, evento: Dict) -> EventoTraducido:
        """
        Traduce un evento a español + inglés y genera embedding
        
        Args:
            evento: Dict con campos del evento
            
        Returns:
            EventoTraducido con todas las traducciones
        """
        texto_lb = evento['texto']
        
        # Traducir a español
        logger.info(f"🔄 Traduciendo match {evento['match_id']} min {evento['minuto']} a español...")
        texto_es = self.translate_text(texto_lb, "spanish")
        
        # Traducir a inglés
        logger.info(f"🔄 Traduciendo match {evento['match_id']} min {evento['minuto']} a inglés...")
        texto_en = self.translate_text(texto_lb, "english")
        
        # Generar embedding del texto español
        logger.info(f"🔢 Generando embedding...")
        embedding = self.embedder.encode(texto_es).tolist()
        
        # Crear objeto
        evento_traducido = EventoTraducido(
            match_id=evento['match_id'],
            jornada=evento['jornada'],
            partido=evento['partido'],
            minuto=evento['minuto'],
            minuto_base=evento['minuto_base'],
            minuto_adicional=evento['minuto_adicional'],
            minuto_exacto=evento['minuto_exacto'],
            equipo=evento['equipo'],
            periodo=evento['periodo'],
            texto_lb=texto_lb,
            texto_es=texto_es,
            texto_en=texto_en,
            embedding=embedding,
            timestamp_traduccion=datetime.now().isoformat(),
            modelo_traduccion=OLLAMA_MODEL,
            modelo_embedding=EMBEDDING_MODEL
        )
        
        logger.info(f"✅ Evento traducido: match {evento['match_id']} min {evento['minuto']}")
        return evento_traducido
    
    # ========================================================================
    # CARGA DATOS PLATA
    # ========================================================================
    
    def load_eventos_plata(self, temporada: str = "2025-2026") -> pd.DataFrame:
        """
        Carga eventos CSV desde PLATA
        
        Args:
            temporada: Temporada (ej: "2025-2026")
            
        Returns:
            DataFrame con eventos
        """
        try:
            # Listar archivos en PLATA/eventos
            prefix = f"{PLATA_EVENTOS_PATH}"
            
            response = self.minio_client.list_objects_v2(
                Bucket=BUCKET_PLATA,
                Prefix=prefix
            )
            
            dfs = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.csv'):
                    logger.info(f"📥 Cargando {obj['Key']}...")
                    
                    # Descargar
                    file_obj = self.minio_client.get_object(
                        Bucket=BUCKET_PLATA,
                        Key=obj['Key']
                    )
                    
                    # Leer CSV
                    df = pd.read_csv(BytesIO(file_obj['Body'].read()))
                    dfs.append(df)
            
            # Concatenar
            if not dfs:
                raise ValueError(f"No se encontraron eventos CSV en {prefix}")
            
            eventos_df = pd.concat(dfs, ignore_index=True)
            logger.info(f"✅ {len(eventos_df)} eventos cargados desde PLATA")
            
            return eventos_df
            
        except Exception as e:
            logger.error(f"❌ Error cargando eventos PLATA: {e}")
            raise
    
    def load_equipos_plata(self) -> pd.DataFrame:
        """Carga equipos CSV desde PLATA"""
        try:
            # Buscar archivo equipos
            prefix = PLATA_EQUIPOS_PATH
            
            response = self.minio_client.list_objects_v2(
                Bucket=BUCKET_PLATA,
                Prefix=prefix
            )
            
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.csv'):
                    logger.info(f"📥 Cargando {obj['Key']}...")
                    
                    file_obj = self.minio_client.get_object(
                        Bucket=BUCKET_PLATA,
                        Key=obj['Key']
                    )
                    
                    df = pd.read_csv(BytesIO(file_obj['Body'].read()))
                    logger.info(f"✅ {len(df)} equipos cargados desde PLATA")
                    return df
            
            raise ValueError(f"No se encontró archivo equipos en {prefix}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando equipos PLATA: {e}")
            raise
    
    def load_goleadores_plata(self) -> pd.DataFrame:
        """Carga goleadores CSV desde PLATA"""
        try:
            prefix = PLATA_GOLEADORES_PATH
            
            response = self.minio_client.list_objects_v2(
                Bucket=BUCKET_PLATA,
                Prefix=prefix
            )
            
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.csv'):
                    logger.info(f"📥 Cargando {obj['Key']}...")
                    
                    file_obj = self.minio_client.get_object(
                        Bucket=BUCKET_PLATA,
                        Key=obj['Key']
                    )
                    
                    df = pd.read_csv(BytesIO(file_obj['Body'].read()))
                    logger.info(f"✅ {len(df)} goles cargados desde PLATA")
                    return df
            
            raise ValueError(f"No se encontró archivo goleadores en {prefix}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando goleadores PLATA: {e}")
            raise
    
    # ========================================================================
    # PROCESAMIENTO BATCH
    # ========================================================================
    
    def process_eventos_batch(
        self,
        eventos_df: pd.DataFrame,
        batch_size: int = None
    ) -> List[EventoTraducido]:
        """
        Procesa eventos en batches
        
        Args:
            eventos_df: DataFrame con eventos
            batch_size: Tamaño batch (usa config si None)
            
        Returns:
            Lista de EventoTraducido
        """
        batch_size = batch_size or self.config.batch_size
        
        eventos_traducidos = []
        total = len(eventos_df)
        
        logger.info(f"🚀 Procesando {total} eventos en batches de {batch_size}...")
        
        for i in range(0, total, batch_size):
            batch = eventos_df.iloc[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            logger.info(f"📦 Batch {batch_num}/{total_batches} ({len(batch)} eventos)")
            
            for idx, row in batch.iterrows():
                try:
                    evento_dict = row.to_dict()
                    evento_traducido = self.translate_event(evento_dict)
                    eventos_traducidos.append(evento_traducido)
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando evento {idx}: {e}")
                    continue
        
        logger.info(f"✅ {len(eventos_traducidos)} eventos traducidos correctamente")
        return eventos_traducidos
    
    # ========================================================================
    # CHROMADB
    # ========================================================================
    
    def create_vector_index(
        self,
        eventos_traducidos: List[EventoTraducido],
        collection_name: str = None
    ):
        """
        Crea índice vectorial en ChromaDB
        
        Args:
            eventos_traducidos: Lista de eventos traducidos
            collection_name: Nombre colección (usa config si None)
        """
        collection_name = collection_name or CHROMADB_COLLECTION
        
        # Eliminar colección existente si existe
        try:
            self.chroma_client.delete_collection(collection_name)
            logger.info(f"🗑️  Colección existente eliminada: {collection_name}")
        except:
            pass
        
        # Crear colección
        self.collection = self.chroma_client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": CHROMADB_DISTANCE}
        )
        
        logger.info(f"📚 Colección creada: {collection_name}")
        logger.info(f"🔢 Indexando {len(eventos_traducidos)} documentos...")
        
        # Preparar documentos
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        for evento in eventos_traducidos:
            doc_id, metadata, embedding = evento.to_chroma_document()
            
            ids.append(doc_id)
            documents.append(evento.texto_es)  # Texto español como documento
            embeddings.append(embedding)
            metadatas.append(metadata)
        
        # Insertar en batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_embeds = embeddings[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            
            self.collection.add(
                ids=batch_ids,
                documents=batch_docs,
                embeddings=batch_embeds,
                metadatas=batch_metas
            )
            
            logger.info(f"✅ Batch {i//batch_size + 1}: {len(batch_ids)} docs indexados")
        
        logger.info(f"🎉 Índice vectorial creado: {len(ids)} documentos")
 
    def append_to_vector_index(
            self,
            eventos_traducidos: List[EventoTraducido],
            collection_name: str = None
        ):
            """
            Agrega eventos al índice vectorial SIN eliminarlo
            
            Args:
                eventos_traducidos: Lista de eventos traducidos a agregar
                collection_name: Nombre colección (usa config si None)
                
            Uso:
                # Primera vez
                pipeline.create_vector_index(eventos1)
                
                # Agregar más después
                pipeline.append_to_vector_index(eventos2)
                pipeline.append_to_vector_index(eventos3)
            """
            collection_name = collection_name or CHROMADB_COLLECTION
            
            # Obtener o crear colección
            try:
                self.collection = self.chroma_client.get_collection(collection_name)
                count_antes = self.collection.count()
                logger.info(f"📚 Colección existente cargada: {collection_name} ({count_antes} docs)")
            except:
                # No existe, crearla
                self.collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": CHROMADB_DISTANCE}
                )
                logger.info(f"📚 Nueva colección creada: {collection_name}")
                count_antes = 0
            
            logger.info(f"➕ Agregando {len(eventos_traducidos)} documentos nuevos...")
            
            # Preparar documentos
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for evento in eventos_traducidos:
                doc_id, metadata, embedding = evento.to_chroma_document()
                
                ids.append(doc_id)
                documents.append(evento.texto_es)
                embeddings.append(embedding)
                metadatas.append(metadata)
            
            # Insertar en batches
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i+batch_size]
                batch_docs = documents[i:i+batch_size]
                batch_embeds = embeddings[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                
                self.collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    embeddings=batch_embeds,
                    metadatas=batch_metas
                )
                
                logger.info(f"✅ Batch {i//batch_size + 1}: {len(batch_ids)} docs agregados")
            
            count_despues = self.collection.count()
            nuevos = count_despues - count_antes
            logger.info(f"🎉 Índice actualizado: +{nuevos} docs (total: {count_despues})")

    def load_existing_index(self, collection_name: str = None) -> bool:
            """
            Carga un índice vectorial existente sin modificarlo
            
            Args:
                collection_name: Nombre colección (usa config si None)
                
            Returns:
                True si el índice existe y se cargó, False si no existe
                
            Uso:
                # Cargar índice existente
                if pipeline.load_existing_index():
                    results = pipeline.query_vector_index("gol")
                else:
                    print("Crear índice primero")
            """
            collection_name = collection_name or CHROMADB_COLLECTION
            
            try:
                self.collection = self.chroma_client.get_collection(collection_name)
                count = self.collection.count()
                logger.info(f"✅ Índice cargado: {collection_name} ({count} documentos)")
                return True
            except Exception as e:
                logger.warning(f"⚠️  Índice '{collection_name}' no existe: {e}")
                logger.info("💡 Crear índice con create_vector_index() o append_to_vector_index()")
                return False

    def query_vector_index(
        self,
        query_text: str,
        n_results: int = 5,
        filters: Dict = None
    ) -> Dict:
        """
        Consulta índice vectorial
        
        Args:
            query_text: Texto de búsqueda (español)
            n_results: Número de resultados
            filters: Filtros metadata (ej: {"match_id": 10895})
            
        Returns:
            Dict con resultados
        """
        if self.collection is None:
            raise ValueError("Índice vectorial no creado. Ejecutar create_vector_index() primero")
        
        # Generar embedding de la query
        query_embedding = self.embedder.encode(query_text).tolist()
        
        # Consultar
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filters
        )
        
        return results
    
    # ========================================================================
    # GUARDADO ORO
    # ========================================================================
    
    def save_eventos_traducidos_oro(
        self,
        eventos_traducidos: List[EventoTraducido],
        temporada: str = "2025-2026"
    ):
        """
        Guarda eventos traducidos en ORO (Parquet + JSON)
        
        Args:
            eventos_traducidos: Lista de eventos traducidos
            temporada: Temporada
        """
        # Convertir a DataFrame
        df = pd.DataFrame(eventos_traducidos)
        
        # Guardar Parquet (eficiente para análisis)
        parquet_path = f"{ORO_PATH}eventos_traducidos.parquet"
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
        parquet_buffer.seek(0)
        
        self.minio_client.put_object(
            Bucket=BUCKET_ORO,
            Key=parquet_path,
            Body=parquet_buffer.getvalue()
        )
        
        logger.info(f"✅ Parquet guardado: {parquet_path}")
        
        # Guardar JSON (para consumo APIs)
        json_path = f"{ORO_PATH}eventos_traducidos.json"
        json_data = df.to_json(orient='records', force_ascii=False, indent=2)
        
        self.minio_client.put_object(
            Bucket=BUCKET_ORO,
            Key=json_path,
            Body=json_data.encode('utf-8')
        )
        
        logger.info(f"✅ JSON guardado: {json_path}")
    
    def save_estadisticas_oro(
        self,
        estadisticas_equipos: List[EstadisticasEquipo],
        estadisticas_goleadores: List[EstadisticasGoleador],
        temporada: str = "2025-2026"
    ):
        """
        Guarda estadísticas en ORO
        
        Args:
            estadisticas_equipos: Lista estadísticas equipos
            estadisticas_goleadores: Lista estadísticas goleadores
            temporada: Temporada
        """
        # Equipos CSV    
        equipos_df = pd.DataFrame(estadisticas_equipos)
        equipos_path = f"{ORO_ANALYTICS_PATH}estadisticas_equipos.csv"
        
        csv_buffer = BytesIO()
        equipos_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        self.minio_client.put_object(
            Bucket=BUCKET_ORO,
            Key=equipos_path,
            Body=csv_buffer.getvalue()
        )
        
        logger.info(f"✅ Estadísticas equipos guardadas: {equipos_path}")
        
        # Goleadores CSV
        goleadores_df = pd.DataFrame(estadisticas_goleadores)

        goleadores_path = f"{ORO_ANALYTICS_PATH}estadisticas_goleadores.csv"
        
        csv_buffer = BytesIO()
        goleadores_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        self.minio_client.put_object(
            Bucket=BUCKET_ORO,
            Key=goleadores_path,
            Body=csv_buffer.getvalue()
        )
        
        logger.info(f"✅ Estadísticas goleadores guardadas: {goleadores_path}")
    
    # ========================================================================
    # AGREGACIONES (placeholder - implementar según necesidad)
    # ========================================================================
    
    def calcular_estadisticas_equipos(self, equipos_df, goleadores_df, eventos_df):
        """
        Calcula estadísticas agregadas por equipo
        
        Args:
            equipos_df: DataFrame con partidos (match_id, equipo_local, equipo_visitante)
            goleadores_df: DataFrame con goles (match_id, equipo_marca, tipo='Gol')
            eventos_df: DataFrame con eventos (match_id, equipo, texto)
        
        Returns:
            list[dict]: Estadísticas por equipo
        """
        logger.info("📊 Calculando estadísticas de equipos...")
        
        try:
            # Obtener todos los equipos únicos
            equipos_locales = set(equipos_df['equipo_local'].unique())
            equipos_visitantes = set(equipos_df['equipo_visitante'].unique())
            todos_equipos = sorted(equipos_locales | equipos_visitantes)
            
            estadisticas = []
            
            for equipo in todos_equipos:
                # Partidos como local y visitante
                partidos_local = equipos_df[equipos_df['equipo_local'] == equipo]
                partidos_visitante = equipos_df[equipos_df['equipo_visitante'] == equipo]
                
                total_partidos = len(partidos_local) + len(partidos_visitante)
                
                # Goles a favor y en contra
                goles_favor = len(goleadores_df[
                    (goleadores_df['equipo_marca'] == equipo) & 
                    (goleadores_df['tipo'] == 'Gol')
                ])
                
                # Goles en contra (cuando el otro equipo marca)
                goles_contra_local = len(goleadores_df[
                    (goleadores_df['match_id'].isin(partidos_local['match_id'])) &
                    (goleadores_df['equipo_marca'] != equipo) &
                    (goleadores_df['tipo'] == 'Gol')
                ])
                
                goles_contra_visitante = len(goleadores_df[
                    (goleadores_df['match_id'].isin(partidos_visitante['match_id'])) &
                    (goleadores_df['equipo_marca'] != equipo) &
                    (goleadores_df['tipo'] == 'Gol')
                ])
                
                goles_contra = goles_contra_local + goles_contra_visitante
                
                # Calcular resultados (simplificado - basado en goles)
                victorias = 0
                empates = 0
                derrotas = 0
                
                # Por cada partido, contar resultado
                for match_id in partidos_local['match_id']:
                    goles_eq = len(goleadores_df[
                        (goleadores_df['match_id'] == match_id) & 
                        (goleadores_df['equipo_marca'] == equipo) &
                        (goleadores_df['tipo'] == 'Gol')
                    ])
                    goles_rival = len(goleadores_df[
                        (goleadores_df['match_id'] == match_id) & 
                        (goleadores_df['equipo_marca'] != equipo) &
                        (goleadores_df['tipo'] == 'Gol')
                    ])
                    
                    if goles_eq > goles_rival:
                        victorias += 1
                    elif goles_eq == goles_rival:
                        empates += 1
                    else:
                        derrotas += 1
                
                for match_id in partidos_visitante['match_id']:
                    goles_eq = len(goleadores_df[
                        (goleadores_df['match_id'] == match_id) & 
                        (goleadores_df['equipo_marca'] == equipo) &
                        (goleadores_df['tipo'] == 'Gol')
                    ])
                    goles_rival = len(goleadores_df[
                        (goleadores_df['match_id'] == match_id) & 
                        (goleadores_df['equipo_marca'] != equipo) &
                        (goleadores_df['tipo'] == 'Gol')
                    ])
                    
                    if goles_eq > goles_rival:
                        victorias += 1
                    elif goles_eq == goles_rival:
                        empates += 1
                    else:
                        derrotas += 1
                
                # Puntos (3 por victoria, 1 por empate)
                puntos = (victorias * 3) + empates
                
                # Diferencia de goles
                diferencia_goles = goles_favor - goles_contra
                
                # Promedios
                promedio_gf = round(goles_favor / total_partidos, 2) if total_partidos > 0 else 0
                promedio_gc = round(goles_contra / total_partidos, 2) if total_partidos > 0 else 0
                
                estadisticas.append({
                    'equipo': equipo,
                    'partidos_jugados': total_partidos,
                    'victorias': victorias,
                    'empates': empates,
                    'derrotas': derrotas,
                    'goles_favor': goles_favor,
                    'goles_contra': goles_contra,
                    'diferencia_goles': diferencia_goles,
                    'puntos': puntos,
                    'promedio_gf': promedio_gf,
                    'promedio_gc': promedio_gc,
                    'partidos_local': len(partidos_local),
                    'partidos_visitante': len(partidos_visitante)
                })
            
            # Ordenar por puntos (descendente) y diferencia de goles
            estadisticas = sorted(
                estadisticas, 
                key=lambda x: (x['puntos'], x['diferencia_goles'], x['goles_favor']), 
                reverse=True
            )
            
            logger.info(f"✅ Estadísticas calculadas para {len(estadisticas)} equipos")
            return estadisticas
        
        except Exception as e:
            logger.error(f"❌ Error calculando estadísticas de equipos: {e}")
            return []


    def calcular_estadisticas_goleadores(self, goleadores_df):
        """
        Calcula estadísticas de goleadores
        
        Args:
            goleadores_df: DataFrame con goles (jugador, equipo_marca, tipo='Gol')
        
        Returns:
            list[dict]: Estadísticas de goleadores
        """
        logger.info("⚽ Calculando estadísticas de goleadores...")
        
        try:
            # Filtrar solo goles (no autogoles, tarjetas, etc.)
            goles = goleadores_df[goleadores_df['tipo'] == 'Gol'].copy()
            
            if len(goles) == 0:
                logger.warning("⚠️ No hay goles registrados")
                return []
            
            # Agrupar por jugador
            estadisticas_jugadores = goles.groupby(['jugador', 'equipo_marca']).agg({
                'match_id': 'count',  # Total de goles
                'jornada': ['min', 'max'],  # Primera y última jornada con gol
                'minuto': lambda x: list(x)  # Minutos de los goles
            }).reset_index()
            
            # Renombrar columnas
            estadisticas_jugadores.columns = [
                'jugador', 
                'equipo', 
                'goles', 
                'primera_jornada', 
                'ultima_jornada',
                'minutos_goles'
            ]
            
            # Calcular partidos con gol
            estadisticas_jugadores['partidos_con_gol'] = goles.groupby(
                ['jugador', 'equipo_marca']
            )['match_id'].nunique().values
            
            # Calcular promedio de goles por partido
            estadisticas_jugadores['promedio_goles'] = round(
                estadisticas_jugadores['goles'] / estadisticas_jugadores['partidos_con_gol'], 
                2
            )
            
            # Ordenar por goles (descendente)
            estadisticas_jugadores = estadisticas_jugadores.sort_values(
                'goles', 
                ascending=False
            )
            
            # Convertir a lista de diccionarios
            resultado = []
            for _, row in estadisticas_jugadores.iterrows():
                resultado.append({
                    'jugador': row['jugador'],
                    'equipo': row['equipo'],
                    'goles': int(row['goles']),
                    'partidos_con_gol': int(row['partidos_con_gol']),
                    'promedio_goles': float(row['promedio_goles']),
                    'primera_jornada': int(row['primera_jornada']),
                    'ultima_jornada': int(row['ultima_jornada']),
                    'racha_jornadas': int(row['ultima_jornada'] - row['primera_jornada'] + 1)
                })
            
            logger.info(f"✅ Estadísticas calculadas para {len(resultado)} goleadores")
            return resultado
        
        except Exception as e:
            logger.error(f"❌ Error calculando estadísticas de goleadores: {e}")
            return []


    def generar_tabla_clasificacion(estadisticas_equipos: list) -> pd.DataFrame:
        """
        Genera tabla de clasificación ordenada
        
        Args:
            estadisticas_equipos: Lista de dicts con estadísticas
        
        Returns:
            DataFrame con tabla de clasificación
        """
        if not estadisticas_equipos:
            return pd.DataFrame()
        
        df = pd.DataFrame(estadisticas_equipos)
        
        # Agregar posición
        df.insert(0, 'posicion', range(1, len(df) + 1))
        
        # Renombrar columnas para visualización
        df = df.rename(columns={
            'partidos_jugados': 'PJ',
            'victorias': 'V',
            'empates': 'E',
            'derrotas': 'D',
            'goles_favor': 'GF',
            'goles_contra': 'GC',
            'diferencia_goles': 'DIF',
            'puntos': 'PTS'
        })
        
        return df[['posicion', 'equipo', 'PJ', 'V', 'E', 'D', 'GF', 'GC', 'DIF', 'PTS']]


    def generar_tabla_goleadores(estadisticas_goleadores: list, top_n: int = 10) -> pd.DataFrame:
        """
        Genera tabla de goleadores (top N)
        
        Args:
            estadisticas_goleadores: Lista de dicts con estadísticas
            top_n: Número de goleadores a mostrar
        
        Returns:
            DataFrame con top goleadores
        """
        if not estadisticas_goleadores:
            return pd.DataFrame()
        
        df = pd.DataFrame(estadisticas_goleadores[:top_n])
        
        # Agregar posición
        df.insert(0, 'posicion', range(1, len(df) + 1))
        
        return df[['posicion', 'jugador', 'equipo', 'goles', 'partidos_con_gol', 'promedio_goles']]

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Configuración
    config = OroConfig()
    
    # Mostrar configuración
    print("=" * 60)
    print("🔧 CONFIGURACIÓN ORO PIPELINE")
    print("=" * 60)
    print(f"MinIO: {MINIO_HOST}")
    print(f"Ollama: {OLLAMA_HOST}")
    print(f"Modelo: {OLLAMA_MODEL}")
    print(f"ChromaDB: {CHROMADB_PATH}")
    print("=" * 60)
    
    # Inicializar pipeline
    try:
        pipeline = TraductorPipeline(config)
        print("\n✅ Pipeline inicializado correctamente")
    except Exception as e:
        print(f"\n❌ Error: {e}")
