# Instalación de MinIO en NVIDIA Jetson AGX

Este documento describe paso a paso cómo instalar y configurar **MinIO** en un dispositivo **NVIDIA Jetson AGX**, utilizando una **estructura medallón** (Bronze, Silver, Gold) y un **único volumen** de datos.

---

## 1. Descarga e instalación de MinIO

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

## 2. Crear el usuario dedicado para MinIO (opcional pero recomendado)
```bash
sudo useradd -r minio-app -s /sbin/nologin
```

Este usuario correrá MinIO y tendrá permisos sobre los volúmenes de datos.

## 3. Crear el volumen único y la estructura medallón

Se recomienda usar un único volumen raíz, por ejemplo /usr/local/share/minio, y dentro crear las carpetas bronze/silver/gold:

```bash
sudo mkdir -p /usr/local/share/minio/bronze/raw_pdf
sudo mkdir -p /usr/local/share/minio/bronze/raw_video
sudo mkdir -p /usr/local/share/minio/bronze/raw_html

sudo mkdir -p /usr/local/share/minio/silver/json
sudo mkdir -p /usr/local/share/minio/silver/video

sudo mkdir -p /usr/local/share/minio/gold/reports
```

Asignar permisos al usuario que correrá MinIO:

```bash
sudo chown -R minio-app:minio-app /usr/local/share/minio
sudo chmod -R 750 /usr/local/share/minio
```


## 4. Configuración de credenciales

Se recomienda crear el archivo /etc/default/minio con las credenciales:

```bash
sudo nano /etc/default/minio
```

Contenido:
```bash
# Directorio de datos
MINIO_VOLUMES="/usr/local/share/minio"

# Credenciales de acceso (mínimo 3 caracteres usuario, 8 contraseña)
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=nimda

# Dirección de escucha (opcional)
MINIO_SERVER_URL="http://192.xxx.xxx.xx:9000"
sudo nano /etc/default/minio
```

					## 5. Arrancar MinIO manualmente

					Para probar la instalación sin crear un servicio systemd:
					```bash
					export MINIO_ROOT_USER=admin
					export MINIO_ROOT_PASSWORD=nimda
					/usr/local/bin/minio server /usr/local/share/minio --address :9000
					```

					Esto arrancará MinIO en la terminal actual.

					Se podrá acceder desde el navegador: http://192.xxx.xxx.xx:9000

					Usuario: admin

					Contraseña: nimda

					Para detener MinIO: presiona CTRL+C.

## 6. Arrancar MinIO como servicio systemd (opcional)

Crear el archivo /etc/systemd/system/minio.service:
```ini
[Unit]
Description=MinIO
Documentation=https://min.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
User=minio-app
Group=minio-app
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

Verifica que esté activo:

Active: active (running)

## 7. Crear buckets (opcional, usando MinIO Client mc)

Instalar MinIO Client:
```bash
wget https://dl.min.io/client/mc/release/linux-arm64/mc
chmod +x mc
sudo mv mc /usr/local/bin/
```

Configurar alias:
```bash
mc alias set local http://localhost:9000 claudia minio1234
```

Crear buckets Bronze, Silver y Gold (si no quieres usar las carpetas preexistentes):

mc mb local/bronze
mc mb local/silver
mc mb local/gold

Notas importantes

MinIO requiere un único volumen raíz; no se pueden pasar múltiples subcarpetas como volúmenes independientes.

La estructura medallón (bronze/silver/gold) debe crearse dentro del volumen raíz.

Para producción, siempre se recomienda usar un usuario dedicado (minio-app).

Los permisos del volumen deben permitir lectura/escritura al usuario que ejecuta MinIO.

## 8. Referencias

Documentación oficial MinIO: https://docs.min.io/enterprise/aistor-object-store/

MinIO Client mc: https://docs.min.io/enterprise/aistor-object-store/reference/cli/