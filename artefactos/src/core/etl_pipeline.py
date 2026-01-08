"""
etl_pipeline.py
===============

Pipeline ETL para procesar HTMLs de RTL Sport (Bronce → Plata).
Extrae eventos, equipos y goleadores de comentarios de partidos.

Autor: Pedro José García Fernández
Fecha: 26 Diciembre 2024
Proyecto: Cl@ud-ia-data TFG
"""

import logging
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup

try:
    from core.config import *
except ImportError as e:
    from config import *

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ETLPipeline:
    """
    Pipeline ETL para transformar datos de Bronce a Plata.
    
    Procesa HTMLs scrapeados de RTL Sport y genera datos estructurados:
    - Eventos minuto a minuto (CSV/JSON)
    - Información de equipos (CSV/JSON)
    - Goleadores (CSV/JSON)
    """
    
    def __init__(
        self,
        minio_storage=None,
        output_dir: Path = Path("./plata"),
        temporada: str = "2025-2026"
    ):
        """
        Inicializa el pipeline ETL.
        
        Args:
            minio_storage: Instancia de MedallionStorage (opcional)
            output_dir: Directorio local para guardar CSVs
            temporada: Temporada a procesar
        """
        self.minio_storage = minio_storage
        self.output_dir = output_dir
        self.temporada = temporada
        
        # Crear directorios locales
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "eventos").mkdir(exist_ok=True)
        (self.output_dir / "equipos").mkdir(exist_ok=True)
        (self.output_dir / "goleadores").mkdir(exist_ok=True)
        
        logger.info(f"ETL Pipeline inicializado para temporada {temporada}")
    
    # ================================================
    # PASO 1: PARSEAR EVENTOS
    # ================================================
    
    def parse_html_to_events(
        self,
        html_content: str,
        match_id: int,
        jornada: int,
        partido: int
    ) -> List[Dict]:
        """
        Extrae eventos del liveticker de un HTML.
        
        Args:
            html_content: Contenido HTML del partido
            match_id: ID del partido
            jornada: Número de jornada
            partido: Número de partido
            
        Returns:
            Lista de eventos con estructura:
            {
                'match_id': int,
                'jornada': int,
                'partido': int,
                'minuto': str,
                'minuto_base': int,
                'minuto_adicional': int,
                'minuto_exacto': int,
                'equipo': str (Local/Visitante),
                'texto': str
            }
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        eventos = []
        
        # Eventos del equipo LOCAL
        eventos_local = soup.find_all(
            "div",
            class_=lambda x: x and "livetickerTeamLeft" in x
        )
        
        for evento in eventos_local:
            minuto_tag = evento.find(
                "p",
                class_=lambda x: x and "livetickerTime" in x
            )
            
            if minuto_tag:
                texto_tag = evento.find(
                    "p",
                    class_=lambda x: x and "livetickerEventText" in x
                )
                
                minuto = minuto_tag.get_text(strip=True)
                texto = texto_tag.get_text(strip=True) if texto_tag else ""
                
                tiempo_base, tiempo_adicional, minuto_exacto = self._descomponer_minuto(minuto)
                
                eventos.append({
                    'match_id': match_id,
                    'jornada': jornada,
                    'partido': partido,
                    'minuto': minuto,
                    'minuto_base': tiempo_base,
                    'minuto_adicional': tiempo_adicional,
                    'minuto_exacto': minuto_exacto,
                    'equipo': 'Local',
                    'texto': texto
                })
        
        # Eventos del equipo VISITANTE
        eventos_visitante = soup.find_all(
            "div",
            class_=lambda x: x and "livetickerTeamRight" in x
        )
        
        for evento in eventos_visitante:
            minuto_tag = evento.find(
                "p",
                class_=lambda x: x and "livetickerTime" in x
            )
            
            if minuto_tag:
                texto_tag = evento.find(
                    "p",
                    class_=lambda x: x and "livetickerEventText" in x
                )
                
                minuto = minuto_tag.get_text(strip=True)
                texto = texto_tag.get_text(strip=True) if texto_tag else ""
                
                tiempo_base, tiempo_adicional, minuto_exacto = self._descomponer_minuto(minuto)
                
                eventos.append({
                    'match_id': match_id,
                    'jornada': jornada,
                    'partido': partido,
                    'minuto': minuto,
                    'minuto_base': tiempo_base,
                    'minuto_adicional': tiempo_adicional,
                    'minuto_exacto': minuto_exacto,
                    'equipo': 'Visitante',
                    'texto': texto
                })
        
        # Ordenar por minuto exacto (descendente)
        eventos.sort(key=lambda x: x['minuto_exacto'], reverse=True)
        
        logger.info(f"  📋 Match {match_id}: {len(eventos)} eventos extraídos")
        return eventos
    
    # ================================================
    # PASO 2: EXTRAER EQUIPOS
    # ================================================
    
    def extract_teams(
        self,
        html_content: str,
        match_id: int,
        jornada: int,
        partido: int
    ) -> Dict:
        """
        Extrae nombres de equipos Local y Visitante.
        
        Args:
            html_content: Contenido HTML del partido
            match_id: ID del partido
            jornada: Número de jornada
            partido: Número de partido
            
        Returns:
            Dict con estructura:
            {
                'match_id': int,
                'jornada': int,
                'partido': int,
                'equipo_local': str,
                'equipo_visitante': str
            }
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extraer equipo local
        equipo_local_div = soup.find(
            "div",
            class_=lambda x: x and "homeTeam" in x
        )
        equipo_local = ""
        if equipo_local_div:
            equipo_local_nombre = equipo_local_div.find(
                "div",
                class_=lambda x: x and "teamName" in x
            )
            if equipo_local_nombre:
                equipo_local = equipo_local_nombre.get_text(strip=True)
        
        # Extraer equipo visitante
        equipo_visitante_div = soup.find(
            "div",
            class_=lambda x: x and "awayTeam" in x
        )
        equipo_visitante = ""
        if equipo_visitante_div:
            equipo_visitante_nombre = equipo_visitante_div.find(
                "div",
                class_=lambda x: x and "teamName" in x
            )
            if equipo_visitante_nombre:
                equipo_visitante = equipo_visitante_nombre.get_text(strip=True)
        
        logger.info(f"  ⚽ Match {match_id}: {equipo_local} vs {equipo_visitante}")
        
        return {
            'match_id': match_id,
            'jornada': jornada,
            'partido': partido,
            'equipo_local': equipo_local,
            'equipo_visitante': equipo_visitante
        }
    
    # ================================================
    # PASO 3: EXTRAER GOLEADORES
    # ================================================
    
    def extract_scorers(
        self,
        html_content: str,
        match_id: int,
        jornada: int,
        partido: int
    ) -> List[Dict]:
        """
        Extrae información de goleadores desde la tabla resumen.
        Detecta autogoles por el color rojo del SVG.
        
        Args:
            html_content: Contenido HTML del partido
            match_id: ID del partido
            jornada: Número de jornada
            partido: Número de partido
            
        Returns:
            Lista de goles con estructura:
            {
                'match_id': int,
                'jornada': int,
                'partido': int,
                'jugador': str,
                'minuto': str,
                'equipo_marca': str (Local/Visitante),
                'equipo_beneficia': str (Local/Visitante),
                'tipo': str (Gol/Autogol),
                'marcador': str
            }
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        goles = []
        
        # Buscar tabla de resumen de goles
        tabla = soup.find(
            "table",
            class_=lambda x: x and "livetickerSummary" in x
        )
        
        if not tabla:
            logger.debug(f"  ⚠️ Match {match_id}: No se encontró tabla de goles")
            return goles
        
        # Procesar cada fila
        filas = tabla.find_all("tr")
        
        for fila in filas:
            celdas = fila.find_all("td")
            
            if len(celdas) >= 5:
                # Gol LOCAL
                jugador_local_td = celdas[0]
                jugador_local = jugador_local_td.get_text(strip=True)
                minuto_local = celdas[1].get_text(strip=True)
                
                # Marcador
                marcador = celdas[2].get_text(strip=True)
                
                # Gol VISITANTE
                minuto_visitante = celdas[3].get_text(strip=True)
                jugador_visitante_td = celdas[4]
                jugador_visitante = jugador_visitante_td.get_text(strip=True)
                
                # Procesar gol local
                if jugador_local and minuto_local:
                    es_autogol = self._detectar_autogol(jugador_local_td)
                    tipo_gol = "Autogol" if es_autogol else "Gol"
                    equipo_marca = "Local"
                    equipo_beneficia = "Visitante" if es_autogol else "Local"
                    
                    goles.append({
                        'match_id': match_id,
                        'jornada': jornada,
                        'partido': partido,
                        'jugador': jugador_local,
                        'minuto': minuto_local,
                        'equipo_marca': equipo_marca,
                        'equipo_beneficia': equipo_beneficia,
                        'tipo': tipo_gol,
                        'marcador': marcador
                    })
                    
                    emoji = "🔴" if es_autogol else "⚽"
                    logger.info(f"    {emoji} {jugador_local} ({minuto_local}) - {tipo_gol}")
                
                # Procesar gol visitante
                if jugador_visitante and minuto_visitante:
                    es_autogol = self._detectar_autogol(jugador_visitante_td)
                    tipo_gol = "Autogol" if es_autogol else "Gol"
                    equipo_marca = "Visitante"
                    equipo_beneficia = "Local" if es_autogol else "Visitante"
                    
                    goles.append({
                        'match_id': match_id,
                        'jornada': jornada,
                        'partido': partido,
                        'jugador': jugador_visitante,
                        'minuto': minuto_visitante,
                        'equipo_marca': equipo_marca,
                        'equipo_beneficia': equipo_beneficia,
                        'tipo': tipo_gol,
                        'marcador': marcador
                    })
                    
                    emoji = "🔴" if es_autogol else "⚽"
                    logger.info(f"    {emoji} {jugador_visitante} ({minuto_visitante}) - {tipo_gol}")
        
        return goles
    
    # ================================================
    # PASO 4: PROCESAR UN PARTIDO COMPLETO
    # ================================================
    
    def process_match(
        self,
        match_id: int,
        jornada: int,
        partido: int
    ) -> Dict:
        """
        Procesa un partido completo: eventos, equipos, goleadores.
        
        Args:
            match_id: ID del partido
            jornada: Número de jornada
            partido: Número de partido
            
        Returns:
            Dict con:
            {
                'success': bool,
                'match_id': int,
                'eventos': List[Dict],
                'equipos': Dict,
                'goleadores': List[Dict]
            }
        """
        logger.info(f"🔄 Procesando match {match_id} (J{jornada}-P{partido})...")
        
        try:
            # Leer HTML desde BRONCE
            if self.minio_storage:
                html_content = self.minio_storage.leer_html_bronce(
                    match_id=match_id,
                    temporada=self.temporada
                )
            else:
                # Leer de archivo local (fallback)
                local_file = self.output_dir.parent / "html" / self.temporada / f"jornada_{jornada}_partido_{partido}.html"
                if not local_file.exists():
                    logger.warning(f"  ⚠️ Archivo no encontrado: {local_file}")
                    return {'success': False, 'match_id': match_id}
                
                with open(local_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            
            if not html_content:
                logger.warning(f"  ⚠️ HTML vacío para match {match_id}")
                return {'success': False, 'match_id': match_id}
            
            # Extraer datos
            eventos = self.parse_html_to_events(html_content, match_id, jornada, partido)
            equipos = self.extract_teams(html_content, match_id, jornada, partido)
            goleadores = self.extract_scorers(html_content, match_id, jornada, partido)
            
            logger.info(f"  ✅ Match {match_id} procesado: {len(eventos)} eventos, {len(goleadores)} goles")
            
            return {
                'success': True,
                'match_id': match_id,
                'eventos': eventos,
                'equipos': equipos,
                'goleadores': goleadores
            }
            
        except Exception as e:
            logger.error(f"  ❌ Error procesando match {match_id}: {e}")
            return {'success': False, 'match_id': match_id, 'error': str(e)}
    
    # ================================================
    # PASO 5: PROCESAR TEMPORADA COMPLETA
    # ================================================
    
    def process_season(
        self,
        match_id_start: int,
        total_jornadas: int = 15,
        partidos_por_jornada: int = 8
    ) -> Dict:
        """
        Procesa todos los partidos de una temporada.
        
        Args:
            match_id_start: Primer match ID
            total_jornadas: Número de jornadas
            partidos_por_jornada: Partidos por jornada
            
        Returns:
            Dict con estadísticas y DataFrames consolidados
        """
        total_partidos = total_jornadas * partidos_por_jornada
        
        logger.info(f"🚀 Iniciando ETL temporada {self.temporada}")
        logger.info(f"   Partidos: {total_partidos}")
        logger.info(f"   Match IDs: {match_id_start} - {match_id_start + total_partidos - 1}")
        
        # Acumuladores
        todos_eventos = []
        todos_equipos = []
        todos_goleadores = []
        
        exitos = 0
        errores = 0
        
        # Procesar cada partido
        for jornada in range(1, total_jornadas + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"📅 JORNADA {jornada}/{total_jornadas}")
            logger.info(f"{'='*60}")
            
            for partido in range(1, partidos_por_jornada + 1):
                match_id = match_id_start + (jornada - 1) * partidos_por_jornada + (partido - 1)
                
                resultado = self.process_match(match_id, jornada, partido)
                
                if resultado['success']:
                    todos_eventos.extend(resultado['eventos'])
                    todos_equipos.append(resultado['equipos'])
                    todos_goleadores.extend(resultado['goleadores'])
                    exitos += 1
                else:
                    errores += 1
        
        # Crear DataFrames consolidados
        df_eventos = pd.DataFrame(todos_eventos)
        df_equipos = pd.DataFrame(todos_equipos)
        df_goleadores = pd.DataFrame(todos_goleadores)
        
        # Filtrar eventos con texto
        if not df_eventos.empty:
            df_eventos_filtrado = df_eventos[
                df_eventos['texto'].notna() & 
                (df_eventos['texto'].str.strip() != '')
            ].copy()
        else:
            df_eventos_filtrado = df_eventos
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 RESUMEN ETL")
        logger.info(f"{'='*60}")
        logger.info(f"   ✅ Partidos procesados: {exitos}/{total_partidos}")
        logger.info(f"   ❌ Errores: {errores}")
        logger.info(f"   📋 Total eventos: {len(df_eventos)}")
        logger.info(f"   📝 Eventos con texto: {len(df_eventos_filtrado)}")
        logger.info(f"   ⚽ Total goles: {len(df_goleadores)}")
        
        if not df_goleadores.empty:
            goles_normales = len(df_goleadores[df_goleadores['tipo'] == 'Gol'])
            autogoles = len(df_goleadores[df_goleadores['tipo'] == 'Autogol'])
            logger.info(f"      • Goles: {goles_normales}")
            logger.info(f"      • Autogoles: {autogoles}")
        
        return {
            'exitos': exitos,
            'errores': errores,
            'total': total_partidos,
            'df_eventos': df_eventos,
            'df_eventos_filtrado': df_eventos_filtrado,
            'df_equipos': df_equipos,
            'df_goleadores': df_goleadores
        }
    
    # ================================================
    # PASO 6: GUARDAR A PLATA
    # ================================================
    
    def save_to_plata(
        self,
        df_eventos: pd.DataFrame,
        df_equipos: pd.DataFrame,
        df_goleadores: pd.DataFrame,
        save_format: str = "both"  # "csv", "json", "both"
    ) -> bool:
        """
        Guarda DataFrames procesados a la capa PLATA.
        
        Args:
            df_eventos: DataFrame de eventos
            df_equipos: DataFrame de equipos
            df_goleadores: DataFrame de goleadores
            save_format: Formato de salida ("csv", "json", "both")
            
        Returns:
            True si éxito
        """
        logger.info(f"\n💾 Guardando datos a capa PLATA...")
        
        try:
            # Guardar localmente
            if save_format in ["csv", "both"]:
                # CSVs
                eventos_csv = self.output_dir / "eventos" / f"eventos_{self.temporada}.csv"
                equipos_csv = self.output_dir / "equipos" / f"equipos_{self.temporada}.csv"
                goleadores_csv = self.output_dir / "goleadores" / f"goleadores_{self.temporada}.csv"
                
                df_eventos.to_csv(eventos_csv, index=False)
                df_equipos.to_csv(equipos_csv, index=False)
                df_goleadores.to_csv(goleadores_csv, index=False)
                
                logger.info(f"   ✅ CSVs guardados en {self.output_dir}")
            
            if save_format in ["json", "both"]:
                # JSONs (para traducción posterior)
                eventos_json = self.output_dir / "eventos" / f"eventos_{self.temporada}.json"
                equipos_json = self.output_dir / "equipos" / f"equipos_{self.temporada}.json"
                goleadores_json = self.output_dir / "goleadores" / f"goleadores_{self.temporada}.json"
                
                df_eventos.to_json(eventos_json, orient='records', force_ascii=False, indent=2)
                df_equipos.to_json(equipos_json, orient='records', force_ascii=False, indent=2)
                df_goleadores.to_json(goleadores_json, orient='records', force_ascii=False, indent=2)
                
                logger.info(f"   ✅ JSONs guardados en {self.output_dir}")
            
            # Subir a MinIO si está configurado
            if self.minio_storage:
                # Subir eventos
                if save_format in ["csv", "both"]:
                    # CSV consolidado de toda la temporada
                    eventos_csv_temp = Path(f"/tmp/eventos_{self.temporada}.csv")
                    df_eventos.to_csv(eventos_csv_temp, index=False)
                    
                    # Subir como archivo consolidado
                    self.minio_storage.s3.upload_file(
                        str(eventos_csv_temp),
                        self.minio_storage.BUCKET_PLATA,
                        f"eventos/{self.temporada}/eventos_consolidado.csv"
                    )
                    eventos_csv_temp.unlink()
                
                if save_format in ["json", "both"]:
                    # JSON consolidado
                    eventos_json_temp = Path(f"/tmp/eventos_{self.temporada}.json")
                    df_eventos.to_json(eventos_json_temp, orient='records', force_ascii=False, indent=2)
                    
                    self.minio_storage.s3.upload_file(
                        str(eventos_json_temp),
                        self.minio_storage.BUCKET_PLATA,
                        f"eventos/{self.temporada}/eventos_consolidado.json"
                    )
                    eventos_json_temp.unlink()
                
                # Equipos y goleadores (solo consolidados)
                equipos_csv_temp = Path(f"/tmp/equipos_{self.temporada}.csv")
                df_equipos.to_csv(equipos_csv_temp, index=False)
                self.minio_storage.s3.upload_file(
                    str(equipos_csv_temp),
                    self.minio_storage.BUCKET_PLATA,
                    f"equipos/{self.temporada}.csv"
                )
                equipos_csv_temp.unlink()
                
                goleadores_csv_temp = Path(f"/tmp/goleadores_{self.temporada}.csv")
                df_goleadores.to_csv(goleadores_csv_temp, index=False)
                self.minio_storage.s3.upload_file(
                    str(goleadores_csv_temp),
                    self.minio_storage.BUCKET_PLATA,
                    f"goleadores/{self.temporada}.csv"
                )
                goleadores_csv_temp.unlink()
                
                logger.info(f"   ☁️ Datos subidos a MinIO (bucket plata)")
            
            logger.info(f"✅ Datos guardados correctamente en PLATA")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando a PLATA: {e}")
            return False
    
    # ================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ================================================
    
    def _descomponer_minuto(self, minuto: str) -> Tuple[int, int, int]:
        """
        Descompone el minuto en base, adicional y exacto.
        
        Args:
            minuto: String como "90+4'"
            
        Returns:
            Tupla (tiempo_base, tiempo_adicional, minuto_exacto)
        """
        tiempo_base = 0
        tiempo_adicional = 0
        
        if minuto:
            minuto = minuto.rstrip("'")
            
            if '+' in minuto:
                base, extra = minuto.split('+')
                tiempo_base = self._safe_int(base)
                tiempo_adicional = self._safe_int(extra)
            else:
                tiempo_base = self._safe_int(minuto)
        
        minuto_exacto = tiempo_base + tiempo_adicional
        return tiempo_base, tiempo_adicional, minuto_exacto
    
    def _detectar_autogol(self, celda_td) -> bool:
        """
        Detecta si un gol es autogol por el color rojo del SVG.
        
        Args:
            celda_td: Celda TD con el jugador
            
        Returns:
            True si es autogol
        """
        svg = celda_td.find("svg")
        if not svg:
            return False
        
        path = svg.find("path")
        if not path:
            return False
        
        style = path.get("style", "")
        fill = path.get("fill", "")
        
        colores_rojo = [
            "rgb(224, 15, 34)",
            "rgb(224,15,34)",
            "#e00f22",
            "red"
        ]
        
        for color_rojo in colores_rojo:
            if color_rojo in style.lower() or color_rojo in fill.lower():
                return True
        
        return False
    
    def _safe_int(self, value: str) -> int:
        """Convierte string a int, retorna 0 si falla."""
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return 0


# ================================================
# FUNCIONES DE CONVENIENCIA
# ================================================

def crear_pipeline(
    minio_storage=None,
    output_dir: Path = Path("./plata"),
    temporada: str = "2025-2026"
) -> ETLPipeline:
    """
    Crea un pipeline ETL con configuración por defecto.
    
    Args:
        minio_storage: Instancia de MedallionStorage
        output_dir: Directorio de salida local
        temporada: Temporada a procesar
        
    Returns:
        Instancia de ETLPipeline
    """
    return ETLPipeline(minio_storage, output_dir, temporada)


if __name__ == "__main__":
    # Test básico
    print("🧪 Test del módulo etl_pipeline")
    print("=" * 60)
    
    # Crear pipeline
    pipeline = crear_pipeline()
    
    print(f"✅ Pipeline creado para temporada {pipeline.temporada}")
    print(f"   Output: {pipeline.output_dir}")
    
    print("\n" + "=" * 60)
    print("💡 Para usar el pipeline:")
    print("   1. Importar: from etl_pipeline import crear_pipeline")
    print("   2. Crear: pipeline = crear_pipeline(minio_storage)")
    print("   3. Ejecutar: results = pipeline.process_season(1001143)")
    print("=" * 60)
