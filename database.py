from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Use environment variable for DB URL or default to a local user for dev
# Format: postgresql://user:password@host/dbname
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://saan_user:senha_segura@localhost/saan_db")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
