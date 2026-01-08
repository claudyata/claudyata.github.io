# core/dependencies.py
import streamlit as st
import logging

try:
    from core.config import *
    from core.data_loaders import *
    from core.utils import *
    from core.features import *
except ImportError:
    from config import *
    from data_loaders import *
    from utils import *
    from features import *

try:
    from core.medallion_storage import MedallionStorage
except ImportError:
    from medallion_storage import MedallionStorage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CACHÉ DE INICIALIZACIÓN
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def bootstrap():
    rag_client = get_rag_client()
    nlp_analyzer = get_nlp_analyzer()
    storage = get_storage()
    partidos = load_partidos_disponibles(nlp_analyzer)
    return rag_client, nlp_analyzer, storage, partidos

# ============================================================================
# SINGLETONS - Recursos que se crean UNA SOLA VEZ
# ============================================================================

@st.cache_resource
def get_rag_client():
    """
    Singleton RAG Client.
    Se crea una sola vez y se reutiliza en toda la sesión.
    """
    try:
        from core.rag_client import create_rag_client
    except ImportError:
        from rag_client import create_rag_client

    logger.info("🔧 Inicializando RAG Client...")
    return create_rag_client()


@st.cache_resource
def get_nlp_analyzer():
    """
    Singleton NLP Analyzer.
    Reutiliza el RAG Client singleton.
    """
    

    try:
        from core.nlp_analyzer import create_nlp_analyzer
    except ImportError:
        from nlp_analyzer import create_nlp_analyzer
    
    rag_client = get_rag_client()
    logger.info("🔧 Inicializando NLP Analyzer...")
    
    return create_nlp_analyzer(rag_client=rag_client)


@st.cache_resource
def get_storage():
    """
    Singleton MedallionStorage.
    Cliente S3 para MinIO.
    """
    #from core.medallion_storage import MedallionStorage
    try:
        from core.medallion_storage import MedallionStorage
    except ImportError:
        from medallion_storage import MedallionStorage

    logger.info("🔧 Inicializando MedallionStorage...")
    
    return MedallionStorage(
        endpoint_url=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY
    )

__all__ = [
  "bootstrap","get_rag_client","get_nlp_analyzer","get_storage"
]
