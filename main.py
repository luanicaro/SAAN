from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

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

def load_db():
    
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if not content: return []
            return json.loads(content)
    except json.JSONDecodeError:
        return []

def save_db(data):

    with open(DB_FILE, "w", encoding="utf-8") as f:

        json.dump(data, f, indent=2, ensure_ascii=False)

@app.get("/")
def read_root():
    return {"status": "online", "message": "API de Formulários rodando. Use POST /forms para salvar."}

@app.post("/forms")
def create_form(form: FormSchema):
    """Recebe um novo formulário e o salva no banco de dados."""
    print(f"[LOG] Recebendo novo formulário: {form.title}")
    
    try:
        current_data = load_db()
        
        new_record = form.dict()
        
        # new_record['created_at'] = str(datetime.now())
        
        current_data.append(new_record)
        save_db(current_data)
        
        print(f"[LOG] Sucesso! Total de formulários salvos: {len(current_data)}")
        
        return {
            "status": "success", 
            "message": "Formulário salvo com sucesso!",
            "total_forms": len(current_data)
        }
        
    except Exception as e:
        print(f"[ERRO] Falha ao salvar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao salvar dados: {str(e)}")

@app.get("/forms")
def get_forms():
    """Retorna todos os formulários salvos (para visualização/debug)."""
    return load_db()