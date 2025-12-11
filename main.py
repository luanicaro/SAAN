from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import time
import hmac
import hashlib
import base64

# ------------------------------
# App & CORS
# ------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(BaseModel):
    id: int
    text: str
    example: Optional[str] = ""
    scaleType: str

class FormSchema(BaseModel):
    title: str
    description: Optional[str] = ""
    questions: List[Question]

# --- PERSISTÊNCIA (Arquivo JSON) ---
DB_FILE = "database.json"
USERS_FILE = "users.json"

ALLOWED_ROLES = [
    "admin",                 # Admin: Cadastra formulários
    "engenheiro",            # Engenheiro de Testes: Cadastra a aplicação/funcionalidades
    "avaliador",             # Avaliador: Realiza a avaliação
    "stakeholder"            # Cliente/Stakeholder: Visualiza relatórios
]

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
TOKEN_EXP_SECONDS = 60 * 60 * 8  # 8h

# ------------------------------
# Utilidades: armazenamento simples (JSON)
# ------------------------------

def load_db():
    """Carrega o arquivo principal. Suporta formato legado (lista de formulários).
    Gera IDs para formulários/aplicações/respostas se ausentes.
    """
    if not os.path.exists(DB_FILE):
        return {"forms": [], "applications": [], "responses": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                return {"forms": [], "applications": [], "responses": []}
            data = json.loads(content)
            # Compatibilidade com formato antigo (lista simples de forms)
            if isinstance(data, list):
                data = {"forms": data, "applications": [], "responses": []}
            # Garante chaves
            data.setdefault("forms", [])
            data.setdefault("applications", [])
            data.setdefault("responses", [])
            # Migração de IDs
            changed = False
            # Forms IDs
            max_form_id = 0
            for f in data["forms"]:
                if isinstance(f, dict) and "id" in f and isinstance(f["id"], int):
                    max_form_id = max(max_form_id, f["id"])
            for f in data["forms"]:
                if isinstance(f, dict) and "id" not in f:
                    max_form_id += 1
                    f["id"] = max_form_id
                    changed = True
            # Applications IDs
            max_app_id = 0
            for a in data["applications"]:
                if isinstance(a, dict) and "id" in a and isinstance(a["id"], int):
                    max_app_id = max(max_app_id, a["id"])
            for a in data["applications"]:
                if isinstance(a, dict) and "id" not in a:
                    max_app_id += 1
                    a["id"] = max_app_id
                    changed = True
            # Responses IDs
            max_resp_id = 0
            for r in data["responses"]:
                if isinstance(r, dict) and "id" in r and isinstance(r["id"], int):
                    max_resp_id = max(max_resp_id, r["id"])
            for r in data["responses"]:
                if isinstance(r, dict) and "id" not in r:
                    max_resp_id += 1
                    r["id"] = max_resp_id
                    changed = True
            if changed:
                save_db(data)
            return data
    except json.JSONDecodeError:
        return {"forms": [], "applications": [], "responses": []}


def save_db(store):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def load_users():
    if not os.path.exists(USERS_FILE):
        # cria admin padrão
        default = [{
            "id": 1,
            "username": "admin",
            "password_hash": "",  # será preenchido na primeira gravação
            "role": "admin"
        }]
        # define hash de senha padrão (admin123)
        default[0]["password_hash"] = hash_password("admin123")
        save_users(default)
        return default
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                return []
            users = json.loads(content)
            # Garante IDs de usuários
            changed = False
            max_id = 0
            for u in users:
                if isinstance(u, dict) and isinstance(u.get("id"), int):
                    max_id = max(max_id, u["id"])
            for u in users:
                if isinstance(u, dict) and "id" not in u:
                    max_id += 1
                    u["id"] = max_id
                    changed = True
            if changed:
                save_users(users)
            return users
    except json.JSONDecodeError:
        return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


# ------------------------------
# Utilidades: Senhas e JWT HS256 (sem dependências externas)
# ------------------------------

def hash_password(password: str, salt: str = "static-salt") -> str:
    # Nota: use bcrypt/argon2 em produção. Aqui é didático e simples.
    return hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def jwt_encode(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    signature_b64 = b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def jwt_decode(token: str, secret: str) -> dict:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, b64url_decode(sig_b64)):
            raise HTTPException(status_code=401, detail="Token inválido")
        payload = json.loads(b64url_decode(payload_b64))
        if "exp" in payload and int(payload["exp"]) < int(time.time()):
            raise HTTPException(status_code=401, detail="Token expirado")
        return payload
    except ValueError:
        raise HTTPException(status_code=401, detail="Token malformado")


def create_token(username: str, role: str) -> str:
    now = int(time.time())
    payload = {"sub": username, "role": role, "iat": now, "exp": now + TOKEN_EXP_SECONDS}
    return jwt_encode(payload, SECRET_KEY)


def get_user_from_token(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    payload = jwt_decode(token, SECRET_KEY)
    return payload


def require_roles(roles: Optional[List[str]] = None):
    def _dependency(request: Request):
        payload = get_user_from_token(request)
        if roles and payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Sem permissão")
        return payload
    return _dependency

@app.get("/")
def read_root():
    return {"status": "online", "message": "API de Formulários rodando. Use POST /forms para salvar."}


# ------------------------------
# AUTH
# ------------------------------

class RegisterSchema(BaseModel):
    username: str
    password: str
    role: str


class LoginSchema(BaseModel):
    username: str
    password: str


@app.post("/auth/register")
def register_user(payload: RegisterSchema):
    username = payload.username.strip().lower()
    role = payload.role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"Role inválida. Use uma de: {', '.join(ALLOWED_ROLES)}")

    users = load_users()
    if any(u.get("username") == username for u in users):
        raise HTTPException(status_code=409, detail="Usuário já existe")

    new_id = (max([u.get("id", 0) for u in users], default=0) + 1) if users else 1
    users.append({
        "id": new_id,
        "username": username,
        "password_hash": hash_password(payload.password),
        "role": role
    })
    save_users(users)
    return {"status": "success", "message": "Usuário cadastrado"}


@app.post("/auth/login")
def login_user(payload: LoginSchema, response: Response):
    username = payload.username.strip().lower()
    users = load_users()
    user = next((u for u in users if u.get("username") == username), None)
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_token(username, user.get("role"))
    # Define cookie HTTPOnly
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # ajuste para True se usar HTTPS
        samesite="lax",
        max_age=TOKEN_EXP_SECONDS,
        path="/"
    )
    return {"status": "success", "user": {"username": username, "role": user.get("role")}}


@app.post("/auth/logout")
def logout_user(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"status": "success"}


@app.get("/auth/me")
def me(user=Depends(require_roles())):
    return {"user": user}

@app.post("/forms")
def create_form(form: FormSchema, user=Depends(require_roles(["admin"]))):
    """Recebe um novo formulário e o salva no banco de dados."""
    print(f"[LOG] Recebendo novo formulário: {form.title}")
    
    try:
        store = load_db()
        new_id = (max([f.get("id", 0) for f in store["forms"]], default=0) + 1) if store["forms"] else 1
        new_record = {"id": new_id, **form.dict()}
        store["forms"].append(new_record)
        save_db(store)
        print(f"[LOG] Sucesso! Total de formulários salvos: {len(store['forms'])}")
        
        return {
            "status": "success", 
            "message": "Formulário salvo com sucesso!",
            "total_forms": len(store["forms"])
        }
        
    except Exception as e:
        print(f"[ERRO] Falha ao salvar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao salvar dados: {str(e)}")

@app.get("/forms")
def get_forms(user=Depends(require_roles(["admin", "avaliador", "stakeholder", "engenheiro"]))):
    """Retorna todos os formulários salvos (para visualização/debug)."""
    store = load_db()
    return store["forms"]


# ------------------------------
# Users (listagem para seleção de avaliadores)
# ------------------------------

@app.get("/users")
def list_users(role: Optional[str] = None, _=Depends(require_roles(["admin", "engenheiro"]))):
    users = load_users()
    if role:
        role = role.strip().lower()
        users = [
            {"id": u["id"], "username": u["username"], "role": u.get("role")}
            for u in users if u.get("role") == role
        ]
    else:
        users = [{"id": u["id"], "username": u["username"], "role": u.get("role")} for u in users]
    return users


# ------------------------------
# Applications (criar/consultar)
# ------------------------------

class ApplicationSchema(BaseModel):
    name: str
    appType: str  # 'web' | 'mobile'
    url: Optional[str] = ""
    formId: int   # ID do formulário
    evaluators: List[str]  # usernames de avaliadores


@app.get("/applications")
def get_applications(_=Depends(require_roles(["admin", "engenheiro", "stakeholder"]))):
    store = load_db()
    return store["applications"]


@app.post("/applications")
def create_application(app_data: ApplicationSchema, user=Depends(require_roles(["engenheiro", "admin"]))):
    store = load_db()
    # valida formId (por ID explícito)
    form = next((f for f in store["forms"] if f.get("id") == app_data.formId), None)
    if not form:
        raise HTTPException(status_code=400, detail="formId inválido")

    # valida usuários avaliadores
    users = load_users()
    allowed_eval = {u["username"] for u in users if u.get("role") == "avaliador"}
    for ev in app_data.evaluators:
        if ev not in allowed_eval:
            raise HTTPException(status_code=400, detail=f"Avaliador inválido: {ev}")

    new_id = (max([a.get("id", 0) for a in store["applications"]], default=0) + 1) if store["applications"] else 1
    record = {
        "id": new_id,
        "name": app_data.name,
        "type": app_data.appType,
        "url": app_data.url or "",
        "formId": app_data.formId,
        "evaluators": app_data.evaluators,
    }
    store["applications"].append(record)
    save_db(store)
    return {"status": "success", "application": record}


# ------------------------------
# Assignments para Avaliador
# ------------------------------

@app.get("/my-assignments")
def my_assignments(me=Depends(require_roles(["avaliador"]))):
    username = me.get("sub")
    store = load_db()
    tasks = []
    for app in store["applications"]:
        if username in app.get("evaluators", []):
            form = next((f for f in store["forms"] if f.get("id") == app.get("formId")), None)
            if form:
                # verifica se já respondeu
                resp = next((r for r in store["responses"] if r.get("applicationId") == app["id"] and r.get("evaluator") == username), None)
                tasks.append({
                    "applicationId": app["id"],
                    "applicationName": app.get("name"),
                    "formId": app.get("formId"),
                    "form": form,
                    "completed": bool(resp),
                    "responseId": resp.get("id") if resp else None
                })
    return tasks


# ------------------------------
# Respostas de Avaliação
# ------------------------------

class AnswerItem(BaseModel):
    questionId: int
    value: int  # 1..5


class ResponseSchema(BaseModel):
    applicationId: int
    formId: int
    answers: List[AnswerItem]


@app.post("/responses")
def submit_response(payload: ResponseSchema, me=Depends(require_roles(["avaliador"]))):
    store = load_db()
    # valida application
    app = next((a for a in store["applications"] if a.get("id") == payload.applicationId), None)
    if not app:
        raise HTTPException(status_code=400, detail="Aplicação inválida")
    if me.get("sub") not in app.get("evaluators", []):
        raise HTTPException(status_code=403, detail="Não atribuído a esta aplicação")
    if payload.formId != app.get("formId"):
        raise HTTPException(status_code=400, detail="Formulário não corresponde à aplicação")
    # valida questionIds pertencem ao form
    form = next((f for f in store["forms"] if f.get("id") == payload.formId), None)
    if not form:
        raise HTTPException(status_code=400, detail="Formulário inválido")
    qids = {q.get("id") for q in form.get("questions", [])}
    for ans in payload.answers:
        if ans.questionId not in qids:
            raise HTTPException(status_code=400, detail=f"Pergunta inválida: {ans.questionId}")
    # valida answers 1..5
    for ans in payload.answers:
        if ans.value < 1 or ans.value > 5:
            raise HTTPException(status_code=400, detail="Valor fora da escala")

    new_id = (max([r.get("id", 0) for r in store["responses"]], default=0) + 1) if store["responses"] else 1
    record = {
        "id": new_id,
        "applicationId": payload.applicationId,
        "formId": payload.formId,
        "evaluator": me.get("sub"),
        "answers": [a.dict() for a in payload.answers],
        "created_at": int(time.time())
    }
    store["responses"].append(record)
    save_db(store)
    return {"status": "success", "responseId": new_id}


# ------------------------------
# Relatórios - Nota 0..10 por aplicação (Stakeholder)
# ------------------------------

def likert_to_score_0_10(v: int) -> float:
    # 1..5 -> 0..10 de forma linear
    return (max(1, min(5, v)) - 1) * 2.5


@app.get("/reports/application-score")
def application_score(applicationId: Optional[int] = None, name: Optional[str] = None, _=Depends(require_roles(["stakeholder", "admin", "engenheiro"]))):
    store = load_db()
    apps = store["applications"]

    target_ids: List[int] = []
    app_name = None
    if applicationId is not None:
        app = next((a for a in apps if a.get("id") == applicationId), None)
        if not app:
            raise HTTPException(status_code=404, detail="Aplicação não encontrada")
        target_ids = [app["id"]]
        app_name = app.get("name")
    elif name:
        name_norm = name.strip().lower()
        matches = [a for a in apps if str(a.get("name", "")).strip().lower() == name_norm]
        if not matches:
            return {"applicationName": name, "applicationIds": [], "score": None, "countResponses": 0, "countAnswers": 0}
        target_ids = [a["id"] for a in matches]
        app_name = name
    else:
        raise HTTPException(status_code=400, detail="Informe applicationId ou name")

    relevant_responses = [r for r in store["responses"] if r.get("applicationId") in target_ids]
    if not relevant_responses:
        return {"applicationName": app_name, "applicationIds": target_ids, "score": None, "countResponses": 0, "countAnswers": 0}

    scores = []
    for r in relevant_responses:
        for ans in r.get("answers", []):
            scores.append(likert_to_score_0_10(int(ans.get("value", 0))))

    if not scores:
        return {"applicationName": app_name, "applicationIds": target_ids, "score": None, "countResponses": len(relevant_responses), "countAnswers": 0}

    avg = sum(scores) / len(scores)
    return {
        "applicationName": app_name,
        "applicationIds": target_ids,
        "score": round(avg, 2),
        "countResponses": len(relevant_responses),
        "countAnswers": len(scores),
        "scale": "0-10",
        "method": "likert-linear"
    }