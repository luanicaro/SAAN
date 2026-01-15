import json
import os
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

def migrate():
    print("Criando tabelas no banco de dados...")
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 1. Migrar Usuários
    print("Migrando Usuários...")
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            users_data = json.load(f)
            for u_data in users_data:
                # Verifica se já existe
                existing = db.query(models.User).filter(models.User.username == u_data["username"]).first()
                if not existing:
                    user = models.User(
                        # id=u_data["id"], # Deixar o banco gerar ou forçar ID? 
                        # Vamos tentar manter os IDs originais se possível, mas Postgres usa serial.
                        # Para simplificar e garantir consistência futura, vamos deixar o Postgres gerar,
                        # exceto se quisermos forçar. SQLAlchemy permite insert explícito de ID.
                        # Mas como vamos remapear tudo, melhor deixar o banco decidir os IDs novos?
                        # O problema é que se os JSONs já tem IDs, manter eles ajuda.
                        # Vamos tentar forçar o ID.
                        id=u_data.get("id"),
                        username=u_data["username"],
                        password_hash=u_data["password_hash"],
                        role=u_data["role"]
                    )
                    db.add(user)
            db.commit()
    
    # Recarregar mapa de usuários para lookup (username -> user object)
    users_map = {u.username: u for u in db.query(models.User).all()}
    
    # 2. Migrar Dados do database.json
    if os.path.exists("database.json"):
        with open("database.json", "r") as f:
            data = json.load(f)
            
            # Forms
            print("Migrando Formulários e Perguntas...")
            forms_map = {} # old_id -> new_obj
            for f_data in data.get("forms", []):
                # Assumindo admin como criador padrão se não houver info
                admin = db.query(models.User).filter(models.User.role == "admin").first()
                creator_id = admin.id if admin else None
                
                form = models.Form(
                    title=f_data["title"],
                    description=f_data.get("description", ""),
                    created_by=creator_id
                )
                db.add(form)
                db.flush() # Para gerar ID
                forms_map[f_data["id"]] = form
                
                # Perguntas
                for q_data in f_data.get("questions", []):
                    question = models.Question(
                        form_id=form.id,
                        text=q_data["text"],
                        example=q_data.get("example", ""),
                        scale_type=q_data.get("scaleType", "5-point")
                    )
                    db.add(question)
            
            db.commit()

            # Applications
            print("Migrando Aplicações...")
            apps_map = {} # old_id -> new_obj
            for a_data in data.get("applications", []):
                old_form_id = a_data.get("formId")
                new_form = forms_map.get(old_form_id)
                
                if not new_form:
                    print(f"Skipping application {a_data['name']} due to missing form {old_form_id}")
                    continue

                app = models.Application(
                    name=a_data["name"],
                    type=a_data["type"],
                    url=a_data.get("url", ""),
                    form_id=new_form.id
                )
                
                # Evaluators (names -> ids)
                for eval_name in a_data.get("evaluators", []):
                    user = users_map.get(eval_name)
                    if user:
                        app.evaluators.append(user)
                
                db.add(app)
                db.flush()
                apps_map[a_data["id"]] = app
            
            db.commit()

            # Responses
            print("Migrando Respostas...")
            for r_data in data.get("responses", []):
                old_app_id = r_data.get("applicationId")
                new_app = apps_map.get(old_app_id)
                
                old_form_id = r_data.get("formId")
                new_form = forms_map.get(old_form_id)
                
                evaluator_name = r_data.get("evaluator")
                evaluator = users_map.get(evaluator_name)
                
                if not new_app or not new_form or not evaluator:
                    print(f"Skipping response due to missing relations")
                    continue
                
                response = models.Response(
                    application_id=new_app.id,
                    form_id=new_form.id,
                    evaluator_id=evaluator.id,
                    created_at=r_data.get("created_at", 0)
                )
                db.add(response)
                db.flush()
                
                # Mapear perguntas do form novo para identificar IDs
                # O problema é que as respostas antigas usam question IDs antigos (1, 2, 3...)
                # E as perguntas novas geraram novos IDs.
                # Assumindo que a ORDEM das perguntas ou o TEXTO não mudou.
                # database.json questions tem "id": 1, 2...
                # Vamos tentar mapear pelo ID antigo local (dentro do form)
                
                # Recarrega perguntas do novo form
                new_questions = {q.text: q for q in new_form.questions}
                # No database.json, precisamos pegar o texto da pergunta antiga com aquele ID para achar a nova
                # Ineficiente, mas funciona pra migração única.
                
                # Ache o form original dados
                original_form = next((f for f in data["forms"] if f["id"] == old_form_id), None)
                if original_form:
                    original_questions = {q["id"]: q["text"] for q in original_form.get("questions", [])}
                    
                    for ans in r_data.get("answers", []):
                        old_q_id = ans["questionId"]
                        q_text = original_questions.get(old_q_id)
                        new_q = new_questions.get(q_text)
                        
                        if new_q:
                            answer = models.Answer(
                                response_id=response.id,
                                question_id=new_q.id,
                                value=ans["value"]
                            )
                            db.add(answer)
            
            db.commit()
    
    print("Migração concluída com sucesso!")
    db.close()

if __name__ == "__main__":
    migrate()
