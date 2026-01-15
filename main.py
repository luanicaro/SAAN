from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from fpdf import FPDF
import io
from datetime import datetime
from sqlalchemy.orm import Session
import time
import os
import hmac
import hashlib
import base64
import models
from database import get_db, engine

# Cria tabelas se não existirem (idealmente use alembic para migrações em prod)
models.Base.metadata.create_all(bind=engine)

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

# ------------------------------
# Schemas (Pydantic)
# ------------------------------

class QuestionSchema(BaseModel):
    id: Optional[int] = None 
    text: str
    example: Optional[str] = ""
    scaleType: str
    group: Optional[str] = None # Nome do grupo (ex: "Usabilidade")

class FormSchema(BaseModel):
    title: str
    description: Optional[str] = ""
    questions: List[QuestionSchema]

class RegisterSchema(BaseModel):
    username: str
    password: str
    role: str

class LoginSchema(BaseModel):
    username: str
    password: str

class ApplicationSchema(BaseModel):
    name: str
    appType: str  # 'web' | 'mobile'
    url: Optional[str] = ""
    formId: int   # ID do formulário
    evaluators: List[str]  # usernames de avaliadores (Mantendo compatibilidade de input)

class AnswerItem(BaseModel):
    questionId: int
    value: int  # 1..5

class ResponseSchema(BaseModel):
    applicationId: int
    formId: int
    answers: List[AnswerItem]

# ------------------------------
# Configs
# ------------------------------

ALLOWED_ROLES = [
    "admin",                 # Admin: Cadastra formulários
    "engenheiro",            # Engenheiro de Testes: Cadastra a aplicação/funcionalidades
    "avaliador",             # Avaliador: Realiza a avaliação
    "stakeholder"            # Cliente/Stakeholder: Visualiza relatórios
]

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
TOKEN_EXP_SECONDS = 60 * 60 * 8  # 8h

# ------------------------------
# Utilidades: Senhas e JWT
# ------------------------------

def hash_password(password: str, salt: str = "static-salt") -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def b64url_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)

import json
def json_dumps(data):
    return json.dumps(data, separators=(",", ":"))

def jwt_encode(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = b64url_encode(json_dumps(header).encode())
    payload_b64 = b64url_encode(json_dumps(payload).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    signature_b64 = b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def jwt_decode(token: str, secret: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3: raise ValueError
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, b64url_decode(sig_b64)):
            raise HTTPException(status_code=401, detail="Token inválido")
        payload = json.loads(b64url_decode(payload_b64))
        if "exp" in payload and int(payload["exp"]) < int(time.time()):
            raise HTTPException(status_code=401, detail="Token expirado")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Token malformado ou inválido")

def create_token(user: models.User) -> str:
    now = int(time.time())
    payload = {"sub": user.username, "role": user.role, "id": user.id, "iat": now, "exp": now + TOKEN_EXP_SECONDS}
    return jwt_encode(payload, SECRET_KEY)

def get_user_from_token(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        # Tenta pegar do header Authorization: Bearer <token>
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ")[1]
            
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

# ------------------------------
# Rotas
# ------------------------------

@app.get("/")
def read_root():
    return {"status": "online", "message": "API de Formulários rodando com PostgreSQL."}

# --- AUTH ---

@app.post("/auth/register")
def register_user(payload: RegisterSchema, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    role = payload.role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"Role inválida. Use uma de: {', '.join(ALLOWED_ROLES)}")

    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Usuário já existe")

    new_user = models.User(
        username=username,
        password_hash=hash_password(payload.password),
        role=role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "success", "message": "Usuário cadastrado"}

@app.post("/auth/login")
def login_user(payload: LoginSchema, response: Response, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    user = db.query(models.User).filter(models.User.username == username).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_token(user)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False, 
        samesite="lax",
        max_age=TOKEN_EXP_SECONDS,
        path="/"
    )
    return {"status": "success", "user": {"username": user.username, "role": user.role, "id": user.id}, "token": token}

@app.post("/auth/logout")
def logout_user(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"status": "success"}

@app.get("/auth/me")
def me(user=Depends(require_roles())):
    return {"user": user}

# --- FORMS ---

@app.post("/forms")
def create_form(form: FormSchema, user=Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    print(f"[LOG] Recebendo novo formulário: {form.title}")
    
    try:
        creator_id = user.get("id") 
        if not creator_id: 
             creator = db.query(models.User).filter(models.User.username == user.get("sub")).first()
             if creator: creator_id = creator.id

        new_form = models.Form(
            title=form.title,
            description=form.description,
            created_by=creator_id
        )
        db.add(new_form)
        db.flush()

        # Dicionário para cachear grupos criados: nome -> objeto QuestionGroup
        groups_map = {}

        for q in form.questions:
            group_id = None
            if q.group:
                # Normaliza nome
                g_name = q.group.strip()
                if g_name:
                    if g_name not in groups_map:
                        # Cria novo grupo
                        new_group = models.QuestionGroup(
                            form_id=new_form.id,
                            name=g_name
                        )
                        db.add(new_group)
                        db.flush() # Precisa do ID
                        groups_map[g_name] = new_group
                    group_id = groups_map[g_name].id

            new_q = models.Question(
                form_id=new_form.id,
                group_id=group_id,
                text=q.text,
                example=q.example,
                scale_type=q.scaleType
            )
            db.add(new_q)
        
        db.commit()
        db.refresh(new_form)
        
        count = db.query(models.Form).count()
        return {
            "status": "success", 
            "message": "Formulário salvo com sucesso!",
            "total_forms": count,
            "formId": new_form.id
        }
        
    except Exception as e:
        print(f"[ERRO] Falha ao salvar: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno ao salvar dados: {str(e)}")

@app.get("/forms")
def get_forms(user=Depends(require_roles(["admin", "avaliador", "stakeholder", "engenheiro"])), db: Session = Depends(get_db)):
    forms = db.query(models.Form).all()
    result = []
    for f in forms:
        questions_data = []
        for q in f.questions:
            questions_data.append({
                "id": q.id,
                "text": q.text,
                "example": q.example,
                "scaleType": q.scale_type,
                "group": q.group.name if q.group else None,
                "groupId": q.group_id
            })

        result.append({
            "id": f.id,
            "title": f.title,
            "description": f.description,
            "questions": questions_data
        })
    return result

# --- USERS ---

@app.get("/users")
def list_users(role: Optional[str] = None, _=Depends(require_roles(["admin", "engenheiro"])), db: Session = Depends(get_db)):
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role.strip().lower())
    users = query.all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]

# --- APPLICATIONS ---

class ApplicationSchema(BaseModel):
    name: str
    appType: str  
    url: Optional[str] = ""
    formId: int   
    evaluators: List[str]  
    groupWeights: Optional[Dict[str, float]] = None # "group_id": weight

class AnswerItem(BaseModel):
    questionId: int
    value: int  

class ResponseSchema(BaseModel):
    applicationId: int
    formId: int
    answers: List[AnswerItem]

@app.get("/applications")
def get_applications(_=Depends(require_roles(["admin", "engenheiro", "stakeholder"])), db: Session = Depends(get_db)):
    apps = db.query(models.Application).all()
    result = []
    for a in apps:
        result.append({
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "url": a.url,
            "formId": a.form_id,
            "evaluators": [u.username for u in a.evaluators] # Compatibilidade: devolver nomes
        })
    return result

@app.post("/applications")
def create_application(app_data: ApplicationSchema, user=Depends(require_roles(["engenheiro", "admin"])), db: Session = Depends(get_db)):
    # valida formId
    form = db.query(models.Form).filter(models.Form.id == app_data.formId).first()
    if not form:
        raise HTTPException(status_code=400, detail="formId inválido")

    # Mapear evaluators (usernames ou ids?) - Schema diz str (usernames)
    evaluators_objects = []
    for ident in app_data.evaluators:
        # Tenta achar por username
        u = db.query(models.User).filter(models.User.username == ident).first()
        if not u:
             # Se falhar, tenta achar por ID (caso venha string de numero)
             if ident.isdigit():
                 u = db.query(models.User).filter(models.User.id == int(ident)).first()
        
        if u and u.role == "avaliador":
            evaluators_objects.append(u)
        else:
             raise HTTPException(status_code=400, detail=f"Avaliador inválido ou não encontrado: {ident}")

    new_app = models.Application(
        name=app_data.name,
        type=app_data.appType,
        url=app_data.url or "",
        form_id=app_data.formId
    )
    new_app.evaluators = evaluators_objects
    
    db.add(new_app)
    db.flush() # ID

    # Salvar Pesos
    if app_data.groupWeights:
        for gid_str, weight in app_data.groupWeights.items():
            try:
                gid = int(gid_str)
                w_val = float(weight)
                if w_val < 0 or w_val > 1:
                    raise HTTPException(status_code=400, detail=f"Peso inválido para o grupo {gid}: deve ser entre 0 e 1")

                gw = models.ApplicationGroupWeight(
                    application_id=new_app.id,
                    group_id=gid,
                    weight=w_val
                )
                db.add(gw)
            except ValueError:
                pass # Ignora chaves invalidas
    
    db.commit()
    db.refresh(new_app)
    
    return {
        "status": "success", 
        "application": {
            "id": new_app.id,
            "name": new_app.name,
            "evaluators": [u.username for u in new_app.evaluators]
        }
    }

# --- ASSIGNMENTS ---

@app.get("/my-assignments")
def my_assignments(me=Depends(require_roles(["avaliador"])), db: Session = Depends(get_db)):
    username = me.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return []

    # SQLAlchemy relationship
    assigned_apps = user.assigned_applications
    
    tasks = []
    for app_obj in assigned_apps:
        # Check if already responded
        resp = db.query(models.Response).filter(
            models.Response.application_id == app_obj.id,
            models.Response.evaluator_id == user.id
        ).first()

        # Requirement: Do not show if completed
        if resp:
            continue
        
        form_obj = app_obj.form
        
        q_list = []
        if form_obj:
            for q in form_obj.questions:
                g_name = "Geral"
                if q.group:
                    g_name = q.group.name
                q_list.append({
                    "id": q.id, 
                    "text": q.text, 
                    "scaleType": q.scale_type,
                    "example": q.example, # Include example too
                    "group": g_name
                })

        tasks.append({
            "applicationId": app_obj.id,
            "applicationName": app_obj.name,
            "formId": app_obj.form_id,
            "form": {
                 "id": form_obj.id, 
                 "title": form_obj.title,
                 "questions": q_list
            } if form_obj else None
        })
    return tasks

# --- RESPONSES ---

@app.post("/responses")
def submit_response(payload: ResponseSchema, me=Depends(require_roles(["avaliador"])), db: Session = Depends(get_db)):
    # Pegar usuario
    username = me.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
         raise HTTPException(status_code=403, detail="Usuário não encontrado")

    # Valida Application
    app_obj = db.query(models.Application).filter(models.Application.id == payload.applicationId).first()
    if not app_obj:
        raise HTTPException(status_code=400, detail="Aplicação inválida")
    
    # Verifica permissão (se está na lista de evaluators)
    if user not in app_obj.evaluators:
        raise HTTPException(status_code=403, detail="Não atribuído a esta aplicação")
        
    if payload.formId != app_obj.form_id:
        raise HTTPException(status_code=400, detail="Formulário não corresponde à aplicação")
    
    # Valida perguntas
    form_questions_ids = {q.id for q in app_obj.form.questions}
    for ans in payload.answers:
        if ans.questionId not in form_questions_ids:
            # Compatibilidade: Se o frontend enviar IDs antigos (1,2,3) mas o banco tem IDs novos (45,46...)
            # isso vai quebrar. O frontend deve usar os IDs que vieram do GET /my-assignments ou GET /forms
            # Assumimos que o fluxo é: GET form (recebe IDs reais) -> POST response (usa IDs reais)
            raise HTTPException(status_code=400, detail=f"Pergunta inválida para este formulário: {ans.questionId}")
        if ans.value < 1 or ans.value > 5:
            raise HTTPException(status_code=400, detail="Valor fora da escala (1-5)")

    # Criar Response
    new_resp = models.Response(
        application_id=payload.applicationId,
        form_id=payload.formId,
        evaluator_id=user.id,
        created_at=int(time.time())
    )
    db.add(new_resp)
    db.flush() # ID
    
    for ans in payload.answers:
        new_ans = models.Answer(
            response_id=new_resp.id,
            question_id=ans.questionId,
            value=ans.value
        )
        db.add(new_ans)
    
    db.commit()
    return {"status": "success", "responseId": new_resp.id}

# --- REPORTS ---

STANDARD_GROUPS = [
    "Ajuda os usuários a entender o que são as coisas e como usá-las?",
    "Reduz a carga cognitiva?",
    "Apoia conhecimentos e hábitos existentes",
    "Fornece suporte e treinamento?",
    "Dá suporte à memória e atenção?",
    "Fornece suporte a erros?",
    "Fornece feedback oportuno, adequado e consistente?",
    "Permite personalização, flexibilidade e alternativas?"
]

NEURODIVERGENCY_PROFILES = {
    "MCI": [0.06, 0.04, 0.16, 0.20, 0.28, 0.12, 0.12, 0.02],
    "Autismo": [0.16, 0.22, 0.18, 0.07, 0.08, 0.05, 0.14, 0.10],
    "Dislexia": [0.24, 0.16, 0.06, 0.14, 0.04, 0.10, 0.08, 0.18],
    "TDAH": [0.10, 0.26, 0.02, 0.14, 0.22, 0.07, 0.14, 0.05],
    "Demencia": [0.10, 0.04, 0.16, 0.20, 0.30, 0.12, 0.07, 0.01],
    "Sindrome de Down": [0.20, 0.22, 0.10, 0.18, 0.06, 0.12, 0.08, 0.04],
    "Discalculia": [0.26, 0.10, 0.04, 0.20, 0.04, 0.16, 0.12, 0.08],
    "Perda de memória": [0.08, 0.03, 0.16, 0.22, 0.32, 0.12, 0.06, 0.01],
    "Afasia": [0.28, 0.12, 0.04, 0.18, 0.03, 0.08, 0.07, 0.20]
}

NEURO_INFO = {
    "MCI": {
        "description": "Comprometimento Cognitivo Leve (MCI) afeta a memória, linguagem e julgamento. Usuários podem ter dificuldade em lembrar passos complexos ou manter o foco.",
        "tips": "Use interfaces limpas, minimize distrações e forneça instruções passo a passo claras. Evite cronômetros curtos."
    },
    "Autismo": {
        "description": "O Transtorno do Espectro Autista (TEA) influencia a comunicação e interação social. Pode haver hipersensibilidade sensorial e preferência por rotinas.",
        "tips": "Evite metáforas complexas e linguagem figurada. Use cores suaves e previsibilidade na navegação. Permita personalização sensorial."
    },
    "Dislexia": {
        "description": "Dificuldade na leitura e processamento de texto. Fontes pequenas, textos justificados e baixo contraste são barreiras.",
        "tips": "Use fontes sans-serif, permita ajuste de tamanho de texto e evite itálicos. Use ícones para reforçar o texto."
    },
    "TDAH": {
        "description": "Transtorno de Déficit de Atenção e Hiperatividade. Dificuldade em manter o foco em tarefas longas e impulsividade.",
        "tips": "Divida tarefas em etapas curtas. Use feedback imediato e visual. Evite paredes de texto e animações distrativas desnecessárias."
    },
    "Demencia": {
        "description": "Declínio cognitivo progressivo que afeta memória e raciocínio.",
        "tips": "Extrema simplicidade é chave. Use navegação linear, botões grandes e etiquetas explícitas. Evite exigir memorização."
    },
    "Sindrome de Down": {
        "description": "Pode envolver desafios cognitivos e de coordenação motora fina.",
        "tips": "Use linguagem simples e direta. Botões grandes e espaçados facilitam o toque. Suporte visual é essencial."
    },
    "Discalculia": {
        "description": "Dificuldade específica com números e conceitos matemáticos.",
        "tips": "Evite depender apenas de números. Use representações gráficas para dados. Evite cálculos mentais obrigatórios (ex: CAPTCHAs matemáticos)."
    },
    "Perda de memória": {
        "description": "Dificuldade em reter informações de curto prazo.",
        "tips": "Não exija que o usuário lembre de informações de uma tela para outra. Use breadcrumbs e histórico visível."
    },
    "Afasia": {
        "description": "Dificuldade na compreensão e produção da linguagem (fala/escrita).",
        "tips": "Priorize comunicação visual (ícones, imagens) sobre texto denso. Use frases curtas e diretas."
    }
}

def get_weight_for_group(profile_name: str, group_name: str) -> float:
    if not group_name:
        return 1.0
    
    weights = NEURODIVERGENCY_PROFILES.get(profile_name)
    if not weights:
        return 1.0

    g_name_lower = group_name.lower().strip()
    
    # Try indexing
    for idx, std in enumerate(STANDARD_GROUPS):
        std_lower = std.lower()
        # Clean naming "1. foo" -> "foo"
        import re
        clean_std = re.sub(r'^\d+\.\s*', '', std_lower)
        clean_g = re.sub(r'^\d+\.\s*', '', g_name_lower)
        
        if clean_std in clean_g or clean_g in clean_std:
             if idx < len(weights):
                 return weights[idx]
    
    return 1.0

def likert_to_score_0_10(v: int) -> float:
    return (max(1, min(5, v)) - 1) * 2.5

@app.get("/reports/application-score")
def application_score(applicationId: Optional[int] = None, name: Optional[str] = None, _=Depends(require_roles(["stakeholder", "admin", "engenheiro"])), db: Session = Depends(get_db)):
    
    target_apps = []
    app_name = None
    
    if applicationId is not None:
        app_obj = db.query(models.Application).filter(models.Application.id == applicationId).first()
        if not app_obj:
            raise HTTPException(status_code=404, detail="Aplicação não encontrada")
        target_apps = [app_obj]
        app_name = app_obj.name
    elif name:
        name_norm = name.strip().lower()
        # Busca case insensitive manual ou usar ILIKE se postgres exclusivo
        # Fazendo em python para manter simples compatibilidade
        all_apps = db.query(models.Application).all()
        target_apps = [a for a in all_apps if a.name.strip().lower() == name_norm]
        if not target_apps:
             return {"applicationName": name, "applicationIds": [], "score": None, "countResponses": 0, "countAnswers": 0}
        app_name = name
    else:
        raise HTTPException(status_code=400, detail="Informe applicationId ou name")

    # Calcula scores
    # Estrutura: { "MCI": {weighted_sum: x, weight_sum: y}, ... "Standard": ... }
    
    profiles_data = {k: {"w_sum": 0.0, "w_total": 0.0} for k in NEURODIVERGENCY_PROFILES.keys()}
    profiles_data["Standard"] = {"w_sum": 0.0, "w_total": 0.0} # Equal weights

    count_resp = 0
    count_ans = 0

    for app in target_apps:
        # Carrega respostas
        responses = db.query(models.Response).filter(models.Response.application_id == app.id).all()
        count_resp += len(responses)

        for r in responses:
            for ans in r.answers:
                count_ans += 1
                q = ans.question
                raw_score = likert_to_score_0_10(ans.value)
                
                # Group Name
                g_name = ""
                if q.group_id:
                    # Need to fetch group name. accessing q.group might need explicit join or lazy load
                    # Assuming lazy load works:
                    if q.group:
                         g_name = q.group.name
                
                # 1. Standard Score (Weight 1.0)
                profiles_data["Standard"]["w_sum"] += raw_score * 1.0
                profiles_data["Standard"]["w_total"] += 1.0
                
                # 2. Neuro Profiles
                for p_name in NEURODIVERGENCY_PROFILES.keys():
                    w = get_weight_for_group(p_name, g_name)
                    profiles_data[p_name]["w_sum"] += raw_score * w
                    profiles_data[p_name]["w_total"] += w

    if profiles_data["Standard"]["w_total"] == 0:
         return {"applicationName": app_name, "applicationIds": [a.id for a in target_apps], "score": None, "neuroScores": {}, "countResponses": count_resp, "countAnswers": 0}

    # Finalize
    final_scores = {}
    for p_name, data in profiles_data.items():
        if data["w_total"] > 0:
            final_scores[p_name] = round(data["w_sum"] / data["w_total"], 2)
        else:
            final_scores[p_name] = None
            
    standard_score = final_scores.pop("Standard")
    
    return {
        "applicationName": app_name,
        "applicationIds": [a.id for a in target_apps],
        "score": standard_score, # Unweighted Average
        "neuroScores": final_scores,
        "countResponses": count_resp,
        "countAnswers": count_ans,
        "scale": "0-10",
        "method": "multi-profile-weighted"
    }
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatório de Acessibilidade - SAAN', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, label, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 5, body)
        self.ln()

@app.get("/reports/export-pdf")
def export_pdf(applicationId: int, db: Session = Depends(get_db)):
    try:
        # 1. Fetch App
        app_obj = db.query(models.Application).filter(models.Application.id == applicationId).first()
        if not app_obj:
            raise HTTPException(status_code=404, detail="Application not found")

        # 2. Calculate Scores (Reusing Logic)
        profiles_data = {k: {"w_sum": 0.0, "w_total": 0.0} for k in NEURODIVERGENCY_PROFILES.keys()}
        profiles_data["Standard"] = {"w_sum": 0.0, "w_total": 0.0}
        
        responses = db.query(models.Response).filter(models.Response.application_id == app_obj.id).all()
        count_resp = len(responses)
        
        for r in responses:
            for ans in r.answers:
                q = ans.question
                raw_score = likert_to_score_0_10(ans.value)
                g_name = q.group.name if q.group else ""
                
                # Standard
                profiles_data["Standard"]["w_sum"] += raw_score
                profiles_data["Standard"]["w_total"] += 1.0
                
                # Profiles
                for p_name in NEURODIVERGENCY_PROFILES.keys():
                    w = get_weight_for_group(p_name, g_name)
                    profiles_data[p_name]["w_sum"] += raw_score * w
                    profiles_data[p_name]["w_total"] += w

        final_scores = {}
        for p_name, data in profiles_data.items():
            if data["w_total"] > 0:
                final_scores[p_name] = round(data["w_sum"] / data["w_total"], 2)
            else:
                final_scores[p_name] = 0.0

        standard_score = final_scores.pop("Standard")

        # 3. Generate PDF
        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Title Info
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Aplicação: {app_obj.name}", 0, 1)
        pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
        pdf.cell(0, 10, f"Total de Avaliações: {count_resp}", 0, 1)
        pdf.ln(10)

        # Main Score
        pdf.set_font('Arial', 'B', 16)
        score_text = f"Nota Geral: {standard_score}/10"
        pdf.cell(0, 10, score_text, 0, 1, 'C')
        pdf.ln(10)

        # Breakdown Table
        pdf.chapter_title("Detalhamento por Neurodivergência")
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 10, 'Neurodivergência', 1)
        pdf.cell(40, 10, 'Nota (0-10)', 1)
        pdf.cell(90, 10, 'Status', 1)
        pdf.ln()

        pdf.set_font('Arial', '', 10)
        for p_name, score in final_scores.items():
            status_txt = "Excelente" if score >= 8 else "Bom" if score >= 5 else "Precisa Melhorar"
            pdf.cell(60, 10, p_name, 1)
            pdf.cell(40, 10, str(score), 1)
            pdf.cell(90, 10, status_txt, 1)
            pdf.ln()
        
        pdf.ln(10)

        # Detailed Info
        pdf.chapter_title("Guias de Acessibilidade")
        
        for p_name, info in NEURO_INFO.items():
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 10, f"{p_name} (Nota: {final_scores.get(p_name, 0)})", 0, 1)
            
            pdf.set_font('Arial', 'I', 10)
            pdf.multi_cell(0, 5, f"Descrição: {info['description']}")
            pdf.ln(2)
            
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 5, f"Dicas de Acessibilidade: {info['tips']}")
            pdf.ln(5)

        # Output
        pdf_bytes = bytes(pdf.output())
        buffer = io.BytesIO(pdf_bytes)
        
        headers = {
            'Content-Disposition': f'attachment; filename="report_{app_obj.id}.pdf"'
        }
        return StreamingResponse(buffer, media_type='application/pdf', headers=headers)

    except Exception as e:
        print(f"[PDF ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
