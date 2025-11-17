# Configuración Python con GPU

Este documento describe la planificación del almacenamiento histórico de datos y la configuración del entorno Python con soporte de GPU para el **TFG** y para que nuestro **agente** pueda procesar los datos de manera eficiente.

---

## INFRA-30: Configurar entorno Python con GPU

**Descripción:**  
Como estudiante, quiero que Python esté configurado con el uso de GPU para facilitar el desarrollo y la ejecución de todas las tareas del TFG.

**Objetivo:**  
Permitir que los procesos en Python aprovechen la GPU, mejorando el rendimiento del agente y reduciendo los tiempos de procesamiento de grandes volúmenes de datos de nuestros pipeplines.

---


## 3. Instalación de dependencias adicionales

Una vez instalado JetPack, se deben añadir los paquetes necesarios para el desarrollo de **Cl@udiata**:

https://developer.nvidia.com/cuda-12-6-0-download-archive?target_os=Linux&target_arch=aarch64-jetson&Compilation=Native&Distribution=Ubuntu&target_version=22.04&target_type=deb_local

https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html

https://forums.developer.nvidia.com/t/torch-on-jetson-jetpack-6-2/322770

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


sudo python3 -m pip install --no-cache https://developer.download.nvidia.com/compute/redist/jp/v60dp/pytorch/torch-2.3.0a0+6ddf5cf85e.nv24.04.14026654-cp310-cp310-linux_aarch64.whl


sudo python3 -m pip install --no-cache https://developer.download.nvidia.com/compute/redist/jp/v60dp/tensorflow/tensorflow-2.15.0+nv24.04-cp310-cp310-linux_aarch64.whl

python3 -m pip uninstall torch torchvision torchaudio -y
python3 -m pip cache purge
python3 -m pip install --pre torch torchvision torchaudio --extra-index-url https://pypi.jetson-ai-lab.dev/jp6/cu126

https://docs.nvidia.com/deeplearning/frameworks/install-tf-jetson-platform/index.html
https://www.jetson-ai-lab.com/tensorrt_llm.html
https://nvidia.github.io/TensorRT-LLM/reference/support-matrix.html
https://github.com/NVIDIA/TensorRT-LLM/blob/v0.12.0-jetson/README4Jetson.md


Requirement already satisfied: mdurl~=0.1 in /home/claudia/.local/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->nvidia-modelopt~=0.15.0->tensorrt-llm==0.12.0) (0.1.2)
Installing collected packages: tensorrt-llm
  WARNING: The scripts trtllm-bench, trtllm-build, trtllm-prune and trtllm-refit are installed in '/home/claudia/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed tensorrt-llm-0.12.0
cla

claudia@ubuntu:~/TensorRT-LLM$ echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc

export PATH=/home/claudia/.local/bin:$PATH


claudia@ubuntu:~/TensorRT-LLM$ source ~/.bashrc



sudo apt update
sudo apt install python3-pip libhdf5-serial-dev hdf5-tools zlib1g-dev zip libjpeg-dev libpng-dev
pip install --upgrade pip

# remove a possible CPU-only install

pip uninstall -y tensorflow
 
# RHEL 9 default Python 3.9, GPU wheel with embedded CUDA 12.4 / cuDNN 9.1

python -m pip install --upgrade pip
python -m pip install "tensorflow[and-cuda]==2.19.1"
 
# clean out the CPU build

pip uninstall -y tensorflow

# GPU-enabled wheel + all NVIDIA runtimes (CUDA 12.4, cuDNN 9.1)

pip install "tensorflow[and-cuda]==2.19.0"
pip install "tensorflow[and-cuda]==2.19.0"

 
import torch, platform
print("torch", torch.__version__, "python", platform.python_version())
print("GPU count:", torch.cuda.device_count())
print("Name:", torch.cuda.get_device_name(0) if torch.cuda.device_count() else "n/a")


python -m pip install --index-url https://download.pytorch.org/whl/cu126 torch==2.7.1


    1  nvcc --version
    2  python3 --version
    3  nvidia-smi
    4  df -h
    5  sudo nvpmodel -m 0
    6  sudo jetson_clocks
    7  sudo apt-get update
    8  sudo apt-get install -y python3-pip libopenblas-dev git-lfs ccache
    9  wget https://raw.githubusercontent.com/pytorch/pytorch/9b424aac1d70f360479dd919d6b7933b5a9181ac/.ci/docker/common/install_cusparselt.sh
   10  export CUDA_VERSION=12.6
   11  sudo -E bash ./install_cusparselt.sh
   12  python3 -m pip install numpy=='1.26.1'
   13  git clone https://github.com/NVIDIA/TensorRT-LLM.git
   14  cd TensorRT-LLM
   15  git checkout v0.12.0-jetson
   16  git lfs pull
   17  python3 scripts/build_wheel.py --clean --cuda_architectures 87 -DENABLE_MULTI_DEVICE=0 --build_type Release --benchmarks --use_ccache
   18  pip install build/tensorrt_llm-*.whl
   19  echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
   20  source ~/.bashrc
   21  git clone https://huggingface.co/MaziyarPanahi/Meta-Llama-3-8B-Instruct-GPTQ
   22  python convert_checkpoint.py --model_dir Meta-Llama-3-8B-Instruct-GPTQ --output_dir tllm_checkpoint_1gpu_gptq --dtype float16 --use_weight_only --weight_only_precision int4_gptq  --per_group
   23  ls /home/claudia/.local/bin
   24  python3 convert_checkpoint.py --model_dir Meta-Llama-3-8B-Instruct-GPTQ --output_dir tllm_checkpoint_1gpu_gptq --dtype float16 --use_weight_only --weight_only_precision int4_gptq  --per_group
   25  ls
   26  python3 -c "import tensorrt_llm; print(tensorrt_llm.__version__)"
   27  which trtllm-build
   28  trtllm-build   --model-dir Meta-Llama-3-8B-Instruct-GPTQ   --output-dir tllm_checkpoint_1gpu_gptq   --dtype float16   --weight-only   --weight-only-precision int4_gptq   --per-group
   29  ls scripts
   30  python3 ./examples/dit/convert_checkpoint.py --model_dir Meta-Llama-3-8B-Instruct-GPTQ --output_dir tllm_checkpoint_1gpu_gptq --dtype float16 --use_weight_only --weight_only_precision int4_gptq  --per_group
   31  python3 -m pip install --upgrade cuda-python
   32  python3 -c "from cuda import cudart; print(cudart.cudaRuntimeGetVersion())"
   33  sudo apt install python3-pycuda
   34  sudo apt update
   35  nvidia-smi
   36  sudo tegrastats
   37  import pycuda.driver as drv
   38  sudo apt install -y python3-dev python3-pip build-essential libcuda1-540.4.0 libcuda-dev freeglut3-dev libboost-python-dev git
   39  sudo apt install -y python3-dev python3-pip build-essential libcuda1-540 libcuda-dev freeglut3-dev libboost-python-dev git
   40  sudo apt install -y python3-dev python3-pip build-essential freeglut3-dev libboost-python-dev git
   41  git clone https://github.com/inducer/pycuda.git
   42  cd pycuda
   43  cd ..
   44  git clone https://github.com/inducer/pycuda.git
   45  cd pycuda
   46  python3 configure.py
   47  python3 -m pip install .
   48  cd TensorRT-LLM
   49  history


 
```

1. Validación del entorno
Antes de iniciar el desarrollo, se recomienda ejecutar los siguientes comandos de validación:

```bash
# Verificar versión de CUDA
nvcc --version
# Verificar soporte de TensorRT
dpkg -l | grep tensorrt
# Probar ejecución en GPU
python3 -c "import torch; print(torch.cuda.is_available())"
```

El sistema estará correctamente configurado si la GPU es reconocida por CUDA y PyTorch, y si TensorRT está instalado correctamente.

Con esta infraestructura:

Se asegura la compatibilidad con los principales frameworks de IA.

Se optimiza la inferencia mediante TensorRT y CUDA.

Se mantiene una arquitectura sostenible, de bajo consumo y lista para la experimentación en entornos locales.

Resultado esperado:
Un entorno de trabajo completamente funcional y optimizado, listo para la ejecución del agente generativo Cl@udiata en el dispositivo Jetson AGX Orin.