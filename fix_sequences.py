from sqlalchemy import text
from database import SessionLocal

def fix_sequences():
    db = SessionLocal()
    try:
        # Tables to fix
        tables = ["users", "forms", "question_groups", "questions", "applications", "application_group_weights", "responses", "answers"]
        
        print("Corrigindo sequências (IDs)...")
        
        for table in tables:
            # Postgres sequence naming convention is usually table_id_seq
            seq_name = f"{table}_id_seq"
            
            # Get max id
            result = db.execute(text(f"SELECT MAX(id) FROM {table}"))
            max_id = result.scalar() or 0
            
            print(f"Tabela '{table}': Max ID = {max_id}")
            
            # Reset sequence
            # we set it to max_id, so the NEXT one will be max_id + 1
            if max_id > 0:
                stmt = text(f"SELECT setval('{seq_name}', :val, true)")
                db.execute(stmt, {"val": max_id})
                print(f" -> Sequência '{seq_name}' ajustada para {max_id}")
            else:
                 print(f" -> Tabela vazia ou sem IDs, pulando.")
        
        db.commit()
        print("\nSucesso! As sequências foram sincronizadas.")
        
    except Exception as e:
        print(f"\n[ERRO] Falha ao corrigir sequências: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_sequences()
