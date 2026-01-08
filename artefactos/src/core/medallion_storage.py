"""
medallion_storage.py
====================

Módulo para gestionar almacenamiento en arquitectura Medallion (Bronce/Plata/Oro)
usando MinIO compatible con S3.

Autor: Pedro José García Fernández
Fecha: 26 Octubre 2024
Proyecto: Cl@ud-ia-data TFG
"""

import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional, List, Dict, BinaryIO
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


try:
    from core.config import *
except ImportError as e:
    from config import *


class MedallionStorage:
    """
    Cliente para gestionar almacenamiento Medallion en MinIO.
    
    Arquitectura:
    - BRONCE: Datos raw (HTML, PDF, videos originales)
    - PLATA: Datos procesados (CSV, JSON estructurado)
    - ORO: Datos analytics-ready (embeddings, agregados)
    """
    
    def __init__(
        self,
        endpoint_url: str = MINIO_ENDPOINT,
        access_key: str = MINIO_ACCESS_KEY,
        secret_key: str = MINIO_SECRET_KEY
    ):
        """
        Inicializa el cliente MinIO.
        
        Args:
            endpoint_url: URL del servidor MinIO
            access_key: Access key
            secret_key: Secret key
        """
        self.endpoint_url = endpoint_url
        self.s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        logger.info(f"Cliente MinIO inicializado: {endpoint_url}")
    
    # ================================================
    # VERIFICACIÓN Y UTILIDADES
    # ================================================
    
    def verificar_estructura(self) -> Dict[str, bool]:
        """
        Verifica que existan los buckets de la arquitectura Medallion.
        
        Returns:
            Dict con status de cada bucket
        """
        buckets_requeridos = [
            BUCKET_BRONCE,
            BUCKET_PLATA,
            BUCKET_ORO
        ]
        
        try:
            response = self.s3.list_buckets()
            buckets_existentes = [b['Name'] for b in response['Buckets']]
            
            status = {}
            for bucket in buckets_requeridos:
                existe = bucket in buckets_existentes
                status[bucket] = existe
                logger.info(f"Bucket '{bucket}': {'✅ existe' if existe else '❌ no existe'}")
            
            return status
            
        except ClientError as e:
            logger.error(f"Error verificando buckets: {e}")
            return {b: False for b in buckets_requeridos}
    
    def crear_estructura(self) -> bool:
        """
        Crea los buckets de la arquitectura Medallion si no existen.
        
        Returns:
            True si éxito, False si error
        """
        buckets = [BUCKET_BRONCE, BUCKET_PLATA, BUCKET_ORO]
        
        try:
            for bucket in buckets:
                try:
                    self.s3.create_bucket(Bucket=bucket)
                    logger.info(f"✅ Bucket '{bucket}' creado")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                        logger.info(f"ℹ️  Bucket '{bucket}' ya existe")
                    else:
                        raise
            return True
            
        except ClientError as e:
            logger.error(f"❌ Error creando buckets: {e}")
            return False
    
    def listar_archivos(
        self,
        bucket: str,
        prefix: str = "",
        max_items: int = 100
    ) -> List[Dict]:
        """
        Lista archivos en un bucket/prefix.
        
        Args:
            bucket: Nombre del bucket
            prefix: Prefijo (carpeta)
            max_items: Máximo de items a retornar
            
        Returns:
            Lista de dicts con info de archivos
        """
        try:
            response = self.s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_items
            )
            
            archivos = []
            for obj in response.get('Contents', []):
                archivos.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'size_mb': round(obj['Size'] / (1024 * 1024), 2)
                })
            
            logger.info(f"📁 {len(archivos)} archivos en {bucket}/{prefix}")
            return archivos
            
        except ClientError as e:
            logger.error(f"❌ Error listando archivos: {e}")
            return []
    
    # ================================================
    # CAPA BRONCE (RAW DATA)
    # ================================================
    
    def subir_html_bronce(
        self,
        local_file: Path,
        match_id: int,
        temporada: str = "2025-2026"
    ) -> bool:
        """
        Sube HTML raw a BRONCE.
        
        Args:
            local_file: Archivo local
            match_id: ID del partido
            temporada: Temporada (ej: "2025-2026")
            
        Returns:
            True si éxito
        """
        s3_key = f"{BRONCE_HTML}/{temporada}/match_{match_id}.html"
        return self._subir_archivo(local_file, BUCKET_BRONCE, s3_key)
    
    def subir_pdf_bronce(
        self,
        local_file: Path,
        match_id: int,
        temporada: str = "2025-2026"
    ) -> bool:
        """
        Sube PDF raw a BRONCE.
        
        Args:
            local_file: Archivo local
            match_id: ID del partido
            temporada: Temporada
            
        Returns:
            True si éxito
        """
        s3_key = f"{BRONCE_PDF}/{temporada}/feuille_de_match_{match_id}.pdf"
        return self._subir_archivo(local_file, BUCKET_BRONCE, s3_key)
    
    def subir_video_bronce(
        self,
        local_file: Path,
        jornada: int,
        partido: int,
        temporada: str = "2025-2026"
    ) -> bool:
        """
        Sube video a BRONCE.
        
        Args:
            local_file: Archivo local
            jornada: Número de jornada
            partido: Número de partido
            temporada: Temporada
            
        Returns:
            True si éxito
        """
        s3_key = f"{BRONCE_VIDEO}/{temporada}/jornada_{jornada}/partido_{partido}.mp4"
        return self._subir_archivo(local_file, BUCKET_BRONCE, s3_key)
    
    def leer_html_bronce(
        self,
        match_id: int,
        temporada: str = "2025-2026"
    ) -> Optional[str]:
        """
        Lee HTML desde BRONCE calculando jornada/partido desde match_id.
        
        Args:
            match_id: ID del partido (ej: 10890 = jornada 1, partido 1)
            temporada: Temporada
            
        Returns:
            Contenido del HTML o None
            
        Example:
            >>> storage.leer_html_bronce(match_id=10890)
            >>> # Calcula: jornada=1, partido=1
            >>> # Lee: bronce/html/2025-2026/jornada_1_partido_1.html
        """
        # Calcular jornada y partido desde match_id
        # match_id inicial = 10890 → jornada 1, partido 1
        MATCH_ID_INICIAL = 10890
        offset = match_id - MATCH_ID_INICIAL
        
        # Cada jornada tiene 8 partidos
        jornada = (offset // 8) + 1
        partido = (offset % 8) + 1
        
        # Construir ruta
        s3_key = f"{BRONCE_HTML}/{temporada}/jornada_{jornada}_partido_{partido}.html"
        return self._leer_archivo(BUCKET_BRONCE, s3_key)

    def leer_pdf_bronce(
        self,
        match_id: int,
        temporada: str = "2025-2026"
    ) -> Optional[bytes]:
        """
        Lee PDF desde BRONCE.
        
        Args:
            match_id: ID del partido
            temporada: Temporada
            
        Returns:
            Bytes del PDF o None
        """
        s3_key = f"{BRONCE_PDF}/{temporada}/feuille_de_match_{match_id}.pdf"
        return self._leer_archivo_binario(BUCKET_BRONCE, s3_key)
    
    # ================================================
    # CAPA PLATA (PROCESSED DATA)
    # ================================================
    
    def subir_eventos_plata(
        self,
        local_file: Path,
        match_id: int,
        temporada: str = "2025-2026"
    ) -> bool:
        """
        Sube CSV/JSON de eventos procesados a PLATA.
        
        Args:
            local_file: Archivo local
            match_id: ID del partido
            temporada: Temporada
            
        Returns:
            True si éxito
        """
        extension = local_file.suffix  # .csv o .json
        s3_key = f"{self.PLATA_EVENTOS}/{temporada}/eventos_{match_id}{extension}"
        return self._subir_archivo(local_file, self.BUCKET_PLATA, s3_key)
    
    def subir_actas_plata(
        self,
        local_file: Path,
        match_id: int,
        temporada: str = "2025-2026"
    ) -> bool:
        """
        Sube JSON de acta procesada a PLATA.
        
        Args:
            local_file: Archivo local
            match_id: ID del partido
            temporada: Temporada
            
        Returns:
            True si éxito
        """
        s3_key = f"{self.PLATA_ACTAS}/{temporada}/Partido-{match_id}.json"
        return self._subir_archivo(local_file, self.BUCKET_PLATA, s3_key)
    
    def leer_eventos_plata(
        self,
        match_id: int,
        temporada: str = "2025-2026",
        formato: str = "json"
    ) -> Optional[str]:
        """
        Lee eventos desde PLATA.
        
        Args:
            match_id: ID del partido
            temporada: Temporada
            formato: "json" o "csv"
            
        Returns:
            Contenido o None
        """
        s3_key = f"{self.PLATA_EVENTOS}/{temporada}/eventos_{match_id}.{formato}"
        return self._leer_archivo(self.BUCKET_PLATA, s3_key)
    
    def leer_actas_plata(
        self,
        match_id: int,
        temporada: str = "2025-2026",
        partido: str = "Partido-2025-08-02-BGL-Ligue"
    ) -> Optional[str]:
        """
        Lee acta JSON desde PLATA.
        
        Args:
            match_id: ID del partido
            temporada: Temporada
            partido: Id del Partido
            
        Returns:
            JSON string o None
        """
        s3_key = f"{self.PLATA_ACTAS}/{temporada}/{partido}-{match_id}.json"
        return self._leer_archivo(self.BUCKET_PLATA, s3_key)
    
    # ================================================
    # CAPA ORO (ANALYTICS-READY)
    # ================================================
    
    def subir_embeddings_oro(
        self,
        local_file: Path,
        nombre: str
    ) -> bool:
        """
        Sube archivo de embeddings a ORO.
        
        Args:
            local_file: Archivo local
            nombre: Nombre del archivo
            
        Returns:
            True si éxito
        """
        s3_key = f"{self.ORO_EMBEDDINGS}/{nombre}"
        return self._subir_archivo(local_file, self.BUCKET_ORO, s3_key)
    
    def subir_analytics_oro(
        self,
        local_file: Path,
        nombre: str
    ) -> bool:
        """
        Sube datos agregados a ORO.
        
        Args:
            local_file: Archivo local
            nombre: Nombre del archivo
            
        Returns:
            True si éxito
        """
        s3_key = f"{self.ORO_ANALYTICS}/{nombre}"
        return self._subir_archivo(local_file, self.BUCKET_ORO, s3_key)
    
    # ================================================
    # MÉTODOS PRIVADOS
    # ================================================
    
    def _subir_archivo(
        self,
        local_file: Path,
        bucket: str,
        s3_key: str
    ) -> bool:
        """Sube archivo a MinIO."""
        try:
            self.s3.upload_file(str(local_file), bucket, s3_key)
            size_mb = local_file.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Subido: {s3_key} ({size_mb:.2f} MB)")
            return True
        except ClientError as e:
            logger.error(f"❌ Error subiendo {s3_key}: {e}")
            return False
    
    def _leer_archivo(self, bucket: str, s3_key: str) -> Optional[str]:
        """Lee archivo de texto desde MinIO."""
        try:
            response = self.s3.get_object(Bucket=bucket, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            logger.info(f"✅ Leído: {s3_key}")
            return content
        except ClientError as e:
            logger.error(f"❌ Error leyendo {s3_key}: {e}")
            return None
    
    def _leer_archivo_binario(self, bucket: str, s3_key: str) -> Optional[bytes]:
        """Lee archivo binario desde MinIO."""
        try:
            response = self.s3.get_object(Bucket=bucket, Key=s3_key)
            content = response['Body'].read()
            logger.info(f"✅ Leído (binario): {s3_key}")
            return content
        except ClientError as e:
            logger.error(f"❌ Error leyendo {s3_key}: {e}")
            return None
    
    # ================================================
    # ESTADÍSTICAS
    # ================================================
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene estadísticas de uso de cada capa.
        
        Returns:
            Dict con stats por bucket
        """
        stats = {}
        
        for bucket in [BUCKET_BRONCE, BUCKET_PLATA, BUCKET_ORO]:
            try:
                response = self.s3.list_objects_v2(Bucket=bucket)
                archivos = response.get('Contents', [])
                
                total_archivos = len(archivos)
                total_bytes = sum(obj['Size'] for obj in archivos)
                total_mb = round(total_bytes / (1024 * 1024), 2)
                total_gb = round(total_bytes / (1024 * 1024 * 1024), 2)
                
                stats[bucket] = {
                    'archivos': total_archivos,
                    'size_mb': total_mb,
                    'size_gb': total_gb
                }
                
            except ClientError as e:
                logger.error(f"Error obteniendo stats de {bucket}: {e}")
                stats[bucket] = {'error': str(e)}
        
        return stats


# ================================================
# FUNCIONES DE CONVENIENCIA
# ================================================

def crear_cliente(
    endpoint: str = MINIO_ENDPOINT,
    access_key: str = MINIO_ACCESS_KEY,
    secret_key: str = MINIO_SECRET_KEY
) -> MedallionStorage:
    """
    Crea un cliente MedallionStorage con configuración por defecto.
    
    Args:
        endpoint: URL MinIO
        access_key: Access key
        secret_key: Secret key
        
    Returns:
        Cliente MedallionStorage
    """
    return MedallionStorage(endpoint, access_key, secret_key)


if __name__ == "__main__":
    # Test básico
    print("🧪 Test del módulo medallion_storage")
    print("=" * 50)
    
    # Crear cliente
    storage = crear_cliente()
    
    # Verificar estructura
    print("\n1. Verificando estructura Medallion...")
    status = storage.verificar_estructura()
    
    # Mostrar estadísticas
    print("\n2. Estadísticas de uso...")
    stats = storage.obtener_estadisticas()
    for bucket, data in stats.items():
        if 'error' not in data:
            print(f"\n📦 {bucket.upper()}:")
            print(f"   Archivos: {data['archivos']}")
            print(f"   Tamaño: {data['size_gb']:.2f} GB")
    
    print("\n" + "=" * 50)
    print("✅ Test completado")
