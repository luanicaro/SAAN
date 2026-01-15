import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import SQLALCHEMY_DATABASE_URL

def apply_changes():
    # Parse URL manually or use sqlalchemy engine to connect
    # URL format: postgresql://user:pass@host/db
    
    print(f"Conectando ao banco...")
    try:
        conn = psycopg2.connect(SQLALCHEMY_DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Criar tabela question_groups se não existir
        print("Verificando tabela question_groups...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS question_groups (
                id SERIAL PRIMARY KEY,
                form_id INTEGER REFERENCES forms(id),
                name VARCHAR
            );
        """)
        
        # 2. Adicionar coluna group_id na tabela questions
        print("Verificando coluna group_id em questions...")
        try:
            cur.execute("ALTER TABLE questions ADD COLUMN group_id INTEGER REFERENCES question_groups(id);")
            print("Coluna group_id adicionada.")
        except psycopg2.errors.DuplicateColumn:
            print("Coluna group_id já existe.")
            conn.rollback() 
        except Exception as e:
            print(f"Erro ao adicionar coluna: {e}")
            conn.rollback()

        # 3. Create index for group_id (good practice)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS ix_questions_group_id ON questions (group_id);")
        except Exception:
            conn.rollback()

        # 4. Create table application_group_weights
        print("Verificando tabela application_group_weights...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS application_group_weights (
                id SERIAL PRIMARY KEY,
                application_id INTEGER REFERENCES applications(id),
                group_id INTEGER REFERENCES question_groups(id),
                weight FLOAT DEFAULT 1.0
            );
        """)
        try:
             cur.execute("CREATE INDEX IF NOT EXISTS ix_app_group_weights_app_id ON application_group_weights (application_id);")
        except Exception:
            conn.rollback()

        conn.commit()
        cur.close()
        conn.close()
        print("Schema atualizado com sucesso!")
        
    except Exception as e:
        print(f"Erro critical: {e}")

if __name__ == "__main__":
    apply_changes()
