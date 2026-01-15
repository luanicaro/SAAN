import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
ADMIN_USER = "admin_test"
ADMIN_PASS = "admin123"
EVAL_USER = "eval_test"
EVAL_PASS = "eval123"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def verify():
    s = requests.Session()

    # 1. Register Admin
    log(f"Registering Admin: {ADMIN_USER}")
    res = s.post(f"{BASE_URL}/auth/register", json={
        "username": ADMIN_USER, "password": ADMIN_PASS, "role": "admin"
    })
    if res.status_code not in [200, 409]:
        log(f"Failed to register admin: {res.text}", "ERROR")
        return False
    
    # 2. Login Admin
    log("Logging in Admin")
    res = s.post(f"{BASE_URL}/auth/login", json={
        "username": ADMIN_USER, "password": ADMIN_PASS
    })
    if res.status_code != 200:
        log(f"Login failed: {res.text}", "ERROR")
        return False
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Form with Groups
    log("Creating Form with Groups")
    form_payload = {
        "title": "Verificacao de Grupos",
        "description": "Formulario teste auto-gerado",
        "questions": [
            {"text": "Questao 1", "scaleType": "5-point", "group": "Grupo A"},
            {"text": "Questao 2", "scaleType": "5-point", "group": "Grupo A"},
            {"text": "Questao 3", "scaleType": "5-point", "group": "Grupo B"}
        ]
    }
    res = requests.post(f"{BASE_URL}/forms", json=form_payload, headers=headers)
    if res.status_code != 200:
        log(f"Create form failed: {res.text}", "ERROR")
        return False
    form_id = res.json()["formId"]
    log(f"Form created with ID: {form_id}", "SUCCESS")

    # 4. Verify Form Structure
    log("Verifying Form Structure (GET /forms)")
    res = requests.get(f"{BASE_URL}/forms", headers=headers)
    forms = res.json()
    my_form = next((f for f in forms if f["id"] == form_id), None)
    if not my_form:
        log("Form not found in list", "ERROR")
        return False
    
    # Check groups
    q1 = next(q for q in my_form["questions"] if q["text"] == "Questao 1")
    if q1.get("group") != "Grupo A":
        log(f"Group mismatch for Q1: expected 'Grupo A', got {q1.get('group')}", "ERROR")
        return False
    
    log("Form structure verified correctly", "SUCCESS")

    return True

if __name__ == "__main__":
    if verify():
        log("Verification Completed Successfully", "SUCCESS")
    else:
        log("Verification Failed", "ERROR")
        sys.exit(1)
