"""
nlp_analyzer.py
===============

Análisis NLP de partidos de fútbol luxemburgués usando LLMs.

Funcionalidades:
- NLP-30: Resúmenes narrativos de partidos
- NLP-10: Análisis DAFO (Debilidades, Amenazas, Fortalezas, Oportunidades)

Usa Qwen2.5:32b vía Ollama para generación de texto de alta calidad.

Autor: Pedro José García Fernández
Fecha: 27 Diciembre 2024
Proyecto: Cl@udiata TFG - RAG-30
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import pandas as pd
from io import BytesIO

# Ollama
try:
    from ollama import Client as OllamaClient
except ImportError:
    print("⚠️  Instalar: pip install ollama")
    raise

# Módulos del proyecto
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

try:
    from core.medallion_storage import MedallionStorage
    #from core.shared_resources import *
except ImportError:
    from medallion_storage import MedallionStorage
    #from shared_resources import *
# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

@dataclass
class NLPConfig:
    """Configuración del analizador NLP"""

# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

RESUMEN_PARTIDO_TEMPLATE = """Eres un periodista deportivo experto en fútbol luxemburgués.

Eventos del partido (orden cronológico):
{eventos}

Información del partido:
- Equipo Local: {equipo_local}
- Equipo Visitante: {equipo_visitante}
- Jornada: {jornada}

Instrucciones:
1. Genera un resumen NARRATIVO del partido estilo crónica periodística
2. Estructura: Introducción → Desarrollo cronológico → Conclusión
3. Menciona los momentos clave (goles, jugadas importantes)
4. Usa lenguaje deportivo profesional pero accesible
5. Máximo 800-1000 palabras
6. NO inventes información que no esté en los eventos

Resumen del partido:"""


ANALISIS_DAFO_TEMPLATE = """Eres un analista táctico de fútbol especializado en el fútbol luxemburgués.

Eventos del partido:
{eventos}

Equipo a analizar: {equipo}

Realiza un análisis DAFO (SWOT en inglés) del equipo basándote ÚNICAMENTE en los eventos mostrados:

**DEBILIDADES (Weaknesses):**
- Aspectos negativos internos del equipo observados en el partido
- Errores tácticos, técnicos o individuales

**AMENAZAS (Threats):**
- Factores externos que afectaron negativamente
- Fortalezas del rival que causaron problemas

**FORTALEZAS (Strengths):**
- Aspectos positivos del rendimiento del equipo
- Jugadas exitosas, buena ejecución táctica

**OPORTUNIDADES (Opportunities):**
- Momentos donde el equipo pudo capitalizar pero no lo hizo completamente
- Aspectos mejorables detectados

Formato de respuesta (JSON):
{{
  "debilidades": ["punto 1", "punto 2", ...],
  "amenazas": ["punto 1", "punto 2", ...],
  "fortalezas": ["punto 1", "punto 2", ...],
  "oportunidades": ["punto 1", "punto 2", ...]
}}

IMPORTANTE: Responde SOLO con el JSON, sin texto adicional.

Análisis DAFO:"""


# ============================================================================
# ANALIZADOR NLP
# ============================================================================

class NLPAnalyzer:
    """
    Analizador NLP para partidos de fútbol.
    
    Funcionalidades:
    - Resúmenes narrativos (NLP-30)
    - Análisis DAFO por equipo (NLP-10)
    """
    
    def __init__(self, config: NLPConfig = None, rag_client=None):
        """
        Inicializa el analizador NLP.
        
        Args:
            config: Configuración NLP (usa defaults si None)
            rag_client: Cliente RAG para búsqueda de eventos (opcional)
        """
        self.config = config or NLPConfig()
        
        logger.info("🚀 Inicializando NLP Analyzer...")
        
        # Clientes
        self.ollama_client = self._init_ollama()
        self.storage = MedallionStorage(
            endpoint_url=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY
        )
        
        # RAG Client (si se proporciona)
        self.rag_client = rag_client
        
        # Si no se proporciona, intentar crear uno
        if self.rag_client is None:
            try:
                from rag_client import create_rag_client
                logger.info("📚 Creando RAG Client...")
                self.rag_client = create_rag_client()
            except Exception as e:
                logger.warning(f"⚠️  No se pudo crear RAG Client: {e}")
                logger.warning("⚠️  Se usará MinIO como fallback para eventos")
                self.rag_client = None
        
        logger.info("✅ NLP Analyzer inicializado")
    
    def _init_ollama(self) -> OllamaClient:
        """Inicializa cliente Ollama"""
        logger.info(f"🤖 Conectando a Ollama: {OLLAMA_HOST}")
        
        client = OllamaClient(host=OLLAMA_HOST)
        
        # Verificar modelo disponible
        try:
            response = client.list()
            model_names = [m.model for m in response.models]
            
            if OLLAMA_MODEL not in model_names:
                logger.warning(f"⚠️  Modelo {OLLAMA_MODEL} no encontrado")
                logger.info(f"Modelos disponibles: {model_names}")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo verificar modelos: {e}")
        
        logger.info(f"✅ Ollama conectado: {OLLAMA_MODEL}")
        return client
    
    # ========================================================================
    # NLP-30: RESÚMENES DE PARTIDOS
    # ========================================================================
    def generar_resumen_partido(self, match_id, verbose=True, stream=False, idioma='es'):
        """
        Genera resumen narrativo del partido
        
        Args:
            match_id: ID del partido
            verbose: Mostrar logs
            stream: Si True, retorna generador para streaming
            idioma: Código ISO del idioma ('es', 'pt', 'en', 'de', 'fr')
        
        Returns:
            Si stream=False: Dict con resumen completo
            Si stream=True: Generador que yield tokens
        """
        
        if verbose:
            print(f"\n📝 Generando resumen para Match {match_id} en {idioma.upper()}...")
        
        # Cargar eventos
        if self.rag_client:
            try:
                eventos = self.rag_client.get_match_events(match_id)
                if verbose:
                    logger.info(f"✅ Eventos cargados desde RAG: {len(eventos)}")
            except Exception as e:
                if verbose:
                    logger.warning(f"⚠️  Error con RAG client: {e}, usando MinIO...")
                eventos = self._load_eventos_from_minio(match_id)
        else:
            eventos = self._load_eventos_from_minio(match_id)
        
        if not eventos:
            return {'error': f'No se encontraron eventos para Match {match_id}'}
        
        # Cargar info del partido
        if verbose:
            logger.info("📋 Cargando info del partido desde CSV...")
        
        match_info = self._load_match_info(match_id)
        
        equipo_local = match_info.get('equipo_local', 'Equipo Local')
        equipo_visitante = match_info.get('equipo_visitante', 'Equipo Visitante')
        jornada = match_info.get('jornada', 'N/A')
        
        if verbose:
            logger.info(f"🏟️  {equipo_local} vs {equipo_visitante} (Jornada {jornada})")
        
        # Ordenar eventos
        eventos_sorted = sorted(eventos, key=lambda x: x.get('minuto_exacto', 0))
        
        contexto_eventos = "\n".join([
            f"- Minuto {e.get('minuto', '?')} ({e.get('equipo', 'Desconocido')}): {e.get('texto_es', '')}"
            for e in eventos_sorted
        ])
        
        # ========================================================================
        # PROMPT MULTILINGÜE
        # ========================================================================

        instrucciones = INSTRUCCIONES_IDIOMA.get(idioma, INSTRUCCIONES_IDIOMA['es'])
        
        prompt = f"""{instrucciones['intro']}

    PARTIDO: {equipo_local} vs {equipo_visitante} (Jornada {jornada})

    EVENTOS DEL PARTIDO:
    {contexto_eventos}

    INSTRUCCIONES:
    1. Escribe una {instrucciones['estilo']} sin limites de texto.
    2. Usa estilo narrativo (introducción, desarrollo, conclusión)
    3. Menciona los momentos clave del partido
    4. NO inventes datos, usa SOLO los eventos proporcionados
    5. Usa lenguaje profesional pero accesible
    6. NO uses emojis
    7. Escribe en {instrucciones['idioma']}

    CRÓNICA:"""

        # ========================================================================
        # GENERAR
        # ========================================================================
        
        if stream:
            return self._generar_con_streaming(
                prompt, 
                equipo_local, 
                equipo_visitante, 
                jornada, 
                len(eventos),
                idioma  # ← Pasar idioma al streaming
            )
        
        else:
            response = self.ollama_client.generate(
                model=OLLAMA_MODEL,
                prompt=prompt,
                options={
                    "temperature": 0.7,
                    "num_predict": MAX_TOKENS_DAFO
                }
            )
            
            resumen = response['response'].strip()
            
            if verbose:
                logger.info(f"✅ Resumen generado ({len(resumen)} caracteres)")
            
            return {
                'resumen': resumen,
                'equipo_local': equipo_local,
                'equipo_visitante': equipo_visitante,
                'jornada': jornada,
                'num_eventos': len(eventos),
                'tokens_generados': response.get('eval_count', 'N/A'),
                'idioma': idioma
            }


    def _generar_con_streaming(self, prompt, equipo_local, equipo_visitante, jornada, num_eventos, idioma='es'):
        """
        Generador que yield tokens en streaming
        """
        
        import time
        
        # Metadata inicial
        yield {
            'type': 'metadata',
            'equipo_local': equipo_local,
            'equipo_visitante': equipo_visitante,
            'jornada': jornada,
            'num_eventos': num_eventos,
            'idioma': idioma
        }
        
        # Generar con streaming
        stream_response = self.ollama_client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            stream=True,
            options={
                "temperature": 0.7,
                "num_predict": MAX_TOKENS_RESUMEN
            }
        )
        
        resumen_completo = ""
        tokens_count = 0
        
        # Tracking de tiempo
        tiempo_inicio = time.time()
        tiempo_primer_token = None
        
        # Yield cada token
        for chunk in stream_response:
            if chunk.get('response'):
                token = chunk['response']
                resumen_completo += token
                tokens_count += 1
                
                # Registrar tiempo del primer token
                if tiempo_primer_token is None:
                    tiempo_primer_token = time.time()
                    logger.debug(f"Primer token después de {tiempo_primer_token - tiempo_inicio:.3f}s")
                
                # Calcular tokens/segundo
                tiempo_transcurrido = time.time() - tiempo_primer_token
                
                # ← FIX: Asegurar que hay tiempo transcurrido
                if tiempo_transcurrido < 0.001:
                    # Muy al inicio, usar valor estimado
                    tokens_por_segundo = 0.0
                else:
                    tokens_por_segundo = tokens_count / tiempo_transcurrido
                
                # ← FIX: Solo después de ciertos tokens para tener medida estable
                if tokens_count >= 5:
                    tok_s_display = round(tokens_por_segundo, 1)
                else:
                    tok_s_display = 0.0  # Muy pronto para medir
                
                yield {
                    'type': 'token',
                    'token': token,
                    'resumen_parcial': resumen_completo,
                    'tokens_generados': tokens_count,
                    'tokens_por_segundo': tok_s_display,  # ← FIX
                    'tiempo_transcurrido': round(tiempo_transcurrido, 2)
                }
        
        # Metadata final
        tiempo_total = time.time() - tiempo_inicio
        
        if tiempo_primer_token:
            tiempo_generacion = time.time() - tiempo_primer_token
            tokens_por_segundo_final = tokens_count / max(tiempo_generacion, 0.001)
        else:
            tiempo_generacion = tiempo_total
            tokens_por_segundo_final = 0.0
        
        yield {
            'type': 'final',
            'resumen': resumen_completo,
            'tokens_generados': tokens_count,
            'idioma': idioma,
            'tokens_por_segundo': round(tokens_por_segundo_final, 1),
            'tiempo_total': round(tiempo_total, 2),
            'tiempo_generacion': round(tiempo_generacion, 2)
        }

    # ========================================================================
    # NLP-10: ANÁLISIS DAFO
    # ========================================================================

    def analizar_dafo_equipo(
        self,
        match_id: int,
        equipo: str,
        eventos: List[Dict] = None,
        verbose: bool = True,
        stream: bool = False  # ← NUEVO
    ) -> Dict:
        """
        Genera análisis DAFO de un equipo en un partido.
        
        Args:
            match_id: ID del partido
            equipo: Nombre del equipo ('Local' o 'Visitante')
            eventos: Lista de eventos (si None, los carga)
            verbose: Mostrar logs
            stream: Si True, retorna generador para streaming
        """
        if verbose:
            logger.info(f"🔍 Analizando DAFO del equipo {equipo} (match {match_id})...")
        
        try:
            # Cargar eventos si no se proporcionaron
            if eventos is None:
                if self.rag_client:
                    try:
                        eventos = self.rag_client.get_match_events(match_id)
                        if verbose:
                            logger.info(f"✅ Eventos cargados desde RAG: {len(eventos)}")
                    except Exception as e:
                        if verbose:
                            logger.warning(f"⚠️  Error con RAG, usando MinIO: {e}")
                        eventos = self._load_eventos_from_minio(match_id)
                else:
                    eventos = self._load_eventos_from_minio(match_id)
            
            if not eventos:
                return {
                    'match_id': match_id,
                    'equipo': equipo,
                    'error': 'No se encontraron eventos'
                }
            
            # Filtrar eventos del equipo
            eventos_equipo = [e for e in eventos if e.get('equipo') == equipo]
            
            if not eventos_equipo:
                return {
                    'match_id': match_id,
                    'equipo': equipo,
                    'error': f'No hay eventos del equipo {equipo}'
                }
            
            # Formatear eventos
            eventos_texto = self._format_eventos_para_dafo(eventos_equipo, eventos)
            
            # Generar prompt
            prompt = ANALISIS_DAFO_TEMPLATE.format(
                eventos=eventos_texto,
                equipo=equipo
            )
            
            # ====================================================================
            # GENERAR CON O SIN STREAMING
            # ====================================================================
            
            if stream:
                # Modo streaming
                return self._generar_dafo_con_streaming(
                    prompt,
                    match_id,
                    equipo,
                    len(eventos_equipo),
                    verbose
                )
            
            else:
                # Modo normal (código existente)
                if verbose:
                    logger.info(f"🤖 Generando análisis DAFO...")
                
                response = self.ollama_client.generate(
                    model=OLLAMA_MODEL,
                    prompt=prompt,
                    options={
                        'temperature': OLLAMA_TEMPERATURE,
                        'num_predict': MAX_TOKENS_DAFO
                    }
                )
                
                # Parsear respuesta JSON
                respuesta_texto = response['response'].strip()
                
                # Limpiar markdown si existe
                if '```json' in respuesta_texto:
                    respuesta_texto = respuesta_texto.split('```json')[1].split('```')[0].strip()
                elif '```' in respuesta_texto:
                    respuesta_texto = respuesta_texto.split('```')[1].split('```')[0].strip()
                
                dafo = json.loads(respuesta_texto)
                
                if verbose:
                    logger.info(f"✅ Análisis DAFO completado")
                
                return {
                    'match_id': match_id,
                    'equipo': equipo,
                    'dafo': dafo,
                    'num_eventos_analizados': len(eventos_equipo)
                }
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON del DAFO: {e}")
            return {
                'match_id': match_id,
                'equipo': equipo,
                'error': f'Error parseando respuesta: {e}',
                'respuesta_raw': respuesta_texto
            }
        except Exception as e:
            logger.error(f"❌ Error en análisis DAFO: {e}")
            return {
                'match_id': match_id,
                'equipo': equipo,
                'error': str(e)
            }

    def analizar_dafo_partido_completo(
        self,
        match_id: int,
        verbose: bool = True
    ) -> Dict:
        """
        Genera análisis DAFO para ambos equipos.
        
        Args:
            match_id: ID del partido
            verbose: Mostrar logs
            
        Returns:
            Dict con DAFO de local y visitante
        """
        logger.info(f"🔍 Análisis DAFO completo del match {match_id}...")
        
        # Cargar eventos una vez
        eventos = self._load_eventos_from_minio(match_id)
        
        # DAFO Local
        dafo_local = self.analizar_dafo_equipo(
            match_id=match_id,
            equipo='Local',
            eventos=eventos,
            verbose=verbose
        )
        
        # DAFO Visitante
        dafo_visitante = self.analizar_dafo_equipo(
            match_id=match_id,
            equipo='Visitante',
            eventos=eventos,
            verbose=verbose
        )
        
        return {
            'match_id': match_id,
            'local': dafo_local,
            'visitante': dafo_visitante
        }
    
    def listar_partidos_disponibles(self) -> List[int]:
        """Lista todos los match_ids disponibles en PLATA"""
        try:
            # Leer consolidado
            response = self.storage.s3.get_object(
                Bucket=BUCKET_PLATA,
                Key='eventos/2025-2026/eventos_consolidado.json'
            )
            
            eventos = json.loads(response['Body'].read().decode('utf-8'))
            
            # Extraer match_ids únicos
            match_ids = sorted(list(set(e.get('match_id') for e in eventos if e.get('match_id'))))
            
            logger.info(f"✅ {len(match_ids)} partidos disponibles")
            return match_ids
            
        except Exception as e:
            logger.error(f"❌ Error listando partidos: {e}")
            return []

    def _generar_dafo_con_streaming(self, prompt, match_id, equipo, num_eventos, verbose):
        """
        Generador que yield tokens para DAFO en streaming
        """
        
        # Metadata inicial
        yield {
            'type': 'metadata',
            'match_id': match_id,
            'equipo': equipo,
            'num_eventos': num_eventos
        }
        
        # Generar con streaming
        stream_response = self.ollama_client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            stream=True,
            options={
                'temperature': OLLAMA_TEMPERATURE,
                'num_predict': MAX_TOKENS_DAFO
            }
        )
        
        respuesta_completa = ""
        tokens_count = 0
        
        # Yield cada token
        for chunk in stream_response:
            if chunk.get('response'):
                token = chunk['response']
                respuesta_completa += token
                tokens_count += 1
                
                yield {
                    'type': 'token',
                    'token': token,
                    'respuesta_parcial': respuesta_completa,
                    'tokens_generados': tokens_count
                }
        
        # Parsear JSON final
        try:
            # Limpiar markdown
            respuesta_limpia = respuesta_completa.strip()
            if '```json' in respuesta_limpia:
                respuesta_limpia = respuesta_limpia.split('```json')[1].split('```')[0].strip()
            elif '```' in respuesta_limpia:
                respuesta_limpia = respuesta_limpia.split('```')[1].split('```')[0].strip()
            
            dafo = json.loads(respuesta_limpia)
            
            # Metadata final con DAFO parseado
            yield {
                'type': 'final',
                'match_id': match_id,
                'equipo': equipo,
                'dafo': dafo,
                'tokens_generados': tokens_count,
                'num_eventos_analizados': num_eventos
            }
        
        except json.JSONDecodeError as e:
            # Error parseando JSON
            yield {
                'type': 'error',
                'error': f'Error parseando JSON: {e}',
                'respuesta_raw': respuesta_completa
            }
    # ========================================================================
    # UTILIDADES PRIVADAS
    # ========================================================================
    
    # En _load_eventos_from_minio
    def _load_eventos_from_minio(self, match_id: int) -> List[Dict]:
        """Carga eventos desde MinIO PLATA"""
        try:
            # Leer archivo consolidado
            logger.info(f"📦 Cargando eventos del match {match_id}...")
            
            response = self.storage.s3.get_object(
                Bucket=BUCKET_PLATA,
                Key='eventos/2025-2026/eventos_consolidado.json'
            )
            
            eventos_todos = json.loads(response['Body'].read().decode('utf-8'))
            
            # Filtrar por match_id
            eventos_partido = [e for e in eventos_todos if e.get('match_id') == match_id]
            
            if eventos_partido:
                logger.info(f"✅ {len(eventos_partido)} eventos cargados")
                return eventos_partido
            
            logger.warning(f"⚠️  No se encontraron eventos para match {match_id}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error cargando eventos: {e}")
            return []

    def _load_eventos_from_minio_error(self, match_id: int) -> List[Dict]:
        """Carga eventos desde MinIO PLATA"""
        try:
            eventos_json = self.storage.leer_eventos_plata(
                match_id=match_id,
                formato='json'
            )
            
            if eventos_json:
                eventos = json.loads(eventos_json)
                logger.info(f"✅ {len(eventos)} eventos cargados desde PLATA")
                return eventos
            
            logger.warning(f"⚠️  No se encontraron eventos para match {match_id}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error cargando eventos: {e}")
            return []
    
    def _load_match_info_bad(self, match_id: int) -> Dict:
        """Carga información del partido desde PLATA"""
        try:
            # Intentar cargar desde equipos
            equipos_json = self.storage.leer_actas_plata(match_id=match_id)
            
            if equipos_json:
                return json.loads(equipos_json)
            
            return {}
            
        except Exception as e:
            logger.warning(f"⚠️  No se pudo cargar info del partido: {e}")
            return {}
    
    def _load_match_info(self, match_id: int) -> Dict:
        """
        Carga información del partido desde eventos consolidado.
        
        Args:
            match_id: ID del partido
            
        Returns:
            Dict con equipo_local, equipo_visitante, jornada, partido
        """
        try:
            logger.info(f"📋 Cargando info del match {match_id}...")
            
            # Cargar eventos consolidado (ya lo hace _load_eventos_from_minio)
            response = self.storage.s3.get_object(
                Bucket=BUCKET_PLATA,
                Key='eventos/2025-2026/eventos_consolidado.json'
            )
            
            eventos = json.loads(response['Body'].read().decode('utf-8'))
            
            # Filtrar eventos de este partido
            eventos_partido = [e for e in eventos if e.get('match_id') == match_id]
            
            if not eventos_partido:
                logger.warning(f"⚠️  No se encontraron eventos para match {match_id}")
                return {
                    'match_id': match_id,
                    'equipo_local': 'Equipo Local',
                    'equipo_visitante': 'Equipo Visitante',
                    'jornada': 0,
                    'partido': 0
                }
            
            # Primer evento tiene la metadata completa
            primer_evento = eventos_partido[0]
            jornada = primer_evento.get('jornada', 0)
            partido = primer_evento.get('partido', 0)
            
            # Intentar cargar nombres de equipos desde CSV
            try:
                import pandas as pd
                from io import BytesIO
                
                equipos_response = self.storage.s3.get_object(
                    Bucket=BUCKET_PLATA,
                    Key='equipos/2025-2026.csv'
                )
                
                df_equipos = pd.read_csv(BytesIO(equipos_response['Body'].read()))
                partido_info = df_equipos[df_equipos['match_id'] == match_id]
                
                if not partido_info.empty:
                    equipo_local = partido_info.iloc[0]['equipo_local']
                    equipo_visitante = partido_info.iloc[0]['equipo_visitante']
                else:
                    equipo_local = 'Equipo Local'
                    equipo_visitante = 'Equipo Visitante'
            
            except Exception as e:
                logger.debug(f"Nombres de equipos no disponibles: {e}")
                equipo_local = 'Equipo Local'
                equipo_visitante = 'Equipo Visitante'
            
            info = {
                'match_id': match_id,
                'equipo_local': equipo_local,
                'equipo_visitante': equipo_visitante,
                'jornada': jornada,
                'partido': partido
            }
            
            logger.info(f"✅ {equipo_local} vs {equipo_visitante} (J{jornada}-P{partido})")
            return info
            
        except Exception as e:
            logger.error(f"❌ Error cargando info: {e}")
            return {
                'match_id': match_id,
                'equipo_local': 'Equipo Local',
                'equipo_visitante': 'Equipo Visitante',
                'jornada': 0,
                'partido': 0
            }

# ========================================================================
# MÉTODO DE TRADUCCIÓN
# ========================================================================

    def _traducir_texto(self, texto: str, idioma_destino: str = 'en') -> str:
        """
        Traduce un texto al idioma destino usando Qwen2.5
        
        Args:
            texto: Texto a traducir
            idioma_destino: Código ISO del idioma ('en', 'es', 'pt', 'de', 'fr')
        
        Returns:
            str: Texto traducido
        """
        
        # Mapeo de códigos a nombres de idiomas
        NOMBRES_IDIOMAS = {
            'en': 'English',
            'es': 'español',
            'pt': 'português',
            'de': 'Deutsch',
            'fr': 'français',
            'lb': 'Lëtzebuergesch'
        }
        
        nombre_idioma = NOMBRES_IDIOMAS.get(idioma_destino, idioma_destino)
        
        prompt = f"""Translate the following text to {nombre_idioma}.
    Only return the translation, no explanations.

    Text: {texto}

    Translation:"""
        
        try:
            response = self.ollama_client.generate(
                model=OLLAMA_MODEL,
                prompt=prompt,
                options={
                    "temperature": 0.3,  # Baja temperatura para traducción precisa
                    "num_predict": 200
                }
            )
            
            traduccion = response['response'].strip()
            
            # Limpiar si viene con comillas o prefijos
            if traduccion.startswith('"') and traduccion.endswith('"'):
                traduccion = traduccion[1:-1]
            
            return traduccion
            
        except Exception as e:
            logger.warning(f"⚠️ Error traduciendo: {e}, usando texto original")
            return texto  # Fallback: devolver original

    def _format_eventos_para_resumen(self, eventos: List[Dict]) -> str:
        """Formatea eventos para prompt de resumen"""
        # Ordenar por minuto
        eventos_sorted = sorted(eventos, key=lambda x: x.get('minuto_exacto', 0))
        
        texto = []
        for evento in eventos_sorted:
            minuto = evento.get('minuto', '0')
            equipo = evento.get('equipo', 'Desconocido')
            texto_evento = evento.get('texto_es', evento.get('texto', ''))
            
            texto.append(f"Min {minuto} ({equipo}): {texto_evento}")
        
        return '\n'.join(texto)
    
    def _format_eventos_para_dafo(
        self,
        eventos_equipo: List[Dict],
        eventos_todos: List[Dict]
    ) -> str:
        """Formatea eventos para análisis DAFO"""
        # Ordenar por minuto
        eventos_sorted = sorted(eventos_equipo, key=lambda x: x.get('minuto_exacto', 0))
        
        texto = []
        texto.append("EVENTOS DEL EQUIPO:")
        for evento in eventos_sorted:
            minuto = evento.get('minuto', '0')
            texto_evento = evento.get('texto_es', evento.get('texto', ''))
            texto.append(f"  Min {minuto}: {texto_evento}")
        
        # Incluir algunos eventos del rival (contexto)
        equipo_analizado = eventos_equipo[0].get('equipo') if eventos_equipo else 'Local'
        equipo_rival = 'Visitante' if equipo_analizado == 'Local' else 'Local'
        
        eventos_rival = [e for e in eventos_todos if e.get('equipo') == equipo_rival]
        eventos_rival_sorted = sorted(eventos_rival, key=lambda x: x.get('minuto_exacto', 0))[:5]
        
        if eventos_rival_sorted:
            texto.append("\nEVENTOS CLAVE DEL RIVAL (contexto):")
            for evento in eventos_rival_sorted:
                minuto = evento.get('minuto', '0')
                texto_evento = evento.get('texto_es', evento.get('texto', ''))
                texto.append(f"  Min {minuto}: {texto_evento}")
        
        return '\n'.join(texto)


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

def create_nlp_analyzer(config: NLPConfig = None, rag_client=None) -> NLPAnalyzer:
    """
    Crea un analizador NLP con configuración por defecto.
    
    Args:
        config: Configuración personalizada (opcional)
        rag_client: Cliente RAG (opcional, se crea uno si no se proporciona)
        
    Returns:
        NLPAnalyzer inicializado
    """
    return NLPAnalyzer(config, rag_client)

# ============================================================================
# MAIN (Testing)
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TEST NLP ANALYZER")
    print("=" * 80)
    
    # Crear analizador
    try:
        analyzer = create_nlp_analyzer()
        
        # Listar partidos disponibles
        print("\n📋 Listando partidos disponibles...")
        partidos = analyzer.listar_partidos_disponibles()
        
        if not partidos:
            print("❌ No hay partidos en PLATA")
            print("💡 Ejecuta primero: python etl_pipeline.py")
            exit(1)
        
        print(f"✅ {len(partidos)} partidos encontrados")
        print(f"   Rango: {partidos[0]} - {partidos[-1]}")
        
        # Usar el primer partido disponible
        test_match_id =  10891 #partidos[0] # 10891
        
        print(f"\n📋 Analizando match {test_match_id}...")
        
        # Test 1: Resumen narrativo
        #print("\n" + "=" * 80)
        #print("📝 TEST: RESUMEN NARRATIVO (NLP-30)")
        #print("=" * 80)
        
        #resumen = analyzer.generar_resumen_partido(test_match_id)
        
        #if 'error' in resumen:
        #    print(f"❌ Error: {resumen['error']}")
        #else:
        #    print(f"\n🏟️  {resumen['equipo_local']} vs {resumen['equipo_visitante']}")
        #    print(f"📅 Jornada {resumen['jornada']}")
        #    print(f"📊 Eventos analizados: {resumen['num_eventos']}")
        #    print(f"\n📰 RESUMEN:")
        #    print("-" * 80)
        #    print(resumen['resumen'])


        # ============================================================================
        # TEST 2: ANÁLISIS DAFO (NLP-10)
        # ============================================================================

        print("\n" + "=" * 80)
        print("🔍 TEST: ANÁLISIS DAFO (NLP-10)")
        print("=" * 80)

        # Cargar eventos una vez
        print("\n📦 Cargando eventos desde RAG...")
        eventos = analyzer.rag_client.get_match_events(test_match_id) if analyzer.rag_client else []

        if not eventos:
            print("⚠️  Cargando desde MinIO como fallback...")
            eventos = analyzer._load_eventos_from_minio(test_match_id)

        if not eventos:
            print("❌ No se encontraron eventos para análisis DAFO")
        else:
            print(f"✅ {len(eventos)} eventos cargados")
            
            # Cargar info del partido
            match_info = analyzer._load_match_info(test_match_id)
            equipo_local = match_info.get('equipo_local', 'Equipo Local')
            equipo_visitante = match_info.get('equipo_visitante', 'Equipo Visitante')
            
            print(f"\n🏟️  {equipo_local} vs {equipo_visitante}")
            print(f"📅 Jornada {match_info.get('jornada', 'N/A')}")
            
            # ========================================================================
            # MODO NORMAL (SIN STREAMING) - EQUIPO LOCAL
            # ========================================================================
            
            print("\n" + "=" * 80)
            print(f"📊 DAFO MODO NORMAL - {equipo_local.upper()}")
            print("=" * 80)
            
            dafo_data = analyzer.analizar_dafo_equipo(
                match_id=test_match_id,
                equipo='Local',
                eventos=eventos,
                verbose=True,
                stream=False  # ← Sin streaming
            )
            
            if 'error' not in dafo_data:
                dafo = dafo_data['dafo']
                
                print(f"\n💪 FORTALEZAS:")
                for i, f in enumerate(dafo.get('fortalezas', []), 1):
                    print(f"   {i}. {f}")
                
                print(f"\n⚠️  DEBILIDADES:")
                for i, d in enumerate(dafo.get('debilidades', []), 1):
                    print(f"   {i}. {d}")
                
                print(f"\n🎯 OPORTUNIDADES:")
                for i, o in enumerate(dafo.get('oportunidades', []), 1):
                    print(f"   {i}. {o}")
                
                print(f"\n🚨 AMENAZAS:")
                for i, a in enumerate(dafo.get('amenazas', []), 1):
                    print(f"   {i}. {a}")
            
            # ========================================================================
            # MODO STREAMING - EQUIPO VISITANTE
            # ========================================================================
            
            print("\n" + "=" * 80)
            print(f"🌊 DAFO MODO STREAMING - {equipo_visitante.upper()}")
            print("=" * 80)
            
            stream_gen = analyzer.analizar_dafo_equipo(
                match_id=test_match_id,
                equipo='Visitante',
                eventos=eventos,
                verbose=False,
                stream=True  # ← Con streaming
            )
            
            respuesta_completa = ""
            dafo_final = None
            
            for chunk in stream_gen:
                if chunk['type'] == 'metadata':
                    print(f"\n🔍 Analizando equipo: {chunk['equipo']}")
                    print(f"📈 Eventos a analizar: {chunk['num_eventos']}")
                    print(f"\n🤖 Generando análisis DAFO en tiempo real...\n")
                    print("-" * 80)
                
                elif chunk['type'] == 'token':
                    # Mostrar token en tiempo real
                    print(chunk['token'], end='', flush=True)
                    respuesta_completa = chunk['respuesta_parcial']
                
                elif chunk['type'] == 'final':
                    print("\n" + "-" * 80)
                    print(f"\n✅ Análisis completado!")
                    print(f"📊 Tokens generados: {chunk['tokens_generados']}")
                    
                    dafo_final = chunk['dafo']
                    
                    # Mostrar DAFO parseado
                    print("\n" + "=" * 80)
                    print("📋 DAFO ESTRUCTURADO:")
                    print("=" * 80)
                    
                    print(f"\n💪 FORTALEZAS:")
                    for i, f in enumerate(dafo_final.get('fortalezas', []), 1):
                        print(f"   {i}. {f}")
                    
                    print(f"\n⚠️  DEBILIDADES:")
                    for i, d in enumerate(dafo_final.get('debilidades', []), 1):
                        print(f"   {i}. {d}")
                    
                    print(f"\n🎯 OPORTUNIDADES:")
                    for i, o in enumerate(dafo_final.get('oportunidades', []), 1):
                        print(f"   {i}. {o}")
                    
                    print(f"\n🚨 AMENAZAS:")
                    for i, a in enumerate(dafo_final.get('amenazas', []), 1):
                        print(f"   {i}. {a}")
                    
                    # Estadísticas
                    total_puntos = (
                        len(dafo_final.get('fortalezas', [])) +
                        len(dafo_final.get('debilidades', [])) +
                        len(dafo_final.get('oportunidades', [])) +
                        len(dafo_final.get('amenazas', []))
                    )
                    
                    print("\n" + "-" * 80)
                    print(f"📊 Total puntos identificados: {total_puntos}")
                
                elif chunk['type'] == 'error':
                    print(f"\n❌ Error: {chunk['error']}")
                    print(f"\n🔍 Respuesta raw:")
                    print(chunk['respuesta_raw'])

        print("\n" + "=" * 80)
        print("✅ Test DAFO completado")
        print("=" * 80)



        # ============================================================================
        # TEST 1: RESUMEN NARRATIVO (NLP-30)
        # ============================================================================

        print("\n" + "=" * 80)
        print("📝 TEST: RESUMEN NARRATIVO (NLP-30)")
        print("=" * 80)

        # Primero probar modo normal (sin streaming)
        print("\n🔹 Modo Normal (sin streaming):")
        print("-" * 80)

        resumen = analyzer.generar_resumen_partido(test_match_id, stream=False, verbose=True)

        if 'error' in resumen:
            print(f"❌ Error: {resumen['error']}")
        else:
            print(f"\n🏟️  {resumen['equipo_local']} vs {resumen['equipo_visitante']}")
            print(f"📅 Jornada {resumen['jornada']}")
            print(f"📊 Eventos analizados: {resumen['num_eventos']}")
            print(f"🔢 Tokens generados: {resumen.get('tokens_generados', 'N/A')}")
            print(f"\n📰 RESUMEN:")
            print("-" * 80)
            print(resumen['resumen'])
            print("-" * 80)
            palabras = len(resumen['resumen'].split())
            print(f"📊 Longitud: {palabras} palabras, {len(resumen['resumen'])} caracteres")

        # ============================================================================
        # TEST 1B: RESUMEN CON STREAMING
        # ============================================================================

        print("\n" + "=" * 80)
        print("🌊 TEST: RESUMEN CON STREAMING")
        print("=" * 80)

        print("\n🔹 Modo Streaming (palabra por palabra):")
        print("-" * 80)

        stream_gen = analyzer.generar_resumen_partido(test_match_id, stream=True, verbose=False)

        resumen_completo = ""
        tokens_count = 0
        palabras_count = 0

        for chunk in stream_gen:
            if chunk['type'] == 'metadata':
                print(f"\n🏟️  {chunk['equipo_local']} vs {chunk['equipo_visitante']}")
                print(f"📅 Jornada {chunk['jornada']} | Eventos: {chunk['num_eventos']}")
                print(f"\n📝 Generando resumen en tiempo real...\n")
                print("-" * 80)
            
            elif chunk['type'] == 'token':
                # Imprimir token en tiempo real (palabra por palabra)
                print(chunk['token'], end='', flush=True)
                
                resumen_completo = chunk['resumen_parcial']
                tokens_count = chunk['tokens_generados']
                
                # Contar palabras (aproximado)
                palabras_count = len(resumen_completo.split())
            
            elif chunk['type'] == 'final':
                print("\n" + "-" * 80)
                print(f"\n✅ Resumen completado!")
                print(f"📊 Estadísticas:")
                print(f"   • Tokens generados: {tokens_count}")
                print(f"   • Palabras: {len(chunk['resumen'].split())}")
                print(f"   • Caracteres: {len(chunk['resumen'])}")

        # ============================================================================
        # COMPARACIÓN
        # ============================================================================

        print("\n" + "=" * 80)
        print("🔄 COMPARACIÓN: Normal vs Streaming")
        print("=" * 80)

        import time

        # Test velocidad modo normal
        print("\n⏱️  Test velocidad modo NORMAL:")
        start = time.time()
        resumen_normal = analyzer.generar_resumen_partido(test_match_id, stream=False, verbose=False)
        tiempo_normal = time.time() - start
        print(f"   Tiempo total: {tiempo_normal:.2f}s")
        print(f"   Percepción: Usuario espera {tiempo_normal:.2f}s antes de ver algo")

        # Test velocidad modo streaming
        print("\n⏱️  Test velocidad modo STREAMING:")
        start = time.time()
        stream_gen = analyzer.generar_resumen_partido(test_match_id, stream=True, verbose=False)

        tiempo_primer_token = None
        for i, chunk in enumerate(stream_gen):
            if chunk['type'] == 'token' and tiempo_primer_token is None:
                tiempo_primer_token = time.time() - start
                break

        tiempo_streaming = time.time() - start
        print(f"   Tiempo primer token: {tiempo_primer_token:.2f}s")
        print(f"   Tiempo total: {tiempo_streaming:.2f}s")
        print(f"   Percepción: Usuario ve progreso desde {tiempo_primer_token:.2f}s")

        print(f"\n💡 Mejora percibida: {((tiempo_normal - tiempo_primer_token) / tiempo_normal * 100):.1f}%")


        # Test 2: Análisis DAFO
        print("\n" + "=" * 80)
        print("🔍 TEST: ANÁLISIS DAFO (NLP-10)")
        print("=" * 80)

        # Cargar eventos una vez desde RAG (más eficiente)
        print("\n📦 Cargando eventos desde RAG...")
        eventos = analyzer.rag_client.get_match_events(test_match_id) if analyzer.rag_client else []

        if not eventos:
            print("⚠️  Cargando desde MinIO como fallback...")
            eventos = analyzer._load_eventos_from_minio(test_match_id)

        if not eventos:
            print("❌ No se encontraron eventos para análisis DAFO")
        else:
            print(f"✅ {len(eventos)} eventos cargados")
            
            # Cargar info del partido
            match_info = analyzer._load_match_info(test_match_id)
            equipo_local = match_info.get('equipo_local', 'Equipo Local')
            equipo_visitante = match_info.get('equipo_visitante', 'Equipo Visitante')
            
            print(f"\n🏟️  {equipo_local} vs {equipo_visitante}")
            print(f"📅 Jornada {match_info.get('jornada', 'N/A')}")
            
            # Analizar DAFO para ambos equipos
            for equipo_tipo, equipo_nombre in [('Local', equipo_local), ('Visitante', equipo_visitante)]:
                print("\n" + "=" * 80)
                print(f"📊 ANÁLISIS DAFO - {equipo_nombre.upper()}")
                print("=" * 80)
                
                dafo_data = analyzer.analizar_dafo_equipo(
                    match_id=test_match_id,
                    equipo=equipo_tipo,
                    eventos=eventos,  # Pasar eventos ya cargados
                    verbose=True
                )
                
                if 'error' in dafo_data:
                    print(f"\n❌ Error en DAFO: {dafo_data['error']}")
                    
                    if 'respuesta_raw' in dafo_data:
                        print("\n🔍 Respuesta raw del LLM:")
                        print("-" * 80)
                        print(dafo_data['respuesta_raw'])
                    
                    continue
                
                dafo = dafo_data['dafo']
                num_eventos = dafo_data.get('num_eventos_analizados', 0)
                
                print(f"\n📈 Eventos analizados del {equipo_tipo}: {num_eventos}")
                print("-" * 80)
                
                # FORTALEZAS
                print(f"\n💪 FORTALEZAS:")
                fortalezas = dafo.get('fortalezas', [])
                if fortalezas:
                    for i, f in enumerate(fortalezas, 1):
                        print(f"   {i}. {f}")
                else:
                    print("   (No detectadas)")
                
                # DEBILIDADES
                print(f"\n⚠️  DEBILIDADES:")
                debilidades = dafo.get('debilidades', [])
                if debilidades:
                    for i, d in enumerate(debilidades, 1):
                        print(f"   {i}. {d}")
                else:
                    print("   (No detectadas)")
                
                # OPORTUNIDADES
                print(f"\n🎯 OPORTUNIDADES:")
                oportunidades = dafo.get('oportunidades', [])
                if oportunidades:
                    for i, o in enumerate(oportunidades, 1):
                        print(f"   {i}. {o}")
                else:
                    print("   (No detectadas)")
                
                # AMENAZAS
                print(f"\n🚨 AMENAZAS:")
                amenazas = dafo.get('amenazas', [])
                if amenazas:
                    for i, a in enumerate(amenazas, 1):
                        print(f"   {i}. {a}")
                else:
                    print("   (No detectadas)")
                
                # Resumen del análisis
                print("\n" + "-" * 80)
                total_puntos = len(fortalezas) + len(debilidades) + len(oportunidades) + len(amenazas)
                print(f"📊 Total puntos identificados: {total_puntos}")
                print(f"   💪 Fortalezas: {len(fortalezas)}")
                print(f"   ⚠️  Debilidades: {len(debilidades)}")
                print(f"   🎯 Oportunidades: {len(oportunidades)}")
                print(f"   🚨 Amenazas: {len(amenazas)}")

        print("\n" + "=" * 80)
        print("✅ Test completado exitosamente")
        print("=" * 80)

        # Test 1b: STREAMING
        print("\n" + "=" * 80)
        print("🌊 TEST: RESUMEN NARRATIVO CON STREAMING (NLP-30)")
        print("=" * 80)

        stream_gen = analyzer.generar_resumen_partido(test_match_id, stream=True, verbose=False)

        resumen_completo = ""
        tokens_count = 0

        for chunk in stream_gen:
            if chunk['type'] == 'metadata':
                print(f"\n🏟️  {chunk['equipo_local']} vs {chunk['equipo_visitante']}")
                print(f"📅 Jornada {chunk['jornada']} | Eventos: {chunk['num_eventos']}")
                print("\n📝 Resumen:\n")
            
            elif chunk['type'] == 'token':
                # Imprimir token en tiempo real
                print(chunk['token'], end='', flush=True)
                resumen_completo = chunk['resumen_parcial']
                tokens_count = chunk['tokens_generados']
            
            elif chunk['type'] == 'final':
                print(f"\n\n✅ Completado!")
                print(f"📊 Total: {len(chunk['resumen'].split())} palabras, {tokens_count} tokens")

        # Test 2: Análisis DAFO
        print("\n" + "=" * 80)
        print("🔍 TEST: ANÁLISIS DAFO (NLP-10)")
        print("=" * 80)
        
        dafo_completo = analyzer.analizar_dafo_partido_completo(test_match_id)
        
        for equipo_tipo in ['local', 'visitante']:
            dafo_data = dafo_completo[equipo_tipo]
            
            if 'error' in dafo_data:
                print(f"\n❌ Error en DAFO {equipo_tipo}: {dafo_data['error']}")
                continue
            
            print(f"\n📊 DAFO - Equipo {equipo_tipo.upper()}:")
            print("-" * 80)
            
            dafo = dafo_data['dafo']
            
            print(f"\n💪 FORTALEZAS:")
            for f in dafo.get('fortalezas', []):
                print(f"   • {f}")
            
            print(f"\n⚠️  DEBILIDADES:")
            for d in dafo.get('debilidades', []):
                print(f"   • {d}")
            
            print(f"\n🎯 OPORTUNIDADES:")
            for o in dafo.get('oportunidades', []):
                print(f"   • {o}")
            
            print(f"\n🚨 AMENAZAS:")
            for a in dafo.get('amenazas', []):
                print(f"   • {a}")
        
        print("\n" + "=" * 80)
        print("✅ Test completado")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()