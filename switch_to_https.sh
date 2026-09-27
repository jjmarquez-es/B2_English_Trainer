#!/bin/bash
set -e

echo "=========================================================="
echo "  CONFIGURANDO ENTORNO HTTPS / SSL CON LET'S ENCRYPT"
echo "=========================================================="

# 1. Comprobaciones previas
if [ ! -f "docker-compose.yaml" ] || [ ! -f "api_tracker.py" ] || [ ! -f ".env" ]; then
    echo "[!] Error: Ejecuta este script desde la raíz del proyecto con .env configurado."
    exit 1
fi

# 2. Extraer dominio y correo desde .env
DOMAIN_NAME=$(grep -E '^DOMAIN_NAME=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')
CERTBOT_EMAIL=$(grep -E '^CERTBOT_EMAIL=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')

if [ -z "$DOMAIN_NAME" ] || [ "$DOMAIN_NAME" = "tu-dominio.com" ]; then
    echo "[!] Error: Define un DOMAIN_NAME válido en tu archivo .env antes de continuar."
    exit 1
fi

if [ -z "$CERTBOT_EMAIL" ] || [ "$CERTBOT_EMAIL" = "admin@tu-dominio.com" ]; then
    echo "[!] Error: Define un CERTBOT_EMAIL real en tu archivo .env para Let's Encrypt."
    exit 1
fi

echo "[*] Dominio detectado: $DOMAIN_NAME"
echo "[*] Correo de contacto: $CERTBOT_EMAIL"

# 3. Asegurar directorios de trabajo
mkdir -p html/generated_audio certbot/conf certbot/www backups data

# 4. Reactivar cookie segura en api_tracker.py
echo "[1/5] Reactivando cookies seguras (secure=True) en api_tracker.py..."
sed -i 's/secure=False/secure=True/g' api_tracker.py

# 5. Escribir docker-compose.yaml con servicio Certbot y puerto 443
echo "[2/5] Configurando docker-compose.yaml con soporte SSL y Certbot..."
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
      - "443:443"
    volumes:
      - ./html:/usr/share/nginx/html:ro
      - ./generated_audio:/usr/share/nginx/html/generated_audio:ro
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - api
    networks:
      - english_net

  certbot:
    image: certbot/certbot
    container_name: english_certbot_gh
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12d & wait $${!}; done;'"

networks:
  english_net:
    driver: bridge
EOF

# 6. Escribir nginx.conf adaptado al dominio
echo "[3/5] Generando nginx.conf con redirección HTTPS y proxy SSL..."
cat << EOF > nginx.conf
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

    # Redirección HTTP a HTTPS y reto Let's Encrypt
    server {
        listen 80;
        listen [::]:80;
        server_name $DOMAIN_NAME;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://\$host\$request_uri;
        }
    }

    # Servidor Seguro HTTPS
    server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        server_name $DOMAIN_NAME;

        ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers off;

        # Frontend estático
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files \$uri \$uri/ /index.html;
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
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF

# 7. Comprobación y emisión de certificados SSL
CERT_PATH="certbot/conf/live/${DOMAIN_NAME}/fullchain.pem"
if [ ! -f "$CERT_PATH" ]; then
    echo "[4/5] No se detectó certificado SSL previo. Generando certificado temporal para bootstrap..."
    mkdir -p "certbot/conf/live/${DOMAIN_NAME}"
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "certbot/conf/live/${DOMAIN_NAME}/privkey.pem" \
        -out "certbot/conf/live/${DOMAIN_NAME}/fullchain.pem" \
        -subj "/CN=localhost" 2>/dev/null

    echo "[*] Arrancando Nginx preliminar para validar reto ACME..."
    docker compose down 2>/dev/null || true
    docker compose up -d web

    echo "[*] Solicitando certificado oficial a Let's Encrypt..."
    docker compose run --rm --entrypoint certbot certbot certonly --webroot \
        --webroot-path=/var/www/certbot \
        --email "$CERTBOT_EMAIL" \
        --agree-tos \
        --no-eff-email \
        --preferred-challenges http \
        -d "$DOMAIN_NAME"
else
    echo "[4/5] Certificado SSL existente detectado para $DOMAIN_NAME."
fi

# 8. Reinicio final con la infraestructura completa
echo "[5/5] Recreando stack en segundo plano con soporte HTTPS..."
docker compose down
docker compose up -d --build

echo "=========================================================="
echo "  SISTEMA OPERATIVO EN MODO HTTPS: https://$DOMAIN_NAME"
echo "=========================================================="
