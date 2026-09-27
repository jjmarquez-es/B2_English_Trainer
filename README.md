# Guía de Despliegue y Puesta en Marcha: Neural Deck B2 Trainer

Manual técnico para el despliegue en producción o desarrollo de la plataforma **Neural Deck B2 Trainer** sobre Ubuntu/Debian utilizando Docker, Nginx, FastAPI y SQLite en modo WAL.

---

## 1. Requisitos Previos

* **Sistema Operativo:** Ubuntu 22.04 LTS, 24.04 LTS o Debian 12.
* **Docker Engine & Docker Compose:** Daemon de Docker operativo y plugin `docker compose`.
* **Puertos de Red:**
* Modo HTTPS: Puertos `80/TCP` y `443/TCP` accesibles.


* Modo HTTP: Puerto `80/TCP` accesible.


* **Dominio DNS (Solo para HTTPS):** Registro tipo `A` apuntando a la IP pública del servidor.
* **Motor de Inferencia IA:** Instancia accesible de Ollama local/remota, o API Key válida de proveedores externos (OpenAI, Groq, OpenRouter, DeepSeek).

---

## 2. Clonación y Permisos de Ejecución

Clona el repositorio oficial desde GitHub y accede a la raíz del proyecto:

```bash
git clone https://github.com/jjmarquez-es/B2_English_Trainer.git
cd B2_English_Trainer

```

Asegura los directorios de datos y concede permisos de ejecución a los scripts de automatización:

```bash
mkdir -p html/generated_audio certbot/conf certbot/www backups data[cite: 2]
chmod +x backup.sh seed_all_banks.py switch_to_http.sh switch_to_https.sh[cite: 2]

```

---

## 3. Configuración del Entorno (`.env`)

Copia el archivo de plantilla:

```bash
cp .env.example .env

```

Genera una clave criptográfica Fernet de 32 bytes en Base64 para cifrar los datos SQLite en reposo:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

```

Abre `.env` para editar:

```bash
nano .env

```

Configura tus credenciales maestras y la clave de cifrado generada:

```ini
# --- SEGURIDAD Y ACCESO MAESTRO ---
DB_ENCRYPTION_KEY=PEGA_AQUI_LA_CLAVE_FERNET_GENERADA
DEFAULT_ADMIN_USER=admin
DEFAULT_ADMIN_PASSWORD=zxcvbnm

# --- DOMINIO Y SSL (Requerido solo para modo HTTPS) ---
DOMAIN_NAME=trainer.tu-dominio.com
CERTBOT_EMAIL=admin@tu-dominio.com

```

### Configuración del Proveedor de IA

Configura el bloque de inferencia según el motor de tu elección:

* **Opción A: Ollama Local (Por defecto)**
```ini
AI_PROVIDER=ollama
AI_MODEL=qwen2.5:latest
AI_BASE_URL=http://host.docker.internal:11434
AI_API_KEY=none

```


* **Opción B: OpenAI Oficial**
```ini
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-proj-tu-api-key-de-openai

```


* **Opción C: Groq (Inferencia Ultrarrápida)**
```ini
AI_PROVIDER=custom
AI_MODEL=llama-3.3-70b-versatile
AI_BASE_URL=https://api.groq.com/openai/v1
AI_API_KEY=gsk_tu-api-key-de-groq

```


* **Opción D: OpenRouter (DeepSeek / Claude / Mistral)**
```ini
AI_PROVIDER=custom
AI_MODEL=deepseek/deepseek-chat
AI_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=sk-or-v1-tu-api-key-de-openrouter

```



Protege el archivo contra accesos no autorizados en el host:

```bash
chmod 600 .env

```

---

## 4. Selección del Modo de Despliegue

La plataforma permite conmutar entre **HTTPS seguro con Let's Encrypt** o **HTTP plano para pruebas locales** mediante scripts automatizados que reconfiguran `nginx.conf`, `docker-compose.yaml` y el comportamiento de cookies en `api_tracker.py`.

### Modo A: Despliegue en Producción con HTTPS (Recomendado)

Para servidores públicos con dominio propio:

```bash
./switch_to_https.sh

```

Este script verifica la presencia del certificado, tramita uno con Let's Encrypt si no existe, habilita cookies seguras (`secure=True`) y arranca Nginx en los puertos 80 y 443.

### Modo B: Despliegue Local / Intranet con HTTP (Sin SSL)

Para entornos de desarrollo, IPs directas o pruebas locales sin dominio:

```bash
./switch_to_http.sh

```

*Este script desacopla Certbot, expone exclusivamente el puerto 80, desactiva la obligatoriedad de SSL en cookies (`secure=False`) y levanta el entorno de forma inmediata.*

---

## 5. Verificación de Servicios

Comprueba que los contenedores necesarios estén activos:

```bash
docker compose ps

```

| Modo | Contenedores Activos | Puertos en Host |
| --- | --- | --- |
| **HTTPS** | `english_web`, `english_api`, `english_certbot`<br> | `80->80`, `443->443`<br> |
| **HTTP** | `english_web`, `english_api`<br> | `80->80` |

---

## 6. Inicialización y Sembrado de la Base de Datos

Ejecuta el sembrador maestro dentro del contenedor backend para inyectar los bancos de datos (3.000 transformaciones Use of English, preguntas Speaking y escenarios interactivos):

```bash
docker compose exec api python3 seed_all_banks.py

```

*Si la base de datos es nueva, el script creará automáticamente el usuario administrador con las credenciales definidas en tu `.env` (`admin` / `zxcvbnm`).*

---

## 7. Primer Acceso y Seguridad

1. Accede desde tu navegador al panel de administración:
* **Modo HTTPS:** `[https://trainer.tu-dominio.com/admin_users.html](https://trainer.tu-dominio.com/admin_users.html)`

* **Modo HTTP:** `http://localhost/admin_users.html` o `http://TU_IP/admin_users.html`



2. Inicia sesión con las credenciales predeterminadas (`admin` / `zxcvbnm`).
3. En el formulario **// REGISTRAR NUEVO ACCESO**, crea tu cuenta de administrador definitiva.
4. Cierra la sesión, accede con la cuenta nueva y elimina la cuenta genérica `admin` de la tabla de usuarios.

---

## 8. Copias de Seguridad Automáticas

El script `backup.sh` genera volcados en caliente de SQLite mediante `VACUUM INTO` con una rotación de 14 días.

1. **Comprobación manual:**
```bash
./backup.sh
ls -lh backups/[cite: 2]

```


2. **Programación en `crontab`:**
Abre el programador de tareas del host:
```bash
crontab -e

```


Añade la ejecución automática a las 03:30 AM (reemplaza `/home/TU_USUARIO` por la ruta absoluta a tu directorio):
```cron
30 3 * * * /home/TU_USUARIO/B2_English_Trainer/backup.sh >> /home/TU_USUARIO/B2_English_Trainer/backups/backup.log 2>&1

```



---

## 9. Restauración ante Desastres

Para restaurar una copia previa en caso de incidente:

1. Detén el contenedor de la API:
```bash
docker compose stop api

```


2. Limpia los archivos WAL residuales:
```bash
rm -f data/neural_deck.db-wal data/neural_deck.db-shm

```


3. Restaura el archivo de volcado sobre la base de datos principal:
```bash
gunzip -c backups/neural_deck_AAAAMMDD_HHMMSS.db.gz > data/neural_deck.db[cite: 2]

```


4. Vuelve a iniciar el contenedor:
```bash
docker compose start api

```
