# Diseño de la tarea: INFRA-40: Configurar un sistema de almacenamiento distribuido de objetos, altamente escalable y compatible con S3.

Este documento describe la tarea **[INFRA-40]** dentro del proyecto **Cl@udiata: Modelos de Lenguaje en la Analítica Deportiva**.  
Incluye la descripción, objetivos, procedimientos, verificación y resultados esperados para que otros estudiantes puedan reproducir el trabajo en su entorno.

---

## Tabla de contenidos
1. [Descripción y Objetivo](#1-descripción-y-objetivo)  
2. [Requisitos / Contexto](#2-requisitos--contexto)  
3. [Procedimiento de instalación y configuración](#3-procedimiento-de-instalación-y-configuración)  
4. [Validación del entorno (Checkpoints)](#4-validación-del-entorno-checkpoints)  
5. [Riesgos / Bloqueos](#5-riesgos--bloqueos)  
6. [Conclusión](#6-conclusión)  
7. [Referencias](# 11. Referencias)

---

## 1. Descripción y Objetivo

# Instalación de MinIO en NVIDIA Jetson AGX

Este documento describe paso a paso cómo instalar y configurar **MinIO** en nuestro dispositivo **NVIDIA Jetson AGX**.

**Descripción:**  
Como estudiante, quiero configurar un sistema de almacenamiento distribuido utilizando MinIO para gestionar el ciclo de vida de los datos en, de manera segura, mediante una estructura medallón (Bronze, Silver, Gold), que permita la colaboración entre nodos o equipos.

**Objetivo:**  
Garantizar una transferencia y almacenamiento seguro de los datos, permitiendo un acceso organizado y controlado, de manera que los datos en crudo, transformados y finales estén disponibles para procesamiento y análisis sin comprometer la seguridad de la información.

---

## 2. Requisitos / Contexto

## 3. Procedimiento de instalación y configuración

1. Descargar el binario de MinIO para Linux ARM64 (compatible con Jetson AGX):

```bash
wget https://dl.min.io/server/minio/release/linux-arm64/minio
```

2. Dar permisos de ejecución:

```bash
chmod +x minio
```

3. Mover el binario a /usr/local/bin:

```bash
sudo mv minio /usr/local/bin/
```

3. Verificar la instalación:
```bash
minio --version
```

4. Deberías ver algo como:

```bash
minio version RELEASE.2025-09-07T16-13-09Z (commit-id=07c3a429bfed433e49018cb0f78a52145d4bedeb)
Runtime: go1.24.6 linux/arm64
License: GNU AGPLv3 - https://www.gnu.org/licenses/agpl-3.0.html
Copyright: 2015-2025 MinIO, Inc.
```

## 4. Configuración de credenciales

Asignar permisos al usuario que correrá el servicio:

```bash
sudo mkdir /usr/local/share/minio
sudo chown -R claudia:claudia /usr/local/share/minio
sudo chmod -R u+rwX /usr/local/share/minio
```

Crear el archivo /etc/default/minio con las credenciales:

```bash
sudo vi /etc/default/minio
```

Añadir el contendio:
```bash
# Archivo de configuración de MinIO
# ---------------------------------

# Directorio de datos (estructura medallón)
MINIO_VOLUMES="/usr/local/share/minio"

# Credenciales de acceso
MINIO_ROOT_USER=minioclaudia
MINIO_ROOT_PASSWORD=minioclaudia

# Configuración de red
#MINIO_SERVER_URL="http://192.168.178.84:9000"
```
Crear el volumen raíz:

```bash
sudo mkdir -p /usr/local/share/minio
```

## 5. Arrancar MinIO como servicio systemd

Crear el archivo /etc/systemd/system/minio.service:
```bash
sudo vi /etc/systemd/system/minio.service
```

Añadir el contendio:
```ini
[Unit]
Description=MinIO
Documentation=https://min.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
User=claudia
Group=root
EnvironmentFile=/etc/default/minio
ExecStart=/usr/local/bin/minio server $MINIO_VOLUMES --address :9000
Restart=always
LimitNOFILE=65536
TimeoutStopSec=30s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Recargar systemd y arrancar el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio
sudo systemctl status minio
```

Tendras que ver algo así:

```bash
● minio.service - MinIO
     Loaded: loaded (/etc/systemd/system/minio.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-10-13 11:22:16 UTC; 20ms ago
       Docs: https://min.io/docs/
   Main PID: 10614 (minio)
      Tasks: 8 (limit: 74767)
     Memory: 13.9M
        CPU: 18ms
     CGroup: /system.slice/minio.service
             └─10614 /usr/local/bin/minio server /usr/local/share/minio --address :9000

oct 13 11:22:16 ubuntu systemd[1]: Started MinIO.
```

## 6. Configuración de AWS CLI y Python boto3 en NVIDIA Jetson AGX

Debido a que MinIO es compatible con la API de S3 de AWS, vamos a aprovechar esa compatibilidad para instalar y probar **AWS CLI** y **Python boto3** y así manipular buckets S3 en MinIO de nuesta Jetson.

1. Instalar AWS CLI

AWS CLI permite administrar servicios S3 (o MinIO con compatibilidad S3) desde la terminal.

Instalación:

```bash
pip3 install --user awscli --upgrade
```

Verifica la instalación:

```bash
export PATH=$HOME/.local/bin:$PATH
aws --version
```

Deberías ver algo como:

```bash
aws-cli/1.42.74 Python/3.12.12 Linux/5.15.148-tegra botocore/1.40.74
```

2. Configurar credenciales para MinIO
Configura el cliente AWS CLI para apuntar a tu servidor MinIO.

```bash
sudo mkdir ~/.aws/
sudo vi ~/.aws/credentials
```

Contenido:
```ini
[minio]
aws_access_key_id = minioclaudia
aws_secret_access_key = minioclaudia
```

Estos valores deben coincidir con tus variables MINIO_ROOT_USER y MINIO_ROOT_PASSWORD.

3. Crear archivo de configuración S3 personalizado
AWS CLI usa por defecto los endpoints de AWS.
Para usarlo con MinIO, debemos definir un endpoint local.

Edita el archivo de configuración de AWS:

```bash
vi ~/.aws/config
```

Contenido:

```ini
[profile minio]
region = us-east-1
output = json
s3 =
    endpoint_url = http://192.168.178.84:9000
```

4. Probar conexión a MinIO usando AWS CLI
Lista todos los buckets en MinIO:

```bash
aws --endpoint-url http://192.168.1.22:9000 s3 ls --profile minio
```

5. Instalar Python boto3

boto3 es la librería oficial de AWS para interactuar con S3 desde Python.

Instalación:
```bash
pip3 install boto3
```

Verifica que está instalado:
```bash
python3 -m pip show boto3
```

Si todo está bien, verás algo como:

```yaml
Name: boto3
Version: 1.40.74
Summary: The AWS SDK for Python
Home-page: https://github.com/boto/boto3
Author: Amazon Web Services
Author-email:
License: Apache License 2.0
Location: /home/claudia/.local/lib/python3.10/site-packages
Requires: botocore, jmespath, s3transfer
Required-by:
```

6. Configurar acceso a MinIO desde Python

1. Crea un script llamado minio_boto3_test.py:

```bash
vi boto3_test.py
```


```python
import boto3


# Configuración de conexión
s3 = boto3.client(
    "s3",
    aws_access_key_id="minioclaudia",
    aws_secret_access_key="minioclaudia",
    endpoint_url="http://192.168.1.22:9000"
)

# Listar buckets
response = s3.list_buckets()
print("Buckets disponibles:")
for bucket in response['Buckets']:
    print(f" - {bucket['Name']}")
```

2. Ejecuta el script:
```bash
python3 boto3_test.py
```

Si todo está correcto, verás la lista de tus buckets MinIO en la consola.

```yaml
Buckets disponibles:
```

## 7. Configurar MinIO Client mc y crear politicas de usuario.

1. Instalar MinIO Client:
```bash
wget https://dl.min.io/client/mc/release/linux-arm64/mc
chmod +x mc
sudo mv mc /usr/local/bin/
```

2. Configurar alias:
```bash
mc alias set local http://192.168.1.22:9000 minioclaudia minioclaudia
```

Si todo está bien, verás algo como:

```yaml

mc: Configuration written to `/home/claudia/.mc/config.json`. Please update your access credentials.
mc: Successfully created `/home/claudia/.mc/share`.
mc: Initialized share uploads `/home/claudia/.mc/share/uploads.json` file.
mc: Initialized share downloads `/home/claudia/.mc/share/downloads.json` file.
Added `local` successfully.
```

3. Crear usuarios para cada bucket

claudia_bronze → acceso solo al bucket bronze
claudia_silver → acceso solo al bucket silver
claudia_gold → acceso solo al bucket gold

```bash
mc admin user add local claudia_bronze claudia_bronze
mc admin user add local claudia_silver claudia_silver
mc admin user add local claudia_gold claudia_gold
```

4. Crear políticas de acceso para cada bucket

Crea un archivo JSON con la política para cada usuario:

```bash
sudo vi bronze-policy.json
```

Contenido:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::bronze",
        "arn:aws:s3:::bronze/*"
      ]
    }
  ]
}
```

```bash
sudo vi silver-policy.json
```
Contenido:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": ["s3:GetObject","s3:ListBucket"],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::silver",
        "arn:aws:s3:::silver/*"
      ]
    }
  ]
}
```

```bash
sudo vi gold-policy.json
```

Contenido:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": ["s3:GetObject","s3:ListBucket"],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::gold",
        "arn:aws:s3:::gold/*"
      ]
    }
  ]
}
```

5. Asignar la política a cada usuario

```bash
mc admin policy create local bronze-policy bronze-policy.json
mc admin policy create local silver-policy silver-policy.json
mc admin policy create local gold-policy gold-policy.json

mc admin policy attach local bronze-policy --user claudia_bronze
mc admin policy attach local silver-policy --user claudia_silver
mc admin policy attach local gold-policy --user claudia_gold
```

6. Comprobar acceso

```bash
mc alias set bronze http://192.168.1.22:9000 claudia_bronze claudia_bronze
mc ls bronze
```

```yaml
[2025-10-13 11:52:21 UTC]     0B bronze/
```

## 8. Instalación de MinIO Client (mc) en Windows 11

Nos interesa conectar al servidor MinIO instalado en la NVIDIA Jetson AGX y acceder a los buckets definidos desde un host externo.


1. Descargar [MinIO Client](https://www.min.io/download?platform=windows), archivo mc.exe y añadelo al PATH del sistema:
 por ejemplo:

2. Verificar instalación

Ejecuta en PowerShell o CMD:
```bash
mc --version
```

3. Si está correctamente instalado, se mostrará la versión del cliente MinIO.
```yaml
mc version RELEASE.2025-08-29T21-30-41Z (commit-id=f7560841be167a94b7014bf8a504e0820843247f)
Runtime: go1.24.6 windows/amd64
Copyright (c) 2015-2025 MinIO, Inc.
MinIO Enterprise License
```

4. Configurar alias para los buckets

Alias para el bucket Bronze, Silver y Gold
```bash
mc alias set bronze http://192.168.1.22:9000 claudia_bronze claudia_bronze
mc alias set silver http://192.168.1.22:9000 claudia_silver claudia_silver
mc alias set gold http://192.168.1.22:9000 claudia_gold claudia_gold
```

Si todo está bien, verás algo como:
```bash
mc ls bronze
[2025-10-13 13:52:21 CEST]     0B bronze/
mc ls silver
[2025-10-13 13:52:27 CEST]     0B silver/
mc ls gold
[2025-10-13 13:52:31 CEST]     0B gold/
```

## 9. Errores comunes y soluciones al usar MinIO con AWS CLI

Al trabajar con MinIO en NVIDIA Jetson AGX y AWS CLI, es frecuente encontrar algunos errores relacionados con la hora, las credenciales o la conexión al endpoint. Aquí se documentan los más comunes y cómo solucionarlos.

1. Error: date value out of range

**Mensaje de error:**

date value out of range


**Causa:** 
AWS CLI usa Signature V4, que depende de la hora del sistema en UTC. Si la hora de tu MinIO (Jetson) y la del cliente no están sincronizadas, aparece este error.

**Solución:**

Verifica la hora en Jetson y cliente:
```bash
date
timedatectl status
```

Sincroniza la hora con NTP:
```bash
sudo timedatectl set-ntp true
timedatectl status
```

(Opcional) Cambia la zona horaria a UTC:
```bash
sudo timedatectl set-timezone UTC
```

Reinicia MinIO:
```bash
sudo systemctl restart minio
```

Prueba de nuevo AWS CLI:
```bash
aws --profile minio --endpoint-url http://192.168.1.22:9000 s3 ls
```

## 10. Desinstalar MinIO, AWS CLI y configuraciones relacionadas en Ubuntu / Jetson AGX

Esta guía elimina completamente MinIO, AWS CLI (instalaciones por apt y pip) y sus configuraciones asociadas.

---

1. Detener y eliminar MinIO

```bash
# Detener el servicio MinIO
sudo systemctl stop minio
sudo systemctl disable minio
# Verificar estado
sudo systemctl status minio
# Eliminar el archivo de servicio
sudo rm /etc/systemd/system/minio.service
sudo rm /etc/default/minio
# Recargar systemd
sudo systemctl daemon-reload
```
 
2. Eliminar binario de MinIO
```bash
sudo rm /usr/local/bin/minio
```

3. Eliminar directorios de datos y permisos
```bash
sudo rm -rf /usr/local/share/minio
sudo rm -rf /home/claudia/.minio
```

Esto elimina buckets, estructura medallón (bronze/silver/gold) y cualquier configuración local de MinIO.

4. Desinstalar AWS CLI

```bash
pip3 uninstall awscli -y
rm -rf ~/.local/lib/python3.10/site-packages/awscli
sudo rm -f /usr/local/bin/aws
```

Asegúrate de que ~/.local/bin ya no contenga aws:

```bash
rm -f ~/.local/bin/aws
rm -rf ~/aws
```

Verifica que AWS CLI ya no exista:

```bash
which aws
aws --version  
```
Debe decir "command not found"

```bash
-bash: /home/claudia/.local/bin/aws: No such file or directory
```

5. Limpiar configuraciones de AWS CLI
```bash
rm -rf ~/.aws
```

Esto elimina perfiles, credenciales y configuraciones locales de AWS/MinIO.

6. Limpiar MinIO Client (mc) si está instalado
```bash
# Si lo instalaste en /usr/local/bin
sudo rm /usr/local/bin/mc
# Configuración de mc
rm -rf ~/.mc
```

7. Verificación final
```bash
# No debe encontrar MinIO ni AWS CLI
minio
aws
mc
```

## 11. Referencias

- [Documentación oficial MinIO](https://docs.min.io/enterprise/aistor-object-store/)

- [MinIO Client mc](https://docs.min.io/enterprise/aistor-object-store/reference/cli/)

- [Documentación oficial de MinIO SDK](https://docs.min.io/enterprise/aistor-object-store/developers/minio-drivers/)

- [Documentación oficial de AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

- [Documentación oficial de S3](https://docs.aws.amazon.com/s3/)

- [Documentación de boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---


