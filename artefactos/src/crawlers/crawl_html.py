"""
crawl_html.py
=============

Scraper para comentarios HTML de RTL Sport usando Selenium Remote.
Guarda archivos localmente y los sube a MinIO (bucket bronce).

Autor: Pedro José García Fernández
Fecha: 26 Diciembre 2024
Proyecto: Cl@ud-ia-data TFG
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RTLSportScraper:
    """
    Scraper para comentarios de partidos de RTL Sport.
    
    Usa Selenium Remote (Docker) y guarda en MinIO.
    """
    
    # Configuración
    RTL_BASE_URL = "https://www.rtl.lu/sport/futtball/match?m="
    SELENIUM_REMOTE_URL = "http://localhost:4444"
    RATE_LIMIT_SECONDS = 3
    PAGE_LOAD_TIMEOUT = 30
    
    def __init__(
        self,
        output_dir: Path = Path("./html"),
        minio_storage=None  # Instancia de MedallionStorage (opcional)
    ):
        """
        Inicializa el scraper.
        
        Args:
            output_dir: Directorio local para guardar HTMLs
            minio_storage: Instancia de MedallionStorage para subir a MinIO
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.minio_storage = minio_storage
        self.driver = None
        self.cookies_rechazadas = False
        logger.info(f"Scraper inicializado. Output: {output_dir}")
    
    def connect(self):
        """Conecta al Selenium Remote (Docker)."""
        firefox_options = webdriver.FirefoxOptions()
        
        try:
            self.driver = webdriver.Remote(
                command_executor=self.SELENIUM_REMOTE_URL,
                options=firefox_options
            )
            self.driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)
            logger.info(f"✅ Conectado a Selenium Remote: {self.SELENIUM_REMOTE_URL}")
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando a Selenium: {e}")
            return False
    
    def disconnect(self):
        """Cierra conexión con Selenium."""
        if self.driver:
            self.driver.quit()
            logger.info("🔌 Desconectado de Selenium")
    
    def _rechazar_cookies(self):
        """
        Rechaza cookies GDPR (solo primera vez).
        Usa el botón 'didomi-notice-disagree-button'.
        """
        if self.cookies_rechazadas:
            return
        
        try:
            # Ir a página principal primero
            self.driver.get("https://www.rtl.lu/sport/futtball")
            time.sleep(2)
            
            # Buscar y hacer clic en botón de rechazo
            reject_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-disagree-button"))
            )
            reject_button.click()
            logger.info("✅ Cookies rechazadas")
            time.sleep(2)
            self.cookies_rechazadas = True
            
        except TimeoutException:
            logger.debug("No se encontró popup de cookies (ya fue rechazado)")
            self.cookies_rechazadas = True
        except Exception as e:
            logger.warning(f"Error rechazando cookies: {e}")
            self.cookies_rechazadas = True  # Marcar como intentado
    
    def scrape_match(
        self,
        match_id: int,
        jornada: int,
        partido: int,
        temporada: str = "2025-2026"
    ) -> Optional[Path]:
        """
        Scrapea comentarios de un partido.
        
        Args:
            match_id: ID del partido en RTL (ej: 1001143)
            jornada: Número de jornada (1-15)
            partido: Número de partido en la jornada (1-8)
            temporada: Temporada (para organizar archivos)
            
        Returns:
            Path del HTML guardado o None si falla
        """
        url = f"{self.RTL_BASE_URL}{match_id}"
        
        try:
            logger.info(f"📥 Scrapeando match {match_id} (J{jornada}-P{partido})...")
            
            # Rechazar cookies solo la primera vez
            if not self.cookies_rechazadas:
                self._rechazar_cookies()
            
            # Navegar al partido
            self.driver.get(url)
            
            # Esperar contenedor principal
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "BasePage_page__YdIrZ"))
                )
            except TimeoutException:
                logger.warning(f"⚠️ Timeout esperando contenido en match {match_id}")
                return None
            
            # Esperar que el contenido REAL cargue (equipos o liveticker)
            logger.debug(f"  ⏳ Esperando carga completa de contenido...")
            time.sleep(10)  # Dar tiempo a que JavaScript cargue todo el contenido
            
            # Extraer secciones
            sections = self.driver.find_elements(By.CLASS_NAME, "BasePage_page__YdIrZ")
            
            if not sections:
                logger.warning(f"⚠️ No se encontró contenido en match {match_id}")
                return None
            
            # Guardar HTML localmente
            temporada_dir = self.output_dir / temporada
            temporada_dir.mkdir(exist_ok=True)
            
            filename = temporada_dir / f"jornada_{jornada}_partido_{partido}.html"
            
            with open(filename, "w", encoding="utf-8") as f:
                for section in sections:
                    f.write(section.get_attribute("outerHTML"))
                    f.write("\n")
            
            size_kb = filename.stat().st_size / 1024
            logger.info(f"✅ Guardado localmente: {filename.name} ({size_kb:.1f} KB)")
            
            # Subir a MinIO si está configurado
            if self.minio_storage:
                try:
                    success = self.minio_storage.subir_html_bronce(
                        local_file=filename,
                        match_id=match_id,
                        temporada=temporada
                    )
                    if success:
                        logger.info(f"☁️ Subido a MinIO: bronce/html/{temporada}/match_{match_id}.html")
                except Exception as e:
                    logger.warning(f"⚠️ Error subiendo a MinIO: {e}")
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Error scrapeando match {match_id}: {e}")
            return None
    
    def scrape_temporada(
        self,
        match_id_start: int,
        total_jornadas: int = 15,
        partidos_por_jornada: int = 8,
        temporada: str = "2025-2026"
    ) -> Dict:
        """
        Scrapea todos los partidos de una temporada.
        
        Args:
            match_id_start: Primer match ID de la temporada
            total_jornadas: Número de jornadas (default: 15)
            partidos_por_jornada: Partidos por jornada (default: 8)
            temporada: Temporada
            
        Returns:
            Dict con estadísticas (éxitos, errores, tiempo)
        """
        total_partidos = total_jornadas * partidos_por_jornada
        
        logger.info(f"🚀 Iniciando scraping de temporada {temporada}")
        logger.info(f"   Jornadas: {total_jornadas}")
        logger.info(f"   Partidos por jornada: {partidos_por_jornada}")
        logger.info(f"   Total partidos: {total_partidos}")
        logger.info(f"   Match ID inicial: {match_id_start}")
        logger.info(f"   Rate limit: {self.RATE_LIMIT_SECONDS}s")
        
        start_time = time.time()
        exitos = 0
        errores = 0
        
        for jornada in range(1, total_jornadas + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"📅 JORNADA {jornada}/{total_jornadas}")
            logger.info(f"{'='*60}")
            
            for partido in range(1, partidos_por_jornada + 1):
                # Calcular match_id
                match_id = match_id_start + (jornada - 1) * partidos_por_jornada + (partido - 1)
                
                # Scrapear
                resultado = self.scrape_match(match_id, jornada, partido, temporada)
                
                if resultado:
                    exitos += 1
                else:
                    errores += 1
            
            # Progreso de jornada
            progreso = (jornada / total_jornadas) * 100
            logger.info(f"📊 Progreso: {progreso:.1f}% ({exitos} éxitos, {errores} errores)")
        
        elapsed = time.time() - start_time
        
        stats = {
            'exitos': exitos,
            'errores': errores,
            'total': total_partidos,
            'tiempo_segundos': elapsed,
            'tiempo_minutos': elapsed / 60
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 RESUMEN FINAL")
        logger.info(f"{'='*60}")
        logger.info(f"   ✅ Éxitos: {exitos}/{total_partidos}")
        logger.info(f"   ❌ Errores: {errores}/{total_partidos}")
        logger.info(f"   ⏱️ Tiempo: {stats['tiempo_minutos']:.1f} minutos")
        logger.info(f"{'='*60}")
        
        return stats


def main():
    """Función principal para uso desde CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scraper RTL Sport")
    parser.add_argument("--start", type=int, default=1001143,
                       help="Primer Match ID (default: 1001143)")
    parser.add_argument("--jornadas", type=int, default=15,
                       help="Número de jornadas (default: 15)")
    parser.add_argument("--partidos", type=int, default=8,
                       help="Partidos por jornada (default: 8)")
    parser.add_argument("--temporada", type=str, default="2025-2026",
                       help="Temporada (default: 2025-2026)")
    parser.add_argument("--output", type=str, default="./html",
                       help="Directorio de salida (default: ./html)")
    parser.add_argument("--single", type=int,
                       help="Scrapear solo un partido (Match ID)")
    parser.add_argument("--minio", action="store_true",
                       help="Subir a MinIO automáticamente")
    
    args = parser.parse_args()
    
    # Configurar MinIO si se solicita
    minio_storage = None
    if args.minio:
        try:
            from medallion_storage import crear_cliente
            minio_storage = crear_cliente()
            logger.info("☁️ MinIO habilitado")
        except ImportError:
            logger.warning("⚠️ No se pudo importar medallion_storage. Continuando sin MinIO.")
    
    # Crear scraper
    scraper = RTLSportScraper(
        output_dir=Path(args.output),
        minio_storage=minio_storage
    )
    
    # Conectar a Selenium
    if not scraper.connect():
        logger.error("No se pudo conectar a Selenium.")
        logger.error("Verifica que el contenedor esté corriendo:")
        logger.error("  docker ps | grep selenium")
        return
    
    try:
        if args.single:
            # Scrapear un solo partido
            scraper.scrape_match(args.single, 1, 1, args.temporada)
        else:
            # Scrapear temporada completa
            scraper.scrape_temporada(
                match_id_start=args.start,
                total_jornadas=args.jornadas,
                partidos_por_jornada=args.partidos,
                temporada=args.temporada
            )
    finally:
        # Siempre desconectar
        scraper.disconnect()


if __name__ == "__main__":
    main()
