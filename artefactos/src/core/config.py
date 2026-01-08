from pathlib import Path
import os

# ============================================================================
# CONSTANTES - CONFIGURACIÓN GLOBAL
# ============================================================================

# Temporada y Partidos
TEMPORADA_ACTUAL = "2025-2026"
MATCH_ID_INICIAL = 10890
PARTIDOS_POR_JORNADA = 8
TOTAL_JORNADAS = 16

# Ollama LLM
OLLAMA_HOST = "192.168.1.22:11434"
OLLAMA_ENDPOINT = "http://192.168.1.22:11434"

OLLAMA_MODEL = "qwen2.5:32b"
#OLLAMA_TEMPERATURE = 0.7
OLLAMA_TEMPERATURE = 0.3  # Traducciones consistentes
OLLAMA_TIMEOUT = 120  # 2 minutos por traducción

# ChromaDB
CHROMADB_PATH = "/home/claudia/perisperis/chroma_db"
CHROMADB_COLLECTION = "eventos-futbol-luxemburgo"
CHROMADB_DISTANCE = "cosine"


# Embeddings
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIMENSIONS = 1024

# Retrieval RAG
TOP_K = 100
SCORE_THRESHOLD = 0.7

# MinIO S3
MINIO_HOST: str = "192.168.1.22:9000"
MINIO_ENDPOINT = "http://192.168.1.22:9000"
MINIO_ACCESS_KEY = "minioclaudia"
MINIO_SECRET_KEY = "minioclaudia"

# Generación de Texto
MAX_TOKENS_RESUMEN = 2048
MAX_TOKENS_DAFO = 1024
MAX_TOKENS = 500

# Buckets MinIO (Arquitectura Medallion)
BUCKET_BRONCE = "bronce"
BUCKET_PLATA = "plata"
BUCKET_ORO = "oro"

# Prefijos BRONCE
BRONCE_HTML = "html"
BRONCE_PDF = "pdf"
BRONCE_VIDEO = "video"

# Prefijos PLATA
PLATA_EVENTOS = "eventos"
PLATA_ACTAS = "actas"
PLATA_VIDEOS = "videos"

# Prefijos ORO
ORO_EMBEDDINGS = "embeddings"
ORO_ANALYTICS = "analytics"
ORO_DATABASE = "database"

    
# Rutas dentro de PLATA
PLATA_EVENTOS_PATH = "eventos/2025-2026/"
PLATA_EQUIPOS_PATH  = "equipos/"
PLATA_GOLEADORES_PATH  = "goleadores/"
    
# Rutas dentro de ORO
ORO_PATH = "embeddings/2025-2026/"
ORO_ANALYTICS_PATH = "analytics/2025-2026/"


IDIOMAS = {
    'es': {'nombre': 'Español', 'flag': '🇪🇸', 'codigo_iso': 'es'},
    'pt': {'nombre': 'Portugués', 'flag': '🇵🇹', 'codigo_iso': 'pt'},
    'en': {'nombre': 'Inglés', 'flag': '🇬🇧', 'codigo_iso': 'en'},
    'de': {'nombre': 'Alemán', 'flag': '🇩🇪', 'codigo_iso': 'de'},
    'fr': {'nombre': 'Francés', 'flag': '🇫🇷', 'codigo_iso': 'fr'},
    'lb': {'nombre': 'Luxemburgués', 'flag': '🇱🇺', 'codigo_iso': 'lb'},
}

INSTRUCCIONES = {
    'es': (
        "Eres Cl@udiata, asistente experto en fútbol luxemburgués.\n"
        "Responde SIEMPRE en español basándote SOLO en los eventos.\n"
        "Si falta info: \"No tengo suficiente información en los eventos disponibles\".\n"
        "Sé específico, conciso y menciona minutos cuando aplique."
    ),
    'pt': (
        "Você é Cl@udiata, assistente especialista em futebol luxemburguês.\n"
        "Responda SEMPRE em português (pt-PT) com base APENAS nos eventos.\n"
        "Se faltar informação: \"Não tenho informação suficiente nos eventos disponíveis\".\n"
        "Seja específico, conciso e mencione os minutos quando relevante.\n"
        "Evite português do Brasil."
    ),
    'en': (
        "You are Cl@udiata, an expert assistant in Luxembourg football.\n"
        "Answer ALWAYS in English based ONLY on the events.\n"
        "If missing: \"I don't have enough information in the available events\".\n"
        "Be specific, concise and mention minutes when relevant."
    ),
    'de': (
        "Du bist Cl@udiata, ein Experten-Assistent für luxemburgischen Fußball.\n"
        "Antworte IMMER auf Deutsch basierend NUR auf den Ereignissen.\n"
        "Wenn Infos fehlen: \"Ich habe nicht genügend Informationen in den verfügbaren Ereignissen\".\n"
        "Sei präzise, knapp und nenne Minuten, wenn relevant."
    ),
    'fr': (
        "Vous êtes Cl@udiata, assistant expert en football luxembourgeois.\n"
        "Répondez TOUJOURS en français en vous basant UNIQUEMENT sur les événements.\n"
        "Si info manquante: \"Je n'ai pas assez d'informations dans les événements disponibles\".\n"
        "Soyez précis, concis, et mentionnez les minutes si pertinent."
    ),
    'lb': (
        "Du bass Cl@udiata, en Expert-Assistent fir Lëtzebuerger Fussball.\n"
        "Äntwert ËMMER op Lëtzebuergesch an nëmme mam Kontext.\n"
        "Wa Infos feelen: \"Ech hunn net genuch Informatioun an den disponibele Evenementer\".\n"
        "Sief präzis, kuerz, a nenn d'Minutten wann et passt."
    ),
}

# Instrucciones específicas por idioma Resuemn
INSTRUCCIONES_IDIOMA = {
    'es': {
        'idioma': 'español',
        'intro': 'Eres un periodista deportivo experto. Escribe una crónica narrativa del siguiente partido de fútbol.',
        'longitud': '1000-1500 palabras',
        'estilo': 'crónica periodística profesional'
    },
    'pt': {
        'idioma': 'português',
        'intro': 'Você é um jornalista esportivo especializado. Escreva uma crônica narrativa da seguinte partida de futebol.',
        'longitud': '1000-1500 palavras',
        'estilo': 'crônica jornalística profissional'
    },
    'en': {
        'idioma': 'English',
        'intro': 'You are an expert sports journalist. Write a narrative chronicle of the following football match.',
        'longitud': '1000-1500 words',
        'estilo': 'professional journalistic chronicle'
    },
    'de': {
        'idioma': 'Deutsch',
        'intro': 'Sie sind ein erfahrener Sportjournalist. Schreiben Sie eine narrative Chronik des folgenden Fußballspiels.',
        'longitud': '1000-1500 Wörter',
        'estilo': 'professionelle journalistische Chronik'
    },
    'fr': {
        'idioma': 'français',
        'intro': 'Vous êtes un journaliste sportif expert. Rédigez une chronique narrative du match de football suivant.',
        'longitud': '1000-1500 mots',
        'estilo': 'chronique journalistique professionnelle'
    },
    'lb': {
            'idioma': 'Lëtzebuergesch',
            'intro': 'Dir sidd en Expert Sportjournalist. Schreift eng narrativ Chronik vum folgende Futtballmatch.',
            'longitud': '1000-1500 Wierder',
            'estilo': 'professionell journalistesch Chronik'
    }
}

__all__ = [
  "TEMPORADA_ACTUAL","MATCH_ID_INICIAL","PARTIDOS_POR_JORNADA","TOTAL_JORNADAS",
  "OLLAMA_HOST","OLLAMA_MODEL","OLLAMA_TEMPERATURE","OLLAMA_ENDPOINT",
  "CHROMADB_PATH","CHROMADB_COLLECTION","EMBEDDING_MODEL","TOP_K","SCORE_THRESHOLD",
  "MINIO_ENDPOINT","MINIO_ACCESS_KEY","MINIO_SECRET_KEY",
  "BUCKET_BRONCE","BUCKET_PLATA","BUCKET_ORO","EMBEDDING_DIMENSIONS",
  "BRONCE_HTML","BRONCE_PDF","BRONCE_VIDEO","MINIO_HOST",
  "PLATA_EVENTOS","PLATA_ACTAS","PLATA_VIDEOS",
  "ORO_EMBEDDINGS","ORO_ANALYTICS","ORO_DATABASE","CHROMADB_DISTANCE",
  "MAX_TOKENS_RESUMEN","MAX_TOKENS_DAFO","MAX_TOKENS",
  "IDIOMAS","INSTRUCCIONES","OLLAMA_TIMEOUT","ORO_ANALYTICS_PATH","ORO_PATH",
  "PLATA_EVENTOS_PATH","PLATA_EQUIPOS_PATH","PLATA_GOLEADORES_PATH","INSTRUCCIONES_IDIOMA"
]