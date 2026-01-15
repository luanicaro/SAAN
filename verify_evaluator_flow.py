import requests
import json
import sys

BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin_verify_flow"
ADMIN_PASS = "admin123"
EVAL_USER = "eval_verify_flow"
EVAL_PASS = "eval123"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def verify():
    s = requests.Session()
    
    # 1. Register Users
    log("Registering Users...")
    s.post(f"{BASE_URL}/auth/register", json={"username": ADMIN_USER, "password": ADMIN_PASS, "role": "admin"})
    s.post(f"{BASE_URL}/auth/register", json={"username": EVAL_USER, "password": EVAL_PASS, "role": "avaliador"})

    # 2. Login Admin
    log("Logging in Admin...")
    resp = s.post(f"{BASE_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if resp.status_code != 200:
        log("Admin Login Failed", "ERROR")
        return False
    
    # 3. Create Form
    log("Creating Form...")
    form_data = {
        "title": "Form Flow Test",
        "description": "Testing Groups",
        "questions": [
            {"text": "Q1 G1", "scaleType": "5-point", "group": "Group 1"},
            {"text": "Q2 G1", "scaleType": "5-point", "group": "Group 1"},
            {"text": "Q3 G2", "scaleType": "5-point", "group": "Group 2"}
        ]
    }
    r = s.post(f"{BASE_URL}/forms", json=form_data)
    if r.status_code != 200:
        log("Form creation failed", "ERROR")
        return False
    form_id = r.json()["formId"]

    # 4. Create Application & Assign
    log("Creating Application...")
    app_data = {
        "name": "App Flow Test",
        "formId": form_id,
        "appType": "mobile",
        "evaluators": [EVAL_USER]
    }
    r = s.post(f"{BASE_URL}/applications", json=app_data)
    if r.status_code != 200:
        log(f"App creation failed: {r.text}", "ERROR")
        return False
    app_id = r.json()["application"]["id"]

    # 5. Login Evaluator
    log("Logging in Evaluator...")
    s.post(f"{BASE_URL}/auth/login", json={"username": EVAL_USER, "password": EVAL_PASS})
    
    # 6. Check Assignments (Should be present and have Groups)
    log("Checking Assignments...")
    r = s.get(f"{BASE_URL}/my-assignments")
    assignments = r.json()
    
    target = next((a for a in assignments if a["applicationId"] == app_id), None)
    if not target:
        log("Assignment not found", "ERROR")
        return False
    
    # Verify Groups
    qs = target["form"]["questions"]
    if qs[0].get("group") != "Group 1":
        log(f"Group 1 missing. Got: {qs[0].get('group')}", "ERROR")
        return False
    if qs[2].get("group") != "Group 2":
        log(f"Group 2 missing. Got: {qs[2].get('group')}", "ERROR")
        return False
    
    log("Groups Verified correctly.", "SUCCESS")

    # 7. Submit Responses (Complete the task)
    log("Submitting Responses...")
    payload = {
        "applicationId": app_id,
        "formId": form_id,
        "answers": [
            {"questionId": qs[0]["id"], "value": 5},
            {"questionId": qs[1]["id"], "value": 5},
            {"questionId": qs[2]["id"], "value": 5}
        ]
    }
    r = s.post(f"{BASE_URL}/responses", json=payload)
    if r.status_code != 200:
        log(f"Submit failed: {r.text}", "ERROR")
        return False
    
    # 8. Check Assignments (Should be GONE)
    log("Checking Assignments (Should be empty/filtered)...")
    r = s.get(f"{BASE_URL}/my-assignments")
    assignments_after = r.json()
    
    target_after = next((a for a in assignments_after if a["applicationId"] == app_id), None)
    if target_after:
        log("Assignment still present after completion!", "ERROR")
        return False

    log("Assignment filtered correctly.", "SUCCESS")
    return True

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)
