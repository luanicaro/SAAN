import json
import os
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

def seed_users():
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        if not os.path.exists("users.json"):
            print("users.json not found, skipping seed.")
            return

        with open("users.json", "r") as f:
            users_data = json.load(f)

        print(f"Found {len(users_data)} users to seed...")
        
        for u in users_data:
            # Check if exists
            existing = db.query(models.User).filter(models.User.username == u["username"]).first()
            if not existing:
                print(f"Creating user: {u['username']}")
                new_user = models.User(
                    username=u["username"],
                    password_hash=u["password_hash"], # stored hash in json
                    role=u["role"]
                )
                db.add(new_user)
            else:
                print(f"User {u['username']} already exists.")
        
        db.commit()
        print("Seeding completed.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()
