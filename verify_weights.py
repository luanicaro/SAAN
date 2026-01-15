import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
ADMIN_USER = "admin_w_test"
ADMIN_PASS = "admin123"
EVAL_USER = "eval_w_test"
EVAL_PASS = "eval123"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def verify():
    s = requests.Session()

    # 1. Register Users
    log("Registering Users...")
    s.post(f"{BASE_URL}/auth/register", json={"username": ADMIN_USER, "password": ADMIN_PASS, "role": "admin"})
    s.post(f"{BASE_URL}/auth/register", json={"username": EVAL_USER, "password": EVAL_PASS, "role": "avaliador"})

    res = s.post(f"{BASE_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if res.status_code != 200:
        log("Admin login failed", "ERROR")
        return False
    data = res.json()
    admin_token = data["token"]
    user_role = data["user"]["role"]
    log(f"Logged in as {ADMIN_USER}, Role: {user_role}")
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # DEBUG: Check /auth/me
    me_res = s.get(f"{BASE_URL}/auth/me", headers=admin_headers)
    log(f"Auth Me Check: {me_res.status_code} {me_res.text}")

    # 3. Create Form with 2 Groups
    log("Creating Form...")
    form_res = s.post(f"{BASE_URL}/forms", json={
        "title": "Form Ponderado",
        "questions": [
            {"text": "Q1 G1", "scaleType": "5-point", "group": "G1"}, # Group 1
            {"text": "Q2 G2", "scaleType": "5-point", "group": "G2"}  # Group 2
        ]
    }, headers=admin_headers)
    form_id = form_res.json()["formId"]

    # Get Form to find Groups IDs
    form_data = s.get(f"{BASE_URL}/forms", headers=admin_headers).json()
    my_form = next(f for f in form_data if f["id"] == form_id)
    g1_id = next(q["groupId"] for q in my_form["questions"] if q["text"] == "Q1 G1")
    g2_id = next(q["groupId"] for q in my_form["questions"] if q["text"] == "Q2 G2")
    
    q1_id = next(q["id"] for q in my_form["questions"] if q["text"] == "Q1 G1")
    q2_id = next(q["id"] for q in my_form["questions"] if q["text"] == "Q2 G2")

    # 4. Create Application with Weights (G1=2.0, G2=1.0)
    log("Creating Application with Weights...")
    app_res = s.post(f"{BASE_URL}/applications", json={
        "name": "App Ponderada",
        "appType": "web",
        "formId": form_id,
        "evaluators": [EVAL_USER],
        "groupWeights": {str(g1_id): 0.8, str(g2_id): 0.4}
    }, headers=admin_headers)
    if app_res.status_code != 200:
        log(f"Create App failed: {app_res.text}", "ERROR")
        return False
    app_id = app_res.json()["application"]["id"]

    # 5. Login Evaluator and Submit Response
    log("Submitting Response...")
    res = s.post(f"{BASE_URL}/auth/login", json={"username": EVAL_USER, "password": EVAL_PASS})
    eval_token = res.json()["token"]
    eval_headers = {"Authorization": f"Bearer {eval_token}"}

    # Answers: Q1(G1)=5 (Score 10), Q2(G2)=3 (Score 5)
    # Weighted Score Expected:
    # (10 * 2.0 + 5 * 1.0) / (2.0 + 1.0) = 25 / 3 = 8.33
    s.post(f"{BASE_URL}/responses", json={
        "applicationId": app_id,
        "formId": form_id,
        "answers": [
            {"questionId": q1_id, "value": 5},
            {"questionId": q2_id, "value": 3}
        ]
    }, headers=eval_headers)

    # 6. Check Report Score
    log("Checking Report Score...")
    report = requests.get(f"{BASE_URL}/reports/application-score?applicationId={app_id}", headers=admin_headers).json()

    log(f"Report Response: {report}")
    if "score" not in report: 
        log("Score not found in report", "ERROR")
        return False
    score = report["score"]
    log(f"Score received: {score}")
    
    if 8.30 <= score <= 8.35:
        log("Weighted Score Verification Passed!", "SUCCESS")
        return True
    else:
        log(f"Weighted Score Verification Failed! Expected ~8.33, got {score}", "ERROR")
        return False

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)
