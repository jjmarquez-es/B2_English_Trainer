#!/usr/bin/env python3
"""
NEURAL DECK // BACKEND API ROUTER
Gestiona autenticación, perfiles cifrados (AES-256), síntesis Edge-TTS,
ingesta de PDFs, banco de exámenes B2/C1 con persistencia y endpoints de IA.
"""

import os
import re
import json
import time
import base64
import sqlite3
import hashlib
import sys
import secrets
import time

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from cryptography.fernet import Fernet
import httpx
from pypdf import PdfReader
import edge_tts

app = FastAPI(title="Neural Deck API", version="4.1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIO_DIR = os.path.join(BASE_DIR, "generated_audio")
CUSTOM_EXAMS_FILE = os.path.join(DATA_DIR, "custom_exams.json")
ADMIN_USERS = os.getenv("ADMIN_USERS", "spacemans8").split(",")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "neural_deck.db")

# Lectura estricta de secretos ----------------------------- 
RAW_SECRET = os.getenv("DB_ENCRYPTION_KEY")
if not RAW_SECRET:
    # Intentar leer del .env explícito si no está en variables de entorno del sistema
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DB_ENCRYPTION_KEY="):
                    RAW_SECRET = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    break

if not RAW_SECRET or len(RAW_SECRET) < 16:
    sys.exit("[CRITICAL SECURITY ERROR] DB_ENCRYPTION_KEY no configurada o demasiado corta en .env. Abortando.")

# ------------------ SEGURIDAD Y CIFRADO (AES-256) ------------------
RAW_SECRET = os.getenv("DB_ENCRYPTION_KEY", "cyberpunk_default_key_32_bytes_len_secure")
SESSION_COOKIE_NAME = "neural_deck_session"
SESSION_DURATION_SECONDS = 60 * 60 * 24 * 7  # 7 días de validez

def create_session(username: str) -> str:
    """Genera un token seguro y lo registra en la base de datos."""
    token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + SESSION_DURATION_SECONDS

    with get_db() as conn:
        # Purgar sesiones viejas de este usuario o caducadas
        conn.execute("DELETE FROM sessions WHERE expires_at < ? OR username = ?", (now, username))
        conn.execute(
            "INSERT INTO sessions (token, username, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, username, now, expires_at)
        )
        conn.commit()
    return token

def delete_session(token: str):
    """Elimina el token de sesión de la base de datos."""
    if not token:
        return
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()

def get_session_user(token: str) -> str:
    """Verifica el token contra la base de datos y comprueba caducidad."""
    if not token:
        return None
    now = time.time()
    with get_db() as conn:
        row = conn.execute(
            "SELECT username FROM sessions WHERE token = ? AND expires_at > ?",
            (token, now)
        ).fetchone()
        if row:
            return row["username"]
    return None

env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("DB_ENCRYPTION_KEY="):
                RAW_SECRET = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                break

derived_key = base64.urlsafe_b64encode(hashlib.sha256(RAW_SECRET.encode("utf-8")).digest())
cipher = Fernet(derived_key)

def encrypt_val(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return cipher.encrypt(raw).decode("utf-8")

def decrypt_val(token: Optional[str], fallback: Any) -> Any:
    if not token:
        return fallback
    try:
        decrypted = cipher.decrypt(token.encode("utf-8"))
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return fallback

# ------------------ CONFIGURACIÓN DE IA ------------------
AI_DEFAULT_PROVIDER = os.getenv("AI_DEFAULT_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "kalikorpz/glm-4.7-flash:latest")

# ------------------ BANCO DE EXÁMENES OFICIALES B2/C1 ------------------
DEFAULT_EXAM_BANK = [
    {
        "exam_id": "b2_exam_01_urban_nature",
        "title": "B2 Exam 01: Urban Gardening & Sustainable Communities",
        "tasks": {
            "task_1_long_reading": {
                "title": "Task 1 - Long Reading: Greening the Metropolis",
                "reading_text": """### Paragraph 1
Modern urban environments are frequently synonymous with concrete infrastructure, persistent noise, and automotive emissions. Historically, city master plans offered minimal space for the natural world, prioritising industrial growth and vehicular transport over biological corridors. However, environmental architects are progressively re-evaluating this design philosophy by reintroducing vegetation into high-density metropolitan zones.

### Paragraph 2
Among the most effective interventions are vertical installations and rooftop gardens. Vertical structures, commonly known as living walls, incorporate climbing flora and specialized watering modules directly onto external facades and internal lobbies. Simultaneously, building owners are transforming underutilised flat roofs into community plots, agricultural gardens, and outdoor relaxation zones.

### Paragraph 3
The integration of natural spaces within corporate buildings generates substantial wellbeing advantages for employees. Routine contact with foliage lowers heart rates, alleviates cognitive fatigue, and heightens daily productivity. Additionally, lunch-hour gardening groups provide workers with opportunities for interpersonal collaboration outside formal workplace meetings.

### Paragraph 4
From an architectural perspective, urban foliage functions as a passive temperature regulator. Green barriers insulate concrete during colder months and deflect direct sunlight in the summer, curtailing reliance on mechanical heating and air-conditioning units. Furthermore, dense plant networks absorb intense rainfall, diminishing urban runoff during severe storms while establishing welcoming habitats for local birds and pollinators.

### Paragraph 5
Everyday citizens without access to a full private garden can nevertheless participate in metropolitan greening. Simple interventions such as balcony planters, communal window ledges, and climbing vines transform plain brick exteriors into vital ecological waypoints. Small-scale domestic cultivation collectively produces measurable environmental benefits across whole residential quarters.""",
                "title_options": [
                    "A Small-scale initiatives by individual residents",
                    "B Psychological and workplace advantages",
                    "C Economic difficulties in building maintenance",
                    "D The historical lack and return of urban nature",
                    "E Insulation and ecological services of green buildings",
                    "F Typologies of modern architectural plantings"
                ],
                "true_false_statements": [
                    "A Vertical walls can be installed on interior as well as exterior facades.",
                    "B Spending time near greenery correlates with reduced cognitive fatigue.",
                    "C Rooftop plantings increase heating expenses during cold winter months.",
                    "D Modern plant installations help manage municipal rainwater drainage.",
                    "E Private residential gardening requires large tracts of land to succeed.",
                    "F Communal window boxes contribute positively to local biodiversity.",
                    "G Corporate buildings never permit gardening clubs during working days.",
                    "H Dense foliage deflects sunlight, which helps stabilize indoor temperatures."
                ],
                "questions": [
                    {"id": 1, "text": "Paragraph 1 (Choose Title A-F)", "answer": "D"},
                    {"id": 2, "text": "Paragraph 2 (Choose Title A-F)", "answer": "F"},
                    {"id": 3, "text": "Paragraph 3 (Choose Title A-F)", "answer": "B"},
                    {"id": 4, "text": "Paragraph 4 (Choose Title A-F)", "answer": "E"},
                    {"id": 5, "text": "Paragraph 5 (Choose Title A-F)", "answer": "A"},
                    {"id": 6, "text": "True Statement 1 (Choose 5 from A-H)", "answer": "A"},
                    {"id": 7, "text": "True Statement 2", "answer": "B"},
                    {"id": 8, "text": "True Statement 3", "answer": "D"},
                    {"id": 9, "text": "True Statement 4", "answer": "F"},
                    {"id": 10, "text": "True Statement 5", "answer": "H"},
                    {"id": 11, "text": "Modern planners are actively reintroducing [GAP] into densely populated areas.", "answer": "Vegetation"},
                    {"id": 12, "text": "Living walls feature specialized [GAP] attached to building walls.", "answer": "Watering modules"},
                    {"id": 13, "text": "Interacting with nature helps alleviate employee [GAP].", "answer": "Cognitive fatigue"},
                    {"id": 14, "text": "Plant cover reduces structural reliance on [GAP] conditioning equipment.", "answer": "Air"},
                    {"id": 15, "text": "Individual households can support biodiversity using balcony [GAP].", "answer": "Planters"}
                ]
            },
            "task_2_multi_text": {
                "title": "Task 2 - Multi-Text Reading: Literacy, Handwriting & Modern Communication",
                "reading_text": """### Text A: Academic History Extract
Pinpointing the precise epoch when symbolic writing first emerged remains an intricate historical challenge. Primitive pictographic marks frequently blurred the frontier between creative visual depictions and formal linguistic messages. Archaeological expeditions reveal that distinct, disconnected scripts materialized concurrently in several cradle regions, including Mesopotamia, East Asia, and Mesoamerica.

### Text B: Primary School Educator's Reflection
Contemporary classroom dynamics have changed drastically as digital tablets supplant lined exercise books. While typing speed allows pupils to produce extended documents rapidly, fine motor skills and letter-formation discipline are visibly declining. Research demonstrates that the tactile exertion of manual script triggers cognitive recall channels that purely mechanical keystrokes fail to replicate.

### Text C: Forensic Documentation Note
Forensic graphologists assess written specimens to authenticate signatures, verify legal testaments, and occasionally profile behavioural tendencies. Although casual character evaluation from penmanship divides scientific opinion, specialized document analysts deliver critical corroborating evidence in commercial litigation and criminal inquiries concerning falsification.

### Text D: Linguistics Overview
Human graphic communication progressed from representational glyphs to nuanced phonographic alphabets. Whereas ancient pictograms stood for concrete entities, contemporary alphabets associate discrete abstract sounds with arbitrary characters. Nevertheless, simplified symbolic icons remain ubiquitous today, appearing on municipal transit signs and airport terminals to transcend language boundaries.""",
                "questions": [
                    {"id": 16, "text": "Which text explores the cognitive benefits associated with writing by hand?", "answer": "B"},
                    {"id": 17, "text": "Which text touches upon the independent development of scripts worldwide?", "answer": "A"},
                    {"id": 18, "text": "Which text addresses the use of document analysis in legal disputes?", "answer": "C"},
                    {"id": 19, "text": "Which text contrasts pictographic symbols with modern sound-based alphabets?", "answer": "D"},
                    {"id": 20, "text": "Which text describes the declining use of traditional notebooks among students?", "answer": "B"},
                    {"id": 21, "text": "True Statement 1 (Choose 5 from A-H): Early writing was occasionally indistinguishable from artwork.", "answer": "A"},
                    {"id": 22, "text": "True Statement 2: Digital keyboards engage the exact same memory recall pathways as penmanship.", "answer": "C"},
                    {"id": 23, "text": "True Statement 3: Forensic document examiners provide testimony in legal scenarios.", "answer": "D"},
                    {"id": 24, "text": "True Statement 4: Universal pictograms remain in use across international transit networks.", "answer": "F"},
                    {"id": 25, "text": "True Statement 5: Handwriting analysis for character diagnosis receives universal scientific consensus.", "answer": "H"},
                    {"id": 26, "text": "Summary Gap: Early visual markings often blended the line between art and formal [GAP].", "answer": "Messages"},
                    {"id": 27, "text": "Summary Gap: Manual handwriting fosters unique pathways for memory [GAP].", "answer": "Recall"},
                    {"id": 28, "text": "Summary Gap: Scientific opinion remains divided over handwriting for character [GAP].", "answer": "Diagnosis"},
                    {"id": 29, "text": "Summary Gap: Modern alphabets represent spoken sounds rather than concrete [GAP].", "answer": "Entities"},
                    {"id": 30, "text": "Summary Gap: Universal transit signs utilise visual icons to overcome language [GAP].", "answer": "Boundaries"}
                ]
            },
            "task_3_writing": "Article (150-180 words) analyzing whether manual handwriting should still be taught in schools.",
            "task_4_writing": "Essay (150-180 words) debating whether municipal councils should legally require green rooftops."
        }
    }
]

def load_custom_exams() -> List[Dict[str, Any]]:
    if not os.path.exists(CUSTOM_EXAMS_FILE):
        return []
    try:
        with open(CUSTOM_EXAMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_custom_exam(exam_obj: Dict[str, Any]):
    exams = load_custom_exams()
    exams.append(exam_obj)
    with open(CUSTOM_EXAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(exams, f, ensure_ascii=False, indent=2)

# ------------------ PERFILES Y BASE DE DATOS ------------------
import sqlite3
from contextlib import contextmanager

DB_PATH = "/app/data/neural_deck.db"

@contextmanager
def get_db():
    # timeout=10.0 indica al driver de Python que espere hasta 10 segundos antes de lanzar excepción
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    
    # 1. Espera activa de hasta 5000 ms si hay una escritura concurrente en curso
    conn.execute("PRAGMA busy_timeout = 5000")
    
    # 2. Forzar integridad referencial (necesaria para ON DELETE CASCADE en sessions)
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        yield conn
    finally:
        conn.close()

class LoginRequest(BaseModel):
    username: str
    password: str

def hash_password(password: str) -> str:
    return hashlib.sha256((password + RAW_SECRET).encode("utf-8")).hexdigest()

# Actualizar init_db para soportar contraseñas
def init_db():
    with get_db() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        
        # (Aquí va tu código existente de creación de tablas: users, sessions, etc.)
        # ...

        # --- BOOTSTRAP ADMINISTRADOR INICIAL ---
        admin_exists = conn.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        if not admin_exists:
            default_user = os.getenv("DEFAULT_ADMIN_USER", "admin")
            default_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "zxcvbnm")
            now = time.time()
            
            conn.execute("""
                INSERT INTO users (
                    username, role, password_hash, target_date, selected_model,
                    encrypted_targets, encrypted_tracker, encrypted_prompts,
                    encrypted_speaking, encrypted_grammar, theme, updated_at
                ) VALUES (?, 'admin', ?, '2026-10-07', ?, ?, ?, ?, ?, ?, 'cyberpunk', ?)
            """, (
                default_user.strip().lower(),
                hash_password(default_pass),
                OLLAMA_MODEL,
                encrypt_val([]),
                encrypt_val({}),
                encrypt_val([]),
                encrypt_val([]),
                encrypt_val([]),
                now
            ))
            conn.commit()
            print(f"[SECURITY] Base de datos nueva detectada. Creado administrador por defecto: '{default_user}'")

#--------------------------- Administración de Usuarios

from pydantic import BaseModel, Field
import re

# Dependencia de seguridad estricta para administradores
def require_admin(request: Request) -> str:
    username = get_username(request)  # Lanza 401 si no hay sesión válida
    role = get_user_role(username)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado: se requieren permisos de administrador.")
    return username

# Esquemas de entrada
from typing import Literal

class CreateUserPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=100)
    role: Literal["user", "admin"] = "user"

class ResetPasswordPayload(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=100)

# 1. LISTAR USUARIOS (excluyendo hashes de contraseña)
@app.get("/api/admin/users")
def list_users(admin: str = Depends(require_admin)):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT username, role, updated_at 
            FROM users 
            ORDER BY username ASC
        """).fetchall()
        return [
            {
                "username": r["username"],
                "role": r["role"],
                "updated_at": r["updated_at"]
            }
            for r in rows
        ]

# 2. CREAR NUEVO USUARIO
@app.post("/api/admin/users")
def create_user(payload: CreateUserPayload, admin: str = Depends(require_admin)):
    u_name = payload.username.strip().lower()
    
    # Validar caracteres seguros para el nombre de usuario
    if not re.match(r"^[a-z0-9_-]+$", u_name):
        raise HTTPException(status_code=400, detail="El nombre de usuario solo admite letras minúsculas, números, guiones y barras bajas.")

    with get_db() as conn:
        # Comprobar si ya existe
        exists = conn.execute("SELECT 1 FROM users WHERE username = ?", (u_name,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail=f"El usuario '{u_name}' ya existe.")

        # Inicializar blobs cifrados para el nuevo usuario
        now = time.time()
        conn.execute("""
            INSERT INTO users (
                username, role, password_hash, target_date, selected_model,
                encrypted_targets, encrypted_tracker, encrypted_prompts,
                encrypted_speaking, encrypted_grammar, theme, updated_at
            ) VALUES (?, ?, ?, '2026-10-07', ?, ?, ?, ?, ?, ?, 'cyberpunk', ?)
        """, (
            u_name,
            payload.role,
            hash_password(payload.password),
            OLLAMA_MODEL,
            encrypt_val([]),
            encrypt_val({}),
            encrypt_val([]),
            encrypt_val([]),
            encrypt_val([]),
            now
        ))
        conn.commit()

    return {"status": "success", "message": f"Usuario '{u_name}' creado correctamente."}

# 3. ELIMINAR USUARIO Y REVOCAR SUS SESIONES
@app.delete("/api/admin/users/{target_user}")
def delete_user(target_user: str, admin: str = Depends(require_admin)):
    target_user = target_user.strip().lower()

    if target_user == admin.lower():
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta de administrador.")

    with get_db() as conn:
        # Purgar sesiones activas de ese usuario
        conn.execute("DELETE FROM sessions WHERE username = ?", (target_user,))
        # Eliminar usuario
        res = conn.execute("DELETE FROM users WHERE username = ?", (target_user,))
        conn.commit()

        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    return {"status": "success", "message": f"Usuario '{target_user}' eliminado correctamente."}

# 4. RESTABLECER CONTRASEÑA
@app.post("/api/admin/users/{target_user}/reset-password")
def reset_user_password(target_user: str, payload: ResetPasswordPayload, admin: str = Depends(require_admin)):
    target_user = target_user.strip().lower()
    with get_db() as conn:
        res = conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE username = ?",
            (hash_password(payload.new_password), time.time(), target_user)
        )
        # Invalidar todas las sesiones existentes para forzar re-login con la nueva clave
        conn.execute("DELETE FROM sessions WHERE username = ?", (target_user,))
        conn.commit()

        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    return {"status": "success", "message": f"Contraseña actualizada para '{target_user}'."}


class LoginPayload(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
def api_login(payload: LoginPayload, response: Response):
    user = payload.username.strip()
    password = payload.password.strip()

    # 1. Comprobar existencia del usuario
    with get_db() as conn:
        row = conn.execute("SELECT password_hash, role FROM users WHERE username = ?", (user,)).fetchone()
    
    if not row or not row["password_hash"]:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # 2. Validar contraseña
    calculated_hash = hash_password(password)
    if calculated_hash != row["password_hash"]:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # 3. Crear sesión segura en SQLite
    session_token = create_session(user)
    user_role = row["role"] or "user"

    # 4. Establecer cookie HttpOnly protegida
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_DURATION_SECONDS,
        path="/",
        httponly=True,
        samesite="lax",
        secure=True  # Cambiar a True cuando actives HTTPS en el dominio
    )

    return {"status": "success", "username": user, "role": user_role}

@app.post("/api/auth/logout")
def api_logout(request: Request, response: Response):
    # 1. Invalidar token en la base de datos
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(token)

    # 2. Ordenar al navegador la destrucción de la cookie en path="/"
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax"
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value="",
        max_age=0,
        expires=0,
        path="/",
        httponly=True,
        samesite="lax"
    )
    return {"status": "success", "message": "Sesión cerrada correctamente"}

def get_user_role(username: str) -> str:
    if username in ADMIN_USERS:
        return "admin"
    with get_db() as conn:
        row = conn.execute("SELECT role FROM users WHERE username = ?", (username,)).fetchone()
        if row and "role" in row.keys() and row["role"]:
            return row["role"]
    return "user"
        
def get_username(request: Request) -> str:
    # 1. Compatibilidad con Proxy inverso si se usa autenticación en upstream
    user = request.headers.get("X-Remote-User") or request.headers.get("Remote-User")
    if user and user.strip() and user.strip() != "$remote_user":
        return user.strip()

    # 2. Validación de sesión criptográfica vía Cookie
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        username = get_session_user(token)
        if username:
            return username

    # 3. Sin sesión o sesión expirada -> 401 Unauthorized
    raise HTTPException(status_code=401, detail="Sesión no válida o expirada")

def get_user_profile(username: str) -> dict:
    role = get_user_role(username)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            conn.execute("""
                INSERT INTO users (
                    username, role, target_date, selected_model,
                    encrypted_targets, encrypted_tracker,
                    encrypted_prompts, encrypted_speaking, encrypted_grammar,
                    theme, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username, role, "2026-10-07", OLLAMA_MODEL,
                encrypt_val([]), encrypt_val({}), encrypt_val([]), encrypt_val([]), encrypt_val([]),
                "cyberpunk", time.time()
            ))
            conn.commit()
            return {
                "username": username,
                "role": role,
                "target_date": "2026-10-07",
                "selected_model": OLLAMA_MODEL,
                "theme": "cyberpunk",
                "hard_targets": [],
                "daily_tracker": {},
                "custom_prompts": [],
                "custom_speaking": [],
                "custom_grammar": []
            }

        return {
            "username": row["username"],
            "role": role,
            "target_date": row["target_date"] or "2026-10-07",
            "selected_model": row["selected_model"] or OLLAMA_MODEL,
            "theme": row["theme"] if ("theme" in row.keys() and row["theme"]) else "cyberpunk",
            "hard_targets": decrypt_val(row["encrypted_targets"], []),
            "daily_tracker": decrypt_val(row["encrypted_tracker"], {}),
            "custom_prompts": decrypt_val(row["encrypted_prompts"], []),
            "custom_speaking": decrypt_val(row["encrypted_speaking"], []),
            "custom_grammar": decrypt_val(row["encrypted_grammar"] if "encrypted_grammar" in row.keys() else None, [])
        }
    
def save_user_profile(username: str, data: dict):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO users (
                username, target_date, selected_model,
                encrypted_targets, encrypted_tracker,
                encrypted_prompts, encrypted_speaking, encrypted_grammar,
                theme, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                target_date = excluded.target_date,
                selected_model = excluded.selected_model,
                encrypted_targets = excluded.encrypted_targets,
                encrypted_tracker = excluded.encrypted_tracker,
                encrypted_prompts = excluded.encrypted_prompts,
                encrypted_speaking = excluded.encrypted_speaking,
                encrypted_grammar = excluded.encrypted_grammar,
                theme = excluded.theme,
                updated_at = excluded.updated_at
        """, (
            username, data.get("target_date", "2026-10-07"), data.get("selected_model", OLLAMA_MODEL),
            encrypt_val(data.get("hard_targets", [])), encrypt_val(data.get("daily_tracker", {})),
            encrypt_val(data.get("custom_prompts", [])), encrypt_val(data.get("custom_speaking", [])),
            encrypt_val(data.get("custom_grammar", [])), data.get("theme", "cyberpunk"), time.time()
        ))
        conn.commit()

async def require_admin(request: Request):
    user = get_username(request)
    role = get_user_role(user)
    if role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Operación denegada: La generación mediante modelos de IA está restringida a administradores."
        )
    return user

# ------------------ MODELOS DE DATOS ------------------
class UserStateModel(BaseModel):
    username: Optional[str] = None
    target_date: Optional[str] = "2026-10-07"
    selected_model: Optional[str] = "kalikorpz/glm-4.7-flash:latest"
    theme: Optional[str] = "cyberpunk"
    hard_targets: Optional[List[str]] = []
    daily_tracker: Optional[Dict[str, Any]] = {}
    custom_prompts: Optional[List[Dict[str, Any]]] = []
    custom_speaking: Optional[List[Dict[str, Any]]] = []
    custom_grammar: Optional[List[Dict[str, Any]]] = []

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-GB-RyanNeural"
    rate: Optional[str] = "-5%"

# ------------------ ENDPOINTS DE EXÁMENES ------------------
@app.get("/api/exams/bank")
def api_get_exam_bank():
    return {"exams": DEFAULT_EXAM_BANK + load_custom_exams()}

@app.post("/api/exams/generate", dependencies=[Depends(require_admin)])
async def api_generate_exam(payload: Dict[str, Any]):
    model = payload.get("model", OLLAMA_MODEL)
    prompt = (
        "Act as an official Cambridge/ISE II exam designer. Produce a complete B2 Reading and Writing exam in strict JSON format. "
        "Do not include code blocks or markdown, return ONLY the raw JSON object with this format:\n"
        "{\n"
        '  "title": "B2 Exam: Title",\n'
        '  "task_1_title": "Task 1 - Long Reading: Title",\n'
        '  "task_1_text": "### Paragraph 1\\nText...\\n\\n### Paragraph 2\\nText...",\n'
        '  "task_1_titles_options": ["A ...", "B ...", "C ...", "D ...", "E ...", "F ..."],\n'
        '  "task_1_true_false": ["A ...", "B ...", "C ...", "D ...", "E ...", "F ...", "G ...", "H ..."],\n'
        '  "task_1_questions": [\n'
        '    {"id": 1, "text": "Paragraph 1", "answer": "A"},\n'
        '    {"id": 2, "text": "Paragraph 2", "answer": "B"},\n'
        '    {"id": 3, "text": "Paragraph 3", "answer": "C"},\n'
        '    {"id": 4, "text": "Paragraph 4", "answer": "D"},\n'
        '    {"id": 5, "text": "Paragraph 5", "answer": "E"},\n'
        '    {"id": 6, "text": "True Statement 1", "answer": "A"},\n'
        '    {"id": 7, "text": "True Statement 2", "answer": "B"},\n'
        '    {"id": 8, "text": "True Statement 3", "answer": "C"},\n'
        '    {"id": 9, "text": "True Statement 4", "answer": "D"},\n'
        '    {"id": 10, "text": "True Statement 5", "answer": "E"},\n'
        '    {"id": 11, "text": "Sentence 11 [GAP]", "answer": "Word"},\n'
        '    {"id": 12, "text": "Sentence 12 [GAP]", "answer": "Word"},\n'
        '    {"id": 13, "text": "Sentence 13 [GAP]", "answer": "Word"},\n'
        '    {"id": 14, "text": "Sentence 14 [GAP]", "answer": "Word"},\n'
        '    {"id": 15, "text": "Sentence 15 [GAP]", "answer": "Word"}\n'
        '  ],\n'
        '  "task_2_title": "Task 2 - Multi-Text Reading: Title",\n'
        '  "task_2_text": "### Text A\\nText...\\n\\n### Text B\\nText...\\n\\n### Text C\\nText...\\n\\n### Text D\\nText...",\n'
        '  "task_2_questions": [\n'
        '    {"id": 16, "text": "Statement 16", "answer": "A"},\n'
        '    {"id": 17, "text": "Statement 17", "answer": "B"},\n'
        '    {"id": 18, "text": "Statement 18", "answer": "C"},\n'
        '    {"id": 19, "text": "Statement 19", "answer": "D"},\n'
        '    {"id": 20, "text": "Statement 20", "answer": "A"},\n'
        '    {"id": 21, "text": "True 1", "answer": "A"},\n'
        '    {"id": 22, "text": "True 2", "answer": "B"},\n'
        '    {"id": 23, "text": "True 3", "answer": "C"},\n'
        '    {"id": 24, "text": "True 4", "answer": "D"},\n'
        '    {"id": 25, "text": "True 5", "answer": "E"},\n'
        '    {"id": 26, "text": "Summary 26 [GAP]", "answer": "Word"},\n'
        '    {"id": 27, "text": "Summary 27 [GAP]", "answer": "Word"},\n'
        '    {"id": 28, "text": "Summary 28 [GAP]", "answer": "Word"},\n'
        '    {"id": 29, "text": "Summary 29 [GAP]", "answer": "Word"},\n'
        '    {"id": 30, "text": "Summary 30 [GAP]", "answer": "Word"}\n'
        '  ],\n'
        '  "task_3_writing": "Article (150-180 words): Instructions...",\n'
        '  "task_4_writing": "Essay (150-180 words): Instructions..."\n'
        "}"
    )

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            res = await client.post(OLLAMA_URL, json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.3}
            })
            if res.status_code == 200:
                raw = res.json().get("message", {}).get("content", "").strip()
                cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
                cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()
                parsed = json.loads(cleaned)

                new_id = f"ai_gen_{int(time.time())}"
                exam_obj = {
                    "exam_id": new_id,
                    "title": f"[IA] {parsed.get('title', 'Generated Practice Exam')}",
                    "tasks": {
                        "task_1_long_reading": {
                            "title": parsed.get("task_1_title", "Task 1 - Long Reading"),
                            "reading_text": parsed.get("task_1_text", ""),
                            "title_options": parsed.get("task_1_titles_options", []),
                            "true_false_statements": parsed.get("task_1_true_false", []),
                            "questions": parsed.get("task_1_questions", [])
                        },
                        "task_2_multi_text": {
                            "title": parsed.get("task_2_title", "Task 2 - Multi-Text Reading"),
                            "reading_text": parsed.get("task_2_text", ""),
                            "questions": parsed.get("task_2_questions", [])
                        },
                        "task_3_writing": parsed.get("task_3_writing", ""),
                        "task_4_writing": parsed.get("task_4_writing", "")
                    }
                }
                save_custom_exam(exam_obj)
                return {"status": "success", "exam": exam_obj}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando examen con IA: {str(e)}")

    raise HTTPException(status_code=500, detail="Fallo inesperado al sintetizar examen.")

@app.post("/api/exams/audit-writing", dependencies=[Depends(require_admin)])
async def api_audit_exam_writing(payload: Dict[str, Any]):
    user_text = payload.get("text", "")
    task_type = payload.get("task_type", "Article / Essay")
    model = payload.get("model", OLLAMA_MODEL)

    prompt = (
        f"Act as a certified Cambridge/ISE II Senior Examiner. Assess this student essay ({task_type}) for B2 First / C1 Advanced:\n\n"
        f"--- ESSAY TEXT ---\n{user_text}\n\n"
        f"Provide your audit in professional Markdown with:\n"
        f"1. Task Achievement & Word Count Assessment\n"
        f"2. Lexical Resource (B2/C1 collocations vs repetitive phrasing)\n"
        f"3. Grammatical Accuracy (complex structures vs syntax errors)\n"
        f"4. Cohesion and Paragraph Flow\n"
        f"5. Precise Revised Sentences with explanations."
    )

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            res = await client.post(OLLAMA_URL, json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            })
            if res.status_code == 200:
                data = res.json()
                return {"feedback": data.get("message", {}).get("content", "Sin respuesta.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"feedback": "Error auditando redacción."}

@app.post("/api/exams/upload-pdf")
async def api_upload_exam_pdf(file: UploadFile = File(...)):
    try:
        reader = PdfReader(file.file)
        text_extracted = ""
        for page in reader.pages:
            text_extracted += (page.extract_text() or "") + "\n"

        return {
            "status": "success",
            "filename": file.filename,
            "extracted_length": len(text_extracted),
            "preview": text_extracted[:2000] + "..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")

# ------------------ ENDPOINTS DE SPEAKING ------------------
@app.post("/api/speaking/extract-pdf", dependencies=[Depends(require_admin)])
@app.post("/api/upload-pdf-speaking", dependencies=[Depends(require_admin)])
async def api_extract_speaking_pdf(file: UploadFile = File(...), model: Optional[str] = Form(None)):
    try:
        reader = PdfReader(file.file)
        extracted_text = ""
        for page in reader.pages:
            extracted_text += (page.extract_text() or "") + "\n"

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No se pudo extraer texto legible del PDF.")

        prompt_text = extracted_text[:12000]
        prompt = (
            "You are a Cambridge and ISE II speaking examiner. Read the extracted mock exam text below.\n"
            "Extract all speaking discussion questions (Part 3 and Part 4).\n\n"
            "Return ONLY a clean JSON array:\n"
            "[\n"
            "  {\n"
            '    "part": 3,\n'
            '    "topic": "General Topic",\n'
            '    "question": "Question text",\n'
            '    "bullet_points": ["Point 1", "Point 2"]\n'
            "  }\n"
            "]\n\n"
            f"--- PDF EXTRACT ---\n{prompt_text}"
        )

        model_to_use = model or OLLAMA_MODEL
        async with httpx.AsyncClient(timeout=90.0) as client:
            res = await client.post(OLLAMA_URL, json={
                "model": model_to_use,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1}
            })

            if res.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Error en motor local ({res.status_code}): {res.text}")

            raw = res.json().get("message", {}).get("content", "").strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()

            try:
                parsed_list = json.loads(cleaned)
            except Exception:
                parsed_list = [{"topic": "Speaking Prompt", "question": raw, "bullet_points": []}]

            normalized = []
            for idx, item in enumerate(parsed_list):
                q_text = item.get("question") or item.get("prompt") or ""
                normalized.append({
                    "id": f"spk_pdf_{int(time.time())}_{idx}",
                    "topic": item.get("topic", "Discussion"),
                    "question": q_text,
                    "model_answer": ", ".join(item.get("bullet_points", [])) if item.get("bullet_points") else ""
                })

            return {
                "status": "success",
                "filename": file.filename,
                "added_count": len(normalized),
                "custom_speaking": normalized,
                "extracted_questions": normalized
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar PDF de Speaking: {str(e)}")

# ------------------ ENDPOINTS DE GRAMÁTICA Y TEORÍA ------------------
@app.get("/api/grammar/theory/{node_key}")
async def api_grammar_theory(node_key: str, topic_label: str, model: Optional[str] = OLLAMA_MODEL, force_refresh: bool = False):
    node_dir = os.path.join(DATA_DIR, "grammar_theory")
    os.makedirs(node_dir, exist_ok=True)
    md_path = os.path.join(node_dir, f"{node_key}.md")

    if not force_refresh and os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            if len(content) > 150:
                return {"node": node_key, "content": content, "cached": True}

    prompt = (
        f"Actúa como un profesor nativo experto en Cambridge C1 Advanced. Redacta una guía teórica extensa y detallada en formato Markdown sobre: '{topic_label}'. "
        f"Debe incluir: 1. Reglas de uso y formación, 2. Estructuras avanzadas, 3. Errores típicos en el Use of English, y 4. Tres ejemplos explicados paso a paso."
    )
    generated_content = ""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            payload = {
                "model": model or OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.3}
            }
            res = await client.post(OLLAMA_URL, json=payload)
            if res.status_code == 200:
                data = res.json()
                if "message" in data and "content" in data["message"]:
                    generated_content = data["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando con Ollama: {str(e)}")

    if not generated_content:
        generated_content = f"# Guía Teórica: {topic_label}\n\nContenido temporal no disponible."

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generated_content)

    return {"node": node_key, "content": generated_content, "cached": False}

@app.post("/api/generate", dependencies=[Depends(require_admin)])
async def api_generate(payload: Dict[str, Any]):
    category = payload.get("category", "")
    topic = payload.get("topic", "")
    user_input = payload.get("user_input", "")
    model = payload.get("model", OLLAMA_MODEL)

    system_prompt = "Eres un examinador experto en exámenes oficiales Cambridge First (B2) y Advanced (C1)."
    user_prompt = user_input or f"Genera contenido para la categoría {category} sobre {topic}."

    if category == "grammar_uoe":
        user_prompt = (
            f"Crea un ejercicio oficial Cambridge Part 4 Key Word Transformation avanzado centrado en '{topic}'. "
            f"Formato exacto requerido:\n"
            f"ORIGINAL: [frase]\n"
            f"KEYWORD: [palabra]\n"
            f"INCOMPLETE: [segunda frase con hueco]\n"
            f"CORRECT_ANSWER: [respuesta exacta]\n"
            f"EXPLANATION: [explicación gramatical detallada]"
        )
    elif category == "grammar_writing_audit":
        user_prompt = f"Analiza este párrafo redactado por un alumno B2/C1 aplicando la estructura '{topic}':\n\n{user_input}\n\nSeñala aciertos, fallos sintácticos y mejoras."
    elif category == "speaking":
        user_prompt = "Genera un debate de Speaking Part 3 & 4 (B2/C1) con respuesta modelo PREP (Point, Reason, Example, Point rephrased)."

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            res = await client.post(OLLAMA_URL, json={
                "model": model or OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            })
            if res.status_code == 200:
                data = res.json()
                return {"content": data.get("message", {}).get("content", "Sin respuesta.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"content": "[!] No se pudo generar respuesta con el motor de IA."}

# ------------------ ENDPOINTS DE VOCABULARIO ------------------
@app.get("/api/vocab/catalog")
def api_vocab_catalog():
    catalog = {}
    if not os.path.exists(AUDIO_DIR):
        return catalog

    for item in os.listdir(AUDIO_DIR):
        full_path = os.path.join(AUDIO_DIR, item)
        if os.path.isdir(full_path):
            cat_name = item
            mp3s = [f"/generated_audio/{cat_name}/{f}" for f in os.listdir(full_path) if f.endswith(".mp3")]
            md_path = os.path.join(full_path, "notes.md")
            md_content = ""
            if os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
            catalog[cat_name] = {"tracks": sorted(mp3s), "markdown": md_content}
    return catalog

@app.get("/api/vocab/markdown")
async def api_vocab_markdown(category: str, model: Optional[str] = OLLAMA_MODEL, force_refresh: bool = False, request: Request = None):
    cat_dir = os.path.join(AUDIO_DIR, category)
    md_path = os.path.join(cat_dir, "notes.md")

    if force_refresh or not os.path.exists(md_path):
        user = get_username(request)
        if get_user_role(user) != "admin":
            if os.path.exists(md_path):
                # Si existe, se entrega la versión en caché sin error
                with open(md_path, "r", encoding="utf-8") as f:
                    return {"category": category, "markdown": f.read(), "cached": True}
            raise HTTPException(status_code=403, detail="Solo los administradores pueden generar nuevos apuntes.")

    os.makedirs(cat_dir, exist_ok=True)
    audio_files = [f for f in os.listdir(cat_dir) if f.endswith(".mp3")]
    track_phrases = []
    for f in sorted(audio_files):
        clean = os.path.splitext(f)[0]
        clean = re.sub(r'^tts_\d+_', '', clean)
        clean = re.sub(r'^\d+[\s_-]*', '', clean)
        clean = clean.replace('_', ' ').strip()
        if clean:
            track_phrases.append(clean)

    if track_phrases:
        items_str = "\n".join([f"- {item}" for item in track_phrases])
        prompt = (
            f"Act as an English tutor for B2/C1. The following is the list of audio phrases for '{category}':\n\n"
            f"{items_str}\n\n"
            f"Generate a study guide in Markdown containing:\n"
            f"1. A complete reference table with the exact phrase, Spanish translation, and phonetic/usage notes.\n"
            f"2. Two formal B2/C1 example sentences illustrating each key term.\n"
            f"3. Common phrasal verbs and collocations related to these terms."
        )
    else:
        prompt = f"Generate Markdown study notes for English category '{category}' with Spanish translations and collocations."

    content = f"# Vocabulary Guide: {category}\n\nNo se pudo contactar con el motor de IA."
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            res = await client.post(OLLAMA_URL, json={
                "model": model or OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.2}
            })
            if res.status_code == 200:
                data = res.json()
                if "message" in data and "content" in data["message"]:
                    content = data["message"]["content"]
    except Exception as e:
        content = f"# Error generando apuntes para {category}\n\nFallo de conexión: {str(e)}"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"category": category, "markdown": content, "cached": False}

# ------------------ ESTADO DE USUARIO, MODELOS Y TTS ------------------
@app.get("/api/user/whoami")
def api_whoami(request: Request):
    user = get_username(request)
    return {"username": user, "role": get_user_role(user)}

@app.get("/api/user/state")
def api_get_state(request: Request):
    return get_user_profile(get_username(request))

@app.post("/api/user/state")
def api_save_state(payload: UserStateModel, request: Request):
    user = get_username(request)
    current = get_user_profile(user)
    merged = {
        "username": user,
        "target_date": payload.target_date or current["target_date"],
        "selected_model": payload.selected_model or current["selected_model"],
        "theme": payload.theme or current["theme"],
        "hard_targets": payload.hard_targets if payload.hard_targets is not None else current["hard_targets"],
        "daily_tracker": payload.daily_tracker if payload.daily_tracker is not None else current["daily_tracker"],
        "custom_prompts": payload.custom_prompts if payload.custom_prompts is not None else current["custom_prompts"],
        "custom_speaking": payload.custom_speaking if payload.custom_speaking is not None else current["custom_speaking"],
        "custom_grammar": payload.custom_grammar if payload.custom_grammar is not None else current["custom_grammar"]
    }
    save_user_profile(user, merged)
    return {"status": "success", "profile": merged}

@app.get("/api/models")
async def api_list_models():
    models = ["kalikorpz/glm-4.7-flash:latest", "qwen3.5:latest", "llama3:latest"]
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(OLLAMA_URL.replace("/api/chat", "/api/tags"))
            if res.status_code == 200:
                data = res.json()
                if "models" in data:
                    fetched = [m["name"] for m in data["models"]]
                    if fetched:
                        models = fetched
    except Exception:
        pass
    return {"models": models}

@app.post("/api/tts")
async def api_tts(payload: TTSRequest):
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', payload.text[:25]).strip('_') or "speech"
        filename = f"tts_{int(time.time())}_{clean_name}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        communicate = edge_tts.Communicate(payload.text, payload.voice, rate=payload.rate)
        await communicate.save(filepath)

        return {"status": "success", "audio_url": f"/generated_audio/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run("api_tracker:app", host="0.0.0.0", port=8001, reload=False)
