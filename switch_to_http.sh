#!/bin/bash
set -e

echo "=========================================================="
echo "  CONFIGURANDO ENTORNO EXCLUSIVO HTTP (SIN HTTPS/SSL)"
echo "=========================================================="

# 1. Comprobar que nos encontramos en la raíz del proyecto
if [ ! -f "docker-compose.yaml" ] || [ ! -f "nginx.conf" ] || [ ! -f "api_tracker.py" ]; then
    echo "[!] Error: Ejecuta este script desde la raíz del proyecto donde están docker-compose.yaml y nginx.conf."
    exit 1
fi

# 2. Respaldar configuración previa
echo "[1/4] Creando copias de respaldo (.bak)..."
cp nginx.conf nginx.conf.bak
cp docker-compose.yaml docker-compose.yaml.bak
cp api_tracker.py api_tracker.py.bak

# 3. Desactivar flag seguro en cookies de sesión (api_tracker.py)
echo "[2/4] Desactivando cookie segura (secure=False) en api_tracker.py..."
sed -i 's/secure=True/secure=False/g' api_tracker.py

# 4. Sobrescribir nginx.conf para puerto 80 plano
echo "[3/4] Generando nginx.conf sin SSL..."
cat << 'EOF' > nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;

    upstream backend_api {
        server api:8001;
    }

    server {
        listen 80;
        server_name _;

        # Frontend estático
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
        }

        # Audios generados
        location /generated_audio/ {
            alias /usr/share/nginx/html/generated_audio/;
            expires 7d;
            add_header Cache-Control "public, no-transform";
        }

        # Proxy inverso FastAPI
        location /api/ {
            proxy_pass http://backend_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 5. Sobrescribir docker-compose.yaml eliminando Certbot y puerto 443
echo "[4/4] Reescribiendo docker-compose.yaml sin Certbot..."
cat << 'EOF' > docker-compose.yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: english_api_gh
    restart: unless-stopped
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ./data:/app/data
      - ./api_tracker.py:/app/api_tracker.py:ro
      - ./generated_audio:/app/generated_audio:rw
    networks:
      - english_net

  web:
    image: nginx:alpine
    container_name: english_web_gh
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
      - ./generated_audio:/usr/share/nginx/html/generated_audio:ro
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api
    networks:
      - english_net

networks:
  english_net:
    driver: bridge
EOF

# 6. Recrear contenedores
echo "Reiniciando servicios Docker en segundo plano..."
docker compose down
docker compose up -d --build

echo "=========================================================="
echo "  SISTEMA OPERATIVO EN MODO HTTP: http://localhost o http://TU_IP"
echo "=========================================================="
