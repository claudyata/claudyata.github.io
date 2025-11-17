# BUILD_TF_JETSON.md

# Instalación de TensorFlow con soporte CUDA y TensorRT en Jetson Orin

## 1. Preparación del entorno

```bash
source ~/tf_venv/bin/activate
```

Clonar TensorFlow (si no lo has hecho):

```bash
git clone https://github.com/tensorflow/tensorflow.git
cd tensorflow
```

## 2. Configuración de TensorFlow

Eliminar configuraciones previas:

```bash
rm -rf ~/.tf_configure.bazelrc
```

Configurar TensorFlow:

```bash
./configure
```

Responde a las preguntas:

* Python: `/home/claudia/tf_venv/bin/python3`
* ROCm support: `N`
* CUDA support: `Y`
* TensorRT support: `Y`
* CUDA compute capabilities: `sm_87`
* Use clang as CUDA compiler: `N`
* GCC host compiler: `/usr/bin/gcc`
* Optimization flags: `-Wno-sign-compare`
* Android builds: `N`

## 3. Preparar TensorRT en Jetson Orin

Crear enlaces simbólicos para los headers de TensorRT:

```bash
sudo ln -s /usr/src/jetson_multimedia_api/include/NvUtils.h /usr/include/aarch64-linux-gnu/NvUtils.h
sudo ln -s /usr/src/jetson_multimedia_api/include/* /usr/include/aarch64-linux-gnu/
```

## 4. Compilar TensorFlow

```bash
bazel build --config=opt --config=cuda //tensorflow/tools/pip_package:build_pip_package
```

Generar el paquete pip:

```bash
./bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/tensorflow_pkg
```

Instalar el paquete:

```bash
pip install /tmp/tensorflow_pkg/tensorflow-*.whl
```

## 5. Verificar CUDA y cuDNN

Verificar la GPU:

```bash
/usr/local/cuda-samples/build_utils/deviceQuery/deviceQuery
```

Verificar versión de cuDNN:

```bash
cat /usr/include/cudnn_version.h | grep CUDNN_MAJOR -A 2
```
