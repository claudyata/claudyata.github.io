import torch
import time

# Crear tensores grandes
size = 8192
a = torch.randn(size, size).cuda().half()  # FP16
b = torch.randn(size, size).cuda().half()

# Calentar GPU
for _ in range(10):
    c = torch.matmul(a, b)
torch.cuda.synchronize()

# Medir
iterations = 100
start = time.time()

for _ in range(iterations):
    c = torch.matmul(a, b)
    
torch.cuda.synchronize()
elapsed = time.time() - start

# Calcular FLOPS
# Multiplicación de matrices: 2 × N³ operaciones
flops_per_iter = 2 * size**3
total_flops = flops_per_iter * iterations
tflops = (total_flops / elapsed) / 1e12

print(f"TFLOPS alcanzados: {tflops:.2f}")
print(f"Eficiencia vs pico (275 TFLOPS): {tflops/275*100:.1f}%")