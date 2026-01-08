"""
Benchmark Q4 vs Q5 - Qwen2.5 32B
Comparar INT4 vs INT5 (no hay FP16 disponible)
"""

import ollama
import time

MODELS = [
    ("qwen2.5:32b", "Q4_K_M (INT4)", "El modelo base ya está cuantizado"),
    ("qwen2.5:32b-instruct-q5_K_M", "Q5_K_M (INT5)", "Cuantización 5-bit"),
]

PROMPT = "Explain the offside rule in football in exactly 50 words"
NUM_TOKENS = 100

def benchmark_model(model_name, precision, description):
    print(f"\n{'='*70}")
    print(f"🧪 Testing: {model_name}")
    print(f"   Cuantización: {precision}")
    print(f"{'='*70}")
    
    # Warmup
    print("🔥 Warming up...")
    for _ in range(2):
        _ = ollama.generate(model=model_name, prompt="Hi", options={'num_predict': 10})
    
    # Benchmark
    print("⏱️  Benchmarking...")
    tokens = 0
    start = time.time()
    first_token = None
    response = ""
    
    stream = ollama.generate(
        model=model_name,
        prompt=PROMPT,
        stream=True,
        options={'num_predict': NUM_TOKENS, 'temperature': 0.7}
    )
    
    for chunk in stream:
        if first_token is None:
            first_token = time.time() - start
        if 'response' in chunk:
            response += chunk['response']
            tokens += 1
    
    total = time.time() - start
    gen_time = total - first_token
    tps = tokens / gen_time if gen_time > 0 else 0
    
    print(f"\n📊 Resultados:")
    print(f"   Tokens/s:           {tps:.2f}")
    print(f"   Latencia 1er token: {first_token:.3f}s")
    print(f"   Tokens generados:   {tokens}")
    
    return {
        'model': model_name,
        'precision': precision,
        'tps': tps,
        'first_token': first_token,
        'tokens': tokens
    }

def main():
    print("="*70)
    print("🚀 BENCHMARK Q4 vs Q5 - QWEN2.5 32B")
    print("="*70)
    
    results = []
    for model, prec, desc in MODELS:
        r = benchmark_model(model, prec, desc)
        if r:
            results.append(r)
        time.sleep(2)
    
    # Comparación
    print("\n" + "="*70)
    print("📊 COMPARACIÓN")
    print("="*70)
    
    if len(results) == 2:
        q4_tps = results[0]['tps']
        q5_tps = results[1]['tps']
        diff = ((q5_tps / q4_tps) - 1) * 100
        
        print(f"\n{'Modelo':<35} {'Cuantización':<15} {'Tokens/s':<12} {'Diferencia'}")
        print("-"*70)
        print(f"{results[0]['model']:<35} {results[0]['precision']:<15} {q4_tps:<12.2f} baseline")
        print(f"{results[1]['model']:<35} {results[1]['precision']:<15} {q5_tps:<12.2f} {diff:+.1f}%")
        
        print("\n💡 CONCLUSIÓN:")
        if abs(diff) < 5:
            print(f"   Q4 y Q5 tienen rendimiento similar ({abs(diff):.1f}% diferencia)")
            print(f"   ✅ Q4_K_M recomendado: menor tamaño, misma velocidad")
        elif diff > 0:
            print(f"   Q5 es {diff:.1f}% más rápido que Q4")
            print(f"   ⚖️  Trade-off: Q5 usa más memoria (+4GB)")
        else:
            print(f"   Q4 es {abs(diff):.1f}% más rápido que Q5")
            print(f"   ✅ Q4_K_M recomendado: más rápido y más compacto")

if __name__ == "__main__":
    main()