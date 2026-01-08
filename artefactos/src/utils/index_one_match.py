# test_index_one_match.py
import sys

from core.oro_translation_pipeline import OroTranslationPipeline, OroConfig
import pandas as pd
import json

# Config
config = OroConfig(batch_size=20)
pipeline = OroTranslationPipeline(config)

# Cargar eventos
response = pipeline.minio_client.get_object(
    Bucket='plata',
    Key='eventos/2025-2026/eventos_consolidado.json'
)

eventos_todos = json.loads(response['Body'].read().decode('utf-8'))

# Filtrar UN partido
MATCH_ID_TEST = 10891  # Tiene 19 eventos
eventos_partido = [e for e in eventos_todos if e['match_id'] == MATCH_ID_TEST]
df_eventos = pd.DataFrame(eventos_partido)

print(f"📊 Match {MATCH_ID_TEST}: {len(df_eventos)} eventos")

# Traducir
eventos_traducidos = pipeline.process_eventos_batch(df_eventos, batch_size=10)

# Indexar (append mode)
if pipeline.load_existing_index():
    print("📚 Agregando a índice existente...")
    pipeline.append_to_vector_index(eventos_traducidos)
else:
    print("📚 Creando índice nuevo...")
    pipeline.create_vector_index(eventos_traducidos)

print(f"✅ Match {MATCH_ID_TEST} indexado ({len(eventos_traducidos)} eventos)")