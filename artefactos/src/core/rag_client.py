"""
rag_client.py
=============

Cliente RAG (Retrieval-Augmented Generation) usando LangChain para el agente Cl@udiata.

Arquitectura:
- Retriever: ChromaDB con embeddings multilingual-E5-large
- LLM: Ollama Qwen2.5:32b
- Framework: LangChain (chains modulares)

Por qué LangChain:
1. Integración nativa Ollama + ChromaDB
2. Chains modulares y reutilizables
3. Prompt templates profesionales
4. Memoria conversacional built-in
5. Trazabilidad y debugging

Autor: Pedro José García Fernández
Fecha: 27 Diciembre 2024
Proyecto: Cl@udiata TFG - RAG-30
"""

import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

# LangChain imports (CORREGIDO para langchain-community 0.4.1)
try:
    from langchain_community.llms import Ollama
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_core.prompts import PromptTemplate
    from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
    
    # RetrievalQA está en langchain-classic
    from langchain_classic.chains import RetrievalQA
    
except ImportError as e:
    print(f"⚠️  Error de importación: {e}")
    print("Paquetes necesarios: langchain langchain-community langchain-classic")
    raise



# Módulos del proyecto
try:
    from core.traductor_pipeline import OroConfig
    from core.medallion_storage import MedallionStorage
    #from core.shared_resources import *
except ImportError:
    from traductor_pipeline import OroConfig
    from medallion_storage import MedallionStorage
    #from shared_resources import *

try:
    from core.config import *
    from core.dependencies import *
    from core.data_loaders import *
    from core.utils import *
    from core.features import *
except ImportError:
    from config import *
    from dependencies import *
    from data_loaders import *
    from utils import *
    from features import *
    

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

# Template para respuestas RAG generales
RAG_PROMPT_TEMPLATE = """Eres Cl@udiata, un asistente experto en fútbol luxemburgués que ayuda a analizar partidos.

Contexto (eventos del partido):
{context}

Pregunta del usuario: {question}

Instrucciones:
1. Responde SOLO basándote en el contexto proporcionado
2. Si el contexto no contiene información suficiente, di "No tengo suficiente información en los eventos disponibles"
3. Sé conciso pero informativo
4. Usa terminología deportiva apropiada
5. Menciona minutos específicos cuando sea relevante

Respuesta:"""

# Template para búsqueda de eventos específicos
EVENT_SEARCH_TEMPLATE = """Dado el siguiente contexto de eventos de un partido de fútbol:

{context}

Pregunta: {question}

Proporciona una respuesta clara y concisa basada únicamente en los eventos mostrados. Menciona los minutos específicos cuando sea relevante.

Respuesta:"""


# ============================================================================
# CLIENTE RAG
# ============================================================================

class RAGClient:
    """
    Cliente RAG para consultas sobre partidos de fútbol luxemburgués.
    
    Componentes:
    - Embedder: multilingual-E5-large (mismos embeddings que indexación)
    - Vector Store: ChromaDB (índice pre-computado)
    - LLM: Qwen2.5:32b vía Ollama
    - Chain: LangChain RetrievalQA
    """
    
    def __init__(self):
        """
        Inicializa el cliente RAG.
        
        Args:
            config: Configuración RAG (usa defaults si None)
        """
        
        logger.info("🚀 Inicializando RAG Client...")
        
        # Componentes
        self.embeddings = self._init_embeddings()
        self.vectorstore = self._init_vectorstore()
        self.llm = self._init_llm()
        self.qa_chain = self._init_qa_chain()
        
        # Storage para metadata
        self.storage = MedallionStorage(
            endpoint_url=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY
        )
        
        logger.info("✅ RAG Client inicializado correctamente")
    
    def _init_embeddings(self) -> HuggingFaceEmbeddings:
        """
        Inicializa modelo de embeddings.
        
        CRÍTICO: Debe ser el MISMO modelo usado en indexación (E5-large)
        """
        logger.info(f"📐 Cargando embeddings: {EMBEDDING_MODEL}")
        
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cuda'},  # Usar GPU en Jetson
            encode_kwargs={'normalize_embeddings': True}
        )
        
        logger.info("✅ Embeddings cargados")
        return embeddings
    
    def _init_vectorstore(self) -> Chroma:
        """
        Conecta al índice vectorial ChromaDB existente.
        
        NO crea índice nuevo, solo lo carga.
        """
        logger.info(f"📚 Conectando a ChromaDB: {CHROMADB_PATH}")
        
        try:
            vectorstore = Chroma(
                collection_name=CHROMADB_COLLECTION,
                embedding_function=self.embeddings,
                persist_directory=CHROMADB_PATH
            )
            
            # Verificar que existe
            count = vectorstore._collection.count()
            logger.info(f"✅ ChromaDB cargado: {count} documentos indexados")
            
            return vectorstore
            
        except Exception as e:
            logger.error(f"❌ Error cargando ChromaDB: {e}")
            logger.info("💡 Asegúrate de haber ejecutado traductor_pipeline.py primero")
            raise
    
    def _init_llm(self) -> Ollama:
        """
        Inicializa LLM Ollama (Qwen2.5:32b).
        
        LangChain maneja la conexión Ollama automáticamente.
        """
        logger.info(f"🤖 Conectando a Ollama: {OLLAMA_ENDPOINT}")
        logger.info(f"📦 Modelo: {OLLAMA_MODEL}")
        
        # Callback para streaming (opcional)
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        
        llm = Ollama(
            base_url=OLLAMA_ENDPOINT,
            model=OLLAMA_MODEL,
            temperature=OLLAMA_TEMPERATURE,
            callbacks=callback_manager.handlers,
            num_predict=MAX_TOKENS_RESUMEN
        )
        
        logger.info("✅ Ollama conectado")
        return llm
    
    def _init_qa_chain(self) -> RetrievalQA:
        """
        Crea chain RetrievalQA de LangChain.
        
        Chain = Retriever + Prompt + LLM
        """
        logger.info("🔗 Creando RAG chain...")
        
        # Prompt template
        prompt = PromptTemplate(
            template=RAG_PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
        
        # Retriever (SIN score_threshold)
        retriever = self.vectorstore.as_retriever(
            search_kwargs={
                "k": TOP_K
            }
        )
        
        # Chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        
        logger.info("✅ RAG chain creada")
        return qa_chain
    
    def _get_retriever(self, match_id: Optional[int] = None):
        search_kwargs = {"k": TOP_K}
        if match_id is not None:
            search_kwargs["filter"] = {"match_id": match_id}
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)

    def _build_context(self, docs) -> str:
        # Evita etiquetas en español (no “contamina” al portugués)
        parts = []
        for doc in docs:
            minuto = doc.metadata.get("minuto", "?")
            equipo = doc.metadata.get("equipo", "N/A")
            parts.append(f"Minute {minuto} | Team {equipo}: {doc.page_content}")
        return "\n".join(parts)

    def _build_prompt(self, question: str, docs, language: str) -> str:
        context = self._build_context(docs)
        instr = INSTRUCCIONES.get(language, INSTRUCCIONES["es"])

        return f"""{instr}

    STRICT RULES:
    - Final answer MUST be in: {language}
    - Do NOT switch language.
    - Use ONLY CONTEXT.

    CONTEXT:
    {context}

    QUESTION:
    {question}

    ANSWER:"""

    # ========================================================================
    # CONSULTAS RAG
    # ========================================================================
    
    def query_stream(
        self,
        query: str,
        match_id: Optional[int] = None,
        language: str = 'es',
        verbose: bool = True
    ):
        """
        Ejecuta consulta RAG con streaming usando callbacks de LangChain.
        
        Args:
            query: Pregunta del usuario
            match_id: Filtrar por partido específico (opcional)
            language: Idioma de respuesta ('es', 'pt', 'en', 'de', 'fr')
            verbose: Mostrar logs detallados
            
        Yields:
            dict: Chunks de tipo 'sources', 'token', 'complete', 'error'
        """
        
        if verbose:
            logger.info(f"❓ Query (streaming): {query}")
            if match_id:
                logger.info(f"🎯 Filtrado por match_id: {match_id}")
        
        try:
            # ====================================================================
            # IMPORTS
            # ====================================================================
            
            from langchain_community.llms import Ollama
            from langchain_core.callbacks import CallbackManager, BaseCallbackHandler
            import threading
            import time
            #from core.shared_resources import INSTRUCCIONES
            
            # ====================================================================
            # PASO 1: RECUPERAR DOCUMENTOS
            # ====================================================================
            
            if match_id:
                docs = self.vectorstore.similarity_search(
                    query,
                    k=TOP_K,
                    filter={"match_id": match_id}
                )
            else:
                docs = self.vectorstore.similarity_search(
                    query,
                    k=TOP_K
                )
            
            source_docs = []
            for doc in docs:
                source_docs.append({
                    'texto': doc.page_content,
                    'metadata': doc.metadata,
                    'match_id': doc.metadata.get('match_id'),
                    'minuto': doc.metadata.get('minuto'),
                    'equipo': doc.metadata.get('equipo')
                })
            
            yield {
                'type': 'sources',
                'documents': source_docs,
                'num_sources': len(source_docs)
            }
            
            if verbose:
                logger.info(f"📚 {len(source_docs)} documentos recuperados")
            
            # ====================================================================
            # PASO 2: CONSTRUIR PROMPT MULTILINGÜE
            # ====================================================================
            
            contexto = "\n\n".join([
                f"Evento (Minuto {doc.metadata.get('minuto', '?')}): {doc.page_content}"
                for doc in docs
            ])
            

            
            prompt = f"""{INSTRUCCIONES.get(language, INSTRUCCIONES['es'])}

    CONTEXTO - Eventos del partido:
    {contexto}

    PREGUNTA: {query}

    RESPUESTA:"""
            
            # ====================================================================
            # PASO 3: CALLBACK HANDLER PERSONALIZADO
            # ====================================================================
            
            class StreamingCallbackHandler(BaseCallbackHandler):
                """Callback para capturar tokens en streaming."""
                
                def __init__(self):
                    self.tokens = []
                    self.current_text = ""
                
                def on_llm_new_token(self, token: str, **kwargs) -> None:
                    """Llamado cuando se genera un nuevo token."""
                    self.tokens.append(token)
                    self.current_text += token
            
            streaming_handler = StreamingCallbackHandler()
            
            # Crear callback manager
            #callback_manager = CallbackManager([streaming_handler])
            
            # Crear LLM con callback
            llm_streaming = Ollama(
                base_url=OLLAMA_ENDPOINT,
                model=OLLAMA_MODEL,
                temperature=0.3,
                callbacks=[streaming_handler],
                num_predict=MAX_TOKENS_RESUMEN
            )
            
            # ====================================================================
            # PASO 4: GENERAR EN THREAD SEPARADO
            # ====================================================================
            
            if verbose:
                logger.info("🤖 Generando respuesta con streaming...")
            
            generation_done = threading.Event()
            generation_error = None
            
            def generate_response():
                """Genera respuesta en thread separado."""
                nonlocal generation_error
                try:
                    llm_streaming.invoke(prompt)
                    generation_done.set()
                except Exception as e:
                    generation_error = e
                    generation_done.set()
            
            # Iniciar generación
            thread = threading.Thread(target=generate_response)
            thread.start()
            
            # ====================================================================
            # PASO 5: YIELD TOKENS A MEDIDA QUE LLEGAN
            # ====================================================================
            
            last_length = 0
            max_wait = 120  # Timeout de 2 minutos
            start_time = time.time()
            
            while not generation_done.is_set() or last_length < len(streaming_handler.current_text):
                # Verificar timeout
                if time.time() - start_time > max_wait:
                    logger.warning("⚠️ Timeout en generación")
                    break
                
                current_length = len(streaming_handler.current_text)
                
                if current_length > last_length:
                    # Hay nuevos tokens
                    new_text = streaming_handler.current_text[last_length:]
                    
                    yield {
                        'type': 'token',
                        'token': new_text,
                        'answer_partial': streaming_handler.current_text,
                        'tokens': len(streaming_handler.tokens)
                    }
                    
                    last_length = current_length
                
                time.sleep(0.05)  # Delay pequeño para no saturar
            
            thread.join(timeout=5)  # Esperar máximo 5s a que termine el thread
            
            # Verificar si hubo error
            if generation_error:
                raise generation_error
            
            # ====================================================================
            # PASO 6: YIELD RESPUESTA COMPLETA
            # ====================================================================
            
            respuesta_final = streaming_handler.current_text
            total_tokens = len(streaming_handler.tokens)
            
            if verbose:
                logger.info(f"✅ Respuesta completada ({total_tokens} tokens, {len(source_docs)} fuentes)")
            
            yield {
                'type': 'complete',
                'answer': respuesta_final,
                'source_documents': source_docs,
                'metadata': {
                    'num_sources': len(source_docs),
                    'match_id_filter': match_id,
                    'tokens_generated': total_tokens,
                    'language': language
                }
            }
        
        except Exception as e:
            logger.error(f"❌ Error en query_stream: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            yield {
                'type': 'error',
                'error': str(e),
                'query': query
            }

    def query(
        self,
        question: str,
        match_id: Optional[int] = None,
        language: str = 'es',
        verbose: bool = True
    ) -> Dict:

        if verbose:
            logger.info(f"❓ Pregunta: {question}")
            logger.info(f"🌍 Idioma: {language}")
            if match_id is not None:
                logger.info(f"🎯 Filtrado por match_id: {match_id}")

        try:
            retriever = self._get_retriever(match_id)
            docs = retriever.get_relevant_documents(question)

            prompt = self._build_prompt(question, docs, language)

            response_llm = self.llm_client.generate(
                model=self.config.llm_model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": MAX_TOKENS_RESUMEN
                }
            )

            answer = response_llm['response'].strip()

            source_docs = []
            for doc in docs:
                source_docs.append({
                    'texto': doc.page_content,
                    'metadata': doc.metadata,
                    'match_id': doc.metadata.get('match_id'),
                    'minuto': doc.metadata.get('minuto'),
                    'equipo': doc.metadata.get('equipo')
                })

            return {
                'question': question,
                'answer': answer,
                'source_documents': source_docs,
                'metadata': {
                    'num_sources': len(source_docs),
                    'match_id_filter': match_id,
                    'language': language
                }
            }

        except Exception as e:
            logger.error(f"❌ Error en query RAG: {e}")
            return {
                'question': question,
                'answer': f"Error: {str(e)}",
                'source_documents': [],
                'metadata': {'error': str(e)}
            }
    
    def search_events(
        self,
        query_text: str,
        match_id: Optional[int] = None,
        top_k: int = None
    ) -> List[Dict]:
        """
        Busca eventos similares sin generar respuesta LLM.
        
        Útil para exploración rápida.
        
        Args:
            query_text: Texto de búsqueda
            match_id: Filtrar por partido (opcional)
            top_k: Número de resultados (usa config si None)
            
        Returns:
            Lista de eventos con metadata
        """
        top_k = top_k or TOP_K
        
        logger.info(f"🔍 Buscando eventos: '{query_text}' (top {top_k})")
        
        # Buscar con o sin filtro
        if match_id:
            docs = self.vectorstore.similarity_search(
                query_text,
                k=top_k,
                filter={"match_id": match_id}
            )
        else:
            docs = self.vectorstore.similarity_search(
                query_text,
                k=top_k
            )
        
        # Formatear resultados
        eventos = []
        for doc in docs:
            eventos.append({
                'texto_es': doc.page_content,
                'texto_lb': doc.metadata.get('texto_lb', ''),
                'texto_en': doc.metadata.get('texto_en', ''),
                'match_id': doc.metadata.get('match_id'),
                'jornada': doc.metadata.get('jornada'),
                'partido': doc.metadata.get('partido'),
                'minuto': doc.metadata.get('minuto'),
                'minuto_exacto': doc.metadata.get('minuto_exacto'),
                'equipo': doc.metadata.get('equipo'),
                'periodo': doc.metadata.get('periodo')
            })
        
        logger.info(f"✅ {len(eventos)} eventos encontrados")
        return eventos
    
    def get_match_events(
        self,
        match_id: int,
        limit: int = 100
    ) -> List[Dict]:
        """
        Obtiene todos los eventos de un partido específico.
        
        Args:
            match_id: ID del partido
            limit: Máximo de eventos a retornar
            
        Returns:
            Lista de eventos ordenados por minuto
        """
        logger.info(f"📋 Obteniendo eventos del match {match_id}...")
        
        # Buscar con filtro de match_id
        # Usamos query genérica para recuperar todos
        docs = self.vectorstore.similarity_search(
            "partido fútbol evento",  # Query genérica
            k=limit,
            filter={"match_id": match_id}
        )
        
        # Formatear y ordenar
        eventos = []
        for doc in docs:
            eventos.append({
                'texto_es': doc.page_content,
                'match_id': doc.metadata.get('match_id'),
                'minuto': doc.metadata.get('minuto'),
                'minuto_exacto': doc.metadata.get('minuto_exacto', 0),
                'equipo': doc.metadata.get('equipo'),
                'periodo': doc.metadata.get('periodo')
            })
        
        # Ordenar por minuto exacto (descendente - más reciente primero)
        eventos.sort(key=lambda x: x['minuto_exacto'], reverse=True)
        
        logger.info(f"✅ {len(eventos)} eventos recuperados del match {match_id}")
        return eventos
    
    # ========================================================================
    # UTILIDADES
    # ========================================================================
    
    def get_match_info(self, match_id: int) -> Optional[Dict]:
        """
        Obtiene información del partido desde PLATA.
        
        Args:
            match_id: ID del partido
            
        Returns:
            Dict con info del partido o None
        """
        try:
            # Leer desde PLATA/equipos
            equipos_json = self.storage.leer_actas_plata(match_id=match_id)
            
            if equipos_json:
                equipos_data = json.loads(equipos_json)
                return equipos_data
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️  No se pudo cargar info match {match_id}: {e}")
            return None
    
    def list_available_matches(self) -> List[int]:
        """
        Lista todos los match_ids disponibles en el índice.
        
        Returns:
            Lista de match_ids únicos
        """
        logger.info("📂 Listando partidos disponibles...")
        
        # Obtener todos los documentos (limitado)
        all_docs = self.vectorstore.similarity_search(
            "partido",
            k=1000  # Límite razonable
        )
        
        # Extraer match_ids únicos
        match_ids = set()
        for doc in all_docs:
            mid = doc.metadata.get('match_id')
            if mid:
                match_ids.add(mid)
        
        match_ids_sorted = sorted(list(match_ids))
        logger.info(f"✅ {len(match_ids_sorted)} partidos disponibles")
        
        return match_ids_sorted
    
    def get_stats(self) -> Dict:
        """
        Estadísticas del índice vectorial.
        
        Returns:
            Dict con estadísticas
        """
        count = self.vectorstore._collection.count()
        match_ids = self.list_available_matches()
        
        return {
            'total_eventos': count,
            'total_partidos': len(match_ids),
            'promedio_eventos_partido': count / len(match_ids) if match_ids else 0,
            'match_ids': match_ids
        }

# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

def create_rag_client():
    """
    Crea un cliente RAG con configuración por defecto.

    Returns:
        RAGClient inicializado
        
    Example:
        >>> client = create_rag_client()
        >>> result = client.query("¿Quién marcó gol en el minuto 23?")
        >>> print(result['answer'])
    """
    return RAGClient()

# ============================================================================
# MAIN (Testing)
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TEST RAG CLIENT")
    print("=" * 80)
    
    # Crear cliente
    try:
        client = create_rag_client()
        
        # Estadísticas
        print("\n📊 Estadísticas del índice:")
        stats = client.get_stats()
        print(f"   Total eventos: {stats['total_eventos']}")
        print(f"   Total partidos: {stats['total_partidos']}")
        print(f"   Promedio eventos/partido: {stats['promedio_eventos_partido']:.1f}")
        
        # Test query
        print("\n❓ Query de prueba:")
        question = "¿Qué eventos importantes ocurrieron en el primer tiempo?"
        result = client.query(question, verbose=True)
        
        print(f"\n💬 Respuesta:")
        print(result['answer'])
        
        print(f"\n📚 Fuentes ({len(result['source_documents'])}):")
        for i, doc in enumerate(result['source_documents'][:3], 1):
            print(f"\n   {i}. Match {doc['match_id']} - Min {doc['minuto']}")
            print(f"      {doc['texto'][:100]}...")
        
        print("\n" + "=" * 80)
        print("✅ Test completado")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Asegúrate de:")
        print("   1. Tener ChromaDB indexado (ejecuta traductor_pipeline.py)")
        print("   2. Ollama corriendo (ollama serve)")
        print("   3. Modelo qwen2.5:32b descargado")