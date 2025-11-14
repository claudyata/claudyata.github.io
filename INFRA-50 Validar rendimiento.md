# Configuración Python con GPU


## INFRA-50: Validar rendimiento

**Descripción:** 
Cómo estudiante, quiero realizar pruebas básicas de rendimiento en GPU para asegurar que la configuración cumple con los requisitos esperados antes del despliegue del agente.

**Objetivo:** 
Detectar y solucionar posibles cuellos de botella en la infraestructura, asegurando un desempeño adecuado.



## 3. Instalación de dependencias adicionales

Una vez instalado JetPack, se deben añadir los paquetes necesarios para el desarrollo de *Cl@udiata*:

```bash
sudo apt update && sudo apt upgrade -y
python3 -m pip install --upgrade pip setuptools wheel
sudo apt install -y python3-pip python3-setuptools python3-wheel python3-dev git
sudo apt install python3-opencv python3-numpy python3-pandas -y
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
pip cache purge
python3 -m pip install --upgrade pip setuptools wheel
pip install transformers scikit-learn fastapi uvicorn
sudo apt-get install python3-pip libopenblas-base libopenmpi-dev

```

                3. Configuración del entorno de desarrollo
                Editor recomendado: Visual Studio Code (con extensión Remote-SSH para conexión al Jetson).

                Control de versiones: Git + GitHub para sincronizar el código fuente.

                Entornos virtuales: Uso de venv o conda (Miniforge ARM) para aislar dependencias del proyecto.

                Monitorización: tegrastats para supervisar temperatura, uso de GPU y consumo energético.

                Seguridad: Usuario sin privilegios root, autenticación SSH y firewall UFW habilitado.

1. Validación del entorno
Antes de iniciar el desarrollo, se recomienda ejecutar los siguientes comandos de validación:

bash
Copiar código
# Verificar versión de CUDA
nvcc --version

# Verificar soporte de TensorRT
dpkg -l | grep tensorrt

# Probar ejecución en GPU
python3 -c "import torch; print(torch.cuda.is_available())"
El sistema estará correctamente configurado si la GPU es reconocida por CUDA y PyTorch, y si TensorRT está instalado correctamente.

5. Conclusión
La correcta configuración del entorno Linux en el NVIDIA Jetson AGX Orin Developer Kit garantiza que el agente Cl@udiata disponga de una plataforma sólida, eficiente y escalable para el desarrollo y despliegue de modelos de lenguaje y análisis de vídeo.

Con esta infraestructura:

Se asegura la compatibilidad con los principales frameworks de IA.

Se optimiza la inferencia mediante TensorRT y CUDA.

Se mantiene una arquitectura sostenible, de bajo consumo y lista para la experimentación en entornos locales.

📦 Resultado esperado:
Un entorno de trabajo completamente funcional y optimizado, listo para la ejecución del agente generativo Cl@udiata en el dispositivo Jetson AGX Orin.