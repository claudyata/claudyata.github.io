"""
Test de velocidad de generación
"""

from core.nlp_analyzer import create_nlp_analyzer
import time

analyzer = create_nlp_analyzer()

match_id = 10891
idioma = 'es'

print(f"🚀 Generando resumen con streaming...")
print(f"Match: {match_id}, Idioma: {idioma}\n")

stream_gen = analyzer.generar_resumen_partido(
    match_id=match_id,
    verbose=False,
    stream=True,
    idioma=idioma
)

tokens_historia = []

for chunk in stream_gen:
    if chunk['type'] == 'metadata':
        print(f"📊 Metadata recibida")
        print(f"   Eventos: {chunk['num_eventos']}")
        print(f"\n⏱️  Monitoreando velocidad...\n")
    
    elif chunk['type'] == 'token':
        tok_s = chunk.get('tokens_por_segundo', 0)
        tokens = chunk['tokens_generados']
        
        tokens_historia.append({
            'tokens': tokens,
            'tok_s': tok_s,
            'tiempo': chunk.get('tiempo_transcurrido', 0)
        })
        
        # Mostrar cada 10 tokens
        if tokens % 10 == 0:
            print(f"Token {tokens:3d}: {tok_s:5.1f} tok/s")
    
    elif chunk['type'] == 'final':
        print(f"\n✅ Completado!")
        print(f"   Total tokens: {chunk['tokens_generados']}")
        print(f"   Velocidad promedio: {chunk['tokens_por_segundo']:.1f} tok/s")
        print(f"   Tiempo generación: {chunk['tiempo_generacion']:.2f}s")
        print(f"   Tiempo total: {chunk['tiempo_total']:.2f}s")

# Análisis
if tokens_historia:
    import pandas as pd
    
    df = pd.DataFrame(tokens_historia)
    
    print(f"\n📊 Estadísticas:")
    print(f"   Min: {df['tok_s'].min():.1f} tok/s")
    print(f"   Max: {df['tok_s'].max():.1f} tok/s")
    print(f"   Media: {df['tok_s'].mean():.1f} tok/s")
    print(f"   Mediana: {df['tok_s'].median():.1f} tok/s")