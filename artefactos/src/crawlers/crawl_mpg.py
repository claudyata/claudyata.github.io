"""
Video Crawler - Descarga de Videos MPG

Clase unificada para:
1. Generar URLs de segmentos de video (.ts)
2. Descargar segmentos en paralelo
3. Concatenar en video MP4
4. Subir a MinIO

Autor: Pedro José García Fernández
Fecha: 29 Diciembre 2024
"""

import csv
import os
import re
import time
import subprocess
import tempfile
import urllib.request
import urllib.parse
import requests
import logging
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoCrawler:
    """
    Crawler para descargar y procesar videos de partidos.
    
    Soporta tres fuentes:
    - live-arena (RTL Live)
    - aisportswatch
    - ondemand (RTL On Demand)
    """
    
    # Configuración de fuentes
    FUENTES = {
        'live': {
            'base_url': 'https://stream.rtl.lu/live-arena/{arena_id}/{quality}',
            'pattern': '{arena_id}_{segment:05d}.ts',
            'qualities': ['1080p', '720p', '480p'],
            'duration': 4  # segundos por segmento
        },
        'aisportswatch': {
            'base_url': 'https://content.aisportswatch.com/{arena_id}/{quality}',
            'pattern': '{arena_id}_{segment:05d}.ts',
            'qualities': ['720p', '480p'],
            'duration': 4
        },
        'ondemand': {
            'base_url': 'https://stream.rtl.lu/data/ondemand/video/e/hls/amlst:{arena_id}',
            'pattern': 'media_{media_id}_{segment:05d}.ts',
            'qualities': ['1920x1080', '1280x720', '854x480'],
            'duration': 9
        }
    }
    
    def __init__(self):
        """Inicializa el crawler de videos."""
        self.temp_dir = None
        logger.info("🎬 VideoCrawler inicializado")
    
    # ========================================================================
    # GENERACIÓN DE URLs
    # ========================================================================
    
    def generate_segment_urls(
        self,
        fuente: str,
        arena_id: str,
        start: int,
        end: int,
        quality: str = None,
        media_id: str = None
    ) -> List[Tuple[int, str]]:
        """
        Genera lista de URLs de segmentos.
        
        Args:
            fuente: 'live', 'aisportswatch', 'ondemand'
            arena_id: ID del stream
            start: Segmento inicial
            end: Segmento final
            quality: Calidad (ej: '1080p', '720p')
            media_id: ID de media (solo para ondemand)
        
        Returns:
            Lista de tuplas (segment_num, url)
        """
        
        if fuente not in self.FUENTES:
            raise ValueError(f"Fuente '{fuente}' no soportada. Opciones: {list(self.FUENTES.keys())}")
        
        config = self.FUENTES[fuente]
        
        # Quality por defecto
        if quality is None:
            quality = config['qualities'][0]
        
        # Para ondemand, necesitamos media_id
        if fuente == 'ondemand' and media_id is None:
            media_id = self._get_media_id(arena_id, quality)
        
        urls = []
        
        for i in range(start, end + 1):
            # Construir base URL
            base = config['base_url'].format(arena_id=arena_id, quality=quality)
            
            # Construir filename
            if fuente == 'ondemand':
                filename = config['pattern'].format(media_id=media_id, segment=i)
            else:
                filename = config['pattern'].format(arena_id=arena_id, segment=i)
            
            url = f"{base}/{filename}"
            urls.append((i, url))
        
        logger.info(f"📋 Generadas {len(urls)} URLs ({fuente}, {quality})")
        return urls
    
    def _get_media_id(self, arena_id: str, resolution: str = "1280x720") -> str:
        """
        Obtiene el media_id para videos ondemand desde el playlist maestro.
        
        Args:
            arena_id: ID del stream
            resolution: Resolución deseada
        
        Returns:
            media_id (ej: 'b6128920')
        """
        
        master_url = f"https://stream.rtl.lu/data/ondemand/video/e/hls/amlst:{arena_id}/playlist.m3u8"
        
        try:
            resp = requests.get(master_url, timeout=10)
            resp.raise_for_status()
            lines = resp.text.splitlines()
            
            for i, line in enumerate(lines):
                if f"RESOLUTION={resolution}" in line:
                    if i + 1 < len(lines):
                        chunklist_name = lines[i + 1].strip()
                        match = re.search(r'_(.+)\.m3u8', chunklist_name)
                        if match:
                            return match.group(1)
            
            raise ValueError(f"No se encontró media_id para {resolution} en playlist")
        
        except Exception as e:
            logger.error(f"Error obteniendo media_id: {e}")
            raise
    
    # ========================================================================
    # DESCARGA DE SEGMENTOS
    # ========================================================================
    
    def _download_segment(
        self,
        segment_num: int,
        url: str,
        output_dir: str,
        retries: int = 3,
        timeout: int = 60
    ) -> Tuple[bool, str]:
        """
        Descarga un segmento individual.
        
        Args:
            segment_num: Número de segmento
            url: URL del segmento
            output_dir: Directorio de salida
            retries: Número de reintentos
            timeout: Timeout en segundos
        
        Returns:
            (success, filepath)
        """
        
        filename = f"segment_{segment_num:05d}.ts"
        dest_path = os.path.join(output_dir, filename)
        
        # Si ya existe, skip
        if os.path.exists(dest_path):
            return True, dest_path
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        
        for attempt in range(1, retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status != 200:
                        raise Exception(f"HTTP {resp.status}")
                    
                    with open(dest_path, 'wb') as f:
                        while True:
                            chunk = resp.read(1024 * 1024)  # 1 MB chunks
                            if not chunk:
                                break
                            f.write(chunk)
                
                return True, dest_path
            
            except Exception as e:
                if attempt < retries:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                else:
                    logger.error(f"❌ Error descargando segmento {segment_num}: {e}")
                    return False, None
    
    def download_segments_parallel(
        self,
        urls: List[Tuple[int, str]],
        output_dir: str,
        max_workers: int = 16,
        progress_callback = None
    ) -> Tuple[List[str], int, int]:
        """
        Descarga segmentos en paralelo.
        
        Args:
            urls: Lista de (segment_num, url)
            output_dir: Directorio de salida
            max_workers: Número de threads
            progress_callback: Función callback(current, total)
        
        Returns:
            (filepaths, downloaded, failed)
        """
        
        os.makedirs(output_dir, exist_ok=True)
        
        downloaded_paths = []
        downloaded_count = 0
        failed_count = 0
        total = len(urls)
        
        logger.info(f"📥 Descargando {total} segmentos (workers={max_workers})...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._download_segment,
                    seg_num,
                    url,
                    output_dir
                ): seg_num for seg_num, url in urls
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                success, filepath = future.result()
                
                if success:
                    downloaded_paths.append(filepath)
                    downloaded_count += 1
                else:
                    failed_count += 1
                
                if progress_callback:
                    progress_callback(i, total)
                
                # Log cada 10%
                if i % max(1, total // 10) == 0:
                    logger.info(f"  Progreso: {i}/{total} ({i/total*100:.1f}%)")
        
        # Ordenar paths por número de segmento
        downloaded_paths.sort()
        
        logger.info(f"✅ Descargados: {downloaded_count}, ❌ Fallidos: {failed_count}")
        return downloaded_paths, downloaded_count, failed_count
    
    # ========================================================================
    # CONCATENACIÓN Y CONVERSIÓN A MP4
    # ========================================================================
    
    def concatenate_to_mp4(
        self,
        segment_paths: List[str],
        output_path: str,
        progress_callback = None
    ) -> bool:
        """
        Concatena segmentos .ts en un video MP4.
        
        Args:
            segment_paths: Lista de rutas a segmentos .ts
            output_path: Ruta del MP4 de salida
            progress_callback: Función callback(stage, message)
        
        Returns:
            success: bool
        """
        
        try:
            # Crear archivo de lista para ffmpeg
            list_file = output_path + '.list.txt'
            
            with open(list_file, 'w') as f:
                for path in segment_paths:
                    # ffmpeg requiere rutas relativas o absolutas
                    abs_path = os.path.abspath(path)
                    f.write(f"file '{abs_path}'\n")
            
            if progress_callback:
                progress_callback("concatenating", "Concatenando segmentos...")
            
            logger.info(f"🎬 Concatenando {len(segment_paths)} segmentos -> {output_path}")
            
            # Comando ffmpeg
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',  # Stream copy (rápido)
                '-y',  # Sobrescribir
                output_path
            ]
            
            # Ejecutar
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutos max
            )
            
            # Limpiar archivo de lista
            try:
                os.remove(list_file)
            except:
                pass
            
            if result.returncode != 0:
                logger.error(f"❌ Error en ffmpeg: {result.stderr}")
                return False
            
            # Verificar que el archivo existe y tiene tamaño
            if not os.path.exists(output_path):
                logger.error(f"❌ Archivo de salida no creado: {output_path}")
                return False
            
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"✅ Video creado: {output_path} ({size_mb:.1f} MB)")
            
            if progress_callback:
                progress_callback("complete", f"Video creado ({size_mb:.1f} MB)")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error concatenando: {e}")
            return False
    
    # ========================================================================
    # MÉTODO PRINCIPAL
    # ========================================================================
    
    def descarga_mp4(
        self,
        modo: int,
        jornada: int,
        partido: int,
        match_id: int = None,
        arena_id: str = None,
        fuente: str = 'live',
        ranges: List[Tuple[int, int]] = None,
        progress_callback = None
    ) -> Dict[str, any]:
        """
        Descarga video MP4 del partido especificado.
        
        Args:
            modo: Modo de descarga (1=Alta 1080p, 2=Media 720p, 3=Baja 480p)
            jornada: Número de jornada (1-16)
            partido: Número de partido dentro de la jornada
            match_id: ID del partido (para nombre de archivo)
            arena_id: ID del stream (obligatorio)
            fuente: 'live', 'aisportswatch', 'ondemand'
            ranges: Lista de rangos [(start, end), ...] (obligatorio)
            progress_callback: Función callback(stage, current, total)
        
        Returns:
            Dict con:
            {
                'success': bool,
                'ruta_local': str,
                'ruta_minio': str,
                'tamano_mb': float,
                'duracion_seg': float,
                'segmentos_descargados': int,
                'segmentos_fallidos': int,
                'error': str
            }
        """
        
        logger.info(f"📥 Iniciando descarga: Jornada {jornada}, Partido {partido}, Modo {modo}")
        
        # ====================================================================
        # VALIDACIÓN DE PARÁMETROS
        # ====================================================================
        
        if arena_id is None:
            return {
                'success': False,
                'error': 'arena_id es obligatorio'
            }
        
        if ranges is None or not ranges:
            return {
                'success': False,
                'error': 'ranges es obligatorio (ej: [(0, 900), (1000, 2000)])'
            }
        
        # ====================================================================
        # CONFIGURACIÓN
        # ====================================================================
        
        # Mapeo de modo a calidad
        quality_map = {
            1: '1080p',  # Alta
            2: '720p',   # Media
            3: '480p'    # Baja
        }
        
        quality = quality_map.get(modo, '720p')
        
        # Nombre de archivo
        if match_id is None:
            match_id = f"{jornada}{partido:02d}"
        
        filename = f"1Partido-BGL-Ligue-{match_id}.mp4"
        
        # ====================================================================
        # PASO 1: GENERAR URLs DE TODOS LOS SEGMENTOS
        # ====================================================================
        
        if progress_callback:
            progress_callback("generating", 0, 1)
        
        all_urls = []
        
        for start, end in ranges:
            urls = self.generate_segment_urls(
                fuente=fuente,
                arena_id=arena_id,
                start=start,
                end=end,
                quality=quality
            )
            all_urls.extend(urls)
        
        total_segments = len(all_urls)
        logger.info(f"📋 Total segmentos a descargar: {total_segments}")
        
        # ====================================================================
        # PASO 2: CREAR DIRECTORIO TEMPORAL
        # ====================================================================
        
        self.temp_dir = tempfile.mkdtemp(prefix=f"video_{jornada}_{partido}_")
        logger.info(f"📁 Directorio temporal: {self.temp_dir}")
        
        # ====================================================================
        # PASO 3: DESCARGAR SEGMENTOS EN PARALELO
        # ====================================================================
        
        if progress_callback:
            progress_callback("downloading", 0, total_segments)
        
        def download_progress(current, total):
            if progress_callback:
                progress_callback("downloading", current, total)
        
        segment_paths, downloaded, failed = self.download_segments_parallel(
            urls=all_urls,
            output_dir=self.temp_dir,
            max_workers=16,
            progress_callback=download_progress
        )
        
        if failed > 0:
            logger.warning(f"⚠️ {failed} segmentos fallaron, continuando con {downloaded} exitosos")
        
        if downloaded == 0:
            return {
                'success': False,
                'error': f'No se descargó ningún segmento (total fallidos: {failed})'
            }
        
        # ====================================================================
        # PASO 4: CONCATENAR A MP4
        # ====================================================================
        
        output_path = os.path.join(self.temp_dir, filename)
        
        def concat_progress(stage, message):
            if progress_callback:
                progress_callback(stage, 0, 1)
        
        success = self.concatenate_to_mp4(
            segment_paths=segment_paths,
            output_path=output_path,
            progress_callback=concat_progress
        )
        
        if not success:
            return {
                'success': False,
                'error': 'Error al concatenar segmentos en MP4'
            }
        
        # ====================================================================
        # PASO 5: SUBIR A MINIO
        # ====================================================================
        
        if progress_callback:
            progress_callback("uploading", 0, 1)
        
        try:
            from shared_resources import get_storage
            storage = get_storage()
            
            ruta_minio = f"video/2025-2026/jornada_{jornada}/{filename}"
            
            logger.info(f"☁️ Subiendo a MinIO: {ruta_minio}")
            
            storage.s3.upload_file(  # ← CORRECTO: usa storage.s3 y upload_file
                output_path,
                'plata',  # bucket
                ruta_minio
            )
            
            logger.info(f"✅ Subido a MinIO exitosamente")
        
        except Exception as e:
            logger.error(f"❌ Error subiendo a MinIO: {e}")
            return {
                'success': False,
                'error': f'Error subiendo a MinIO: {str(e)}'
            }
        
        # ====================================================================
        # PASO 6: OBTENER METADATA
        # ====================================================================
        
        tamano_mb = os.path.getsize(output_path) / (1024 * 1024)
        
        # Obtener duración con ffprobe
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                duracion_seg = float(data['format'].get('duration', 0))
            else:
                duracion_seg = 0
        except:
            duracion_seg = 0
        
        # ====================================================================
        # PASO 7: CLEANUP
        # ====================================================================
        
        if progress_callback:
            progress_callback("cleaning", 0, 1)
        
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info(f"🗑️ Limpieza: {self.temp_dir} eliminado")
        except Exception as e:
            logger.warning(f"⚠️ Error en cleanup: {e}")
        
        # ====================================================================
        # RETORNO
        # ====================================================================
        
        logger.info(f"✅ Descarga completada exitosamente")
        
        return {
            'success': True,
            'ruta_local': output_path,
            'ruta_minio': ruta_minio,
            'tamano_mb': tamano_mb,
            'duracion_seg': duracion_seg,
            'segmentos_descargados': downloaded,
            'segmentos_fallidos': failed
        }