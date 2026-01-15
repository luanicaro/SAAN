import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
ADMIN_USER = "admin_prof_test"
ADMIN_PASS = "admin123"
EVAL_USER = "eval_prof_test"
EVAL_PASS = "eval123"

# Profile: MCI
# Weights: [0.06, 0.04, 0.16, 0.20, 0.28, 0.12, 0.12, 0.02]
# Groups:
GROUPS = [
    "1. Ajuda os usuários a entender o que são as coisas e como usá-las?",
    "2. Reduz a carga cognitiva?", # Index 1 -> 0.04
    "3. Apoia conhecimentos e hábitos existentes" # Index 2 -> 0.16
]
# Expected Weights:
# G1: 0.06
# G2: 0.04
# G3: 0.16

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def verify():
    # Helper to clean session
    s = requests.Session()

    # 1. Register Users
    log("Registering Users...")
    s.post(f"{BASE_URL}/auth/register", json={"username": ADMIN_USER, "password": ADMIN_PASS, "role": "admin"})
    s.post(f"{BASE_URL}/auth/register", json={"username": EVAL_USER, "password": EVAL_PASS, "role": "avaliador"})

    # 2. Login Admin
    res = s.post(f"{BASE_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if res.status_code != 200:
        log("Admin login failed", "ERROR")
        return False
    admin_token = res.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Create Form
    log("Creating Form with Standard Groups...")
    form_res = s.post(f"{BASE_URL}/forms", json={
        "title": "Form Neurodiverso",
        "questions": [
            {"text": "Q1", "scaleType": "5-point", "group": GROUPS[0]},
            {"text": "Q2", "scaleType": "5-point", "group": GROUPS[1]},
            {"text": "Q3", "scaleType": "5-point", "group": GROUPS[2]}
        ]
    }, headers=admin_headers)
    form_id = form_res.json()["formId"]

    # Get GIDs
    form_data = s.get(f"{BASE_URL}/forms", headers=admin_headers).json()
    my_form = next(f for f in form_data if f["id"] == form_id)
    
    gid_map = {}
    qid_map = {}
    for q in my_form["questions"]:
        gid_map[q["group"]] = q["groupId"]
        qid_map[q["group"]] = q["id"]

    # 4. Create Application simulating Frontend Logic for MCI
    # Frontend logic would map:
    # GROUPS[0] -> Index 0 -> 0.06
    # GROUPS[1] -> Index 1 -> 0.04
    # GROUPS[2] -> Index 2 -> 0.16
    
    weights_payload = {
        str(gid_map[GROUPS[0]]): 0.06,
        str(gid_map[GROUPS[1]]): 0.04,
        str(gid_map[GROUPS[2]]): 0.16
    }
    
    log(f"Simulating Frontend Payload for MCI: {weights_payload}")

    app_res = s.post(f"{BASE_URL}/applications", json={
        "name": "App MCI",
        "appType": "web",
        "formId": form_id,
        "evaluators": [EVAL_USER],
        "groupWeights": weights_payload
    }, headers=admin_headers)
    
    if app_res.status_code != 200:
        log(f"App Creation Failed: {app_res.text}", "ERROR")
        return False
    app_id = app_res.json()["application"]["id"]

    # 5. Evaluate
    # Answers:
    # Q1 (Weight 0.06): 5 (Score 10)
    # Q2 (Weight 0.04): 5 (Score 10)
    # Q3 (Weight 0.16): 1 (Score 0) -- To check impact
    
    # Weighted Score:
    # Weighted Score:
    # (10*0.06 + 10*0.04 + 0*0.16) / (0.06 + 0.04 + 0.16)
    # (0.6 + 0.4 + 0) / 0.26
    # 1.0 / 0.26 = 3.846...
    
    # Use generic request to avoid cookie issues
    
    eval_login = requests.post(f"{BASE_URL}/auth/login", json={"username": EVAL_USER, "password": EVAL_PASS})
    eval_token = eval_login.json()["token"]
    eval_headers = {"Authorization": f"Bearer {eval_token}"}

    requests.post(f"{BASE_URL}/responses", json={
        "applicationId": app_id,
        "formId": form_id,
        "answers": [
            {"questionId": qid_map[GROUPS[0]], "value": 5},
            {"questionId": qid_map[GROUPS[1]], "value": 5},
            {"questionId": qid_map[GROUPS[2]], "value": 1}
        ]
    }, headers=eval_headers)

    # 6. Check Report
    log("Checking Report...")
    report = s.get(f"{BASE_URL}/reports/application-score?applicationId={app_id}", headers=admin_headers).json()
    
    # New API structure:
    # score: Standard
    # neuroScores: { ... }
    
    if "neuroScores" not in report:
        log("Missing neuroScores in report", "ERROR")
        return False
        
    mci_score = report["neuroScores"].get("MCI")
    standard_score = report["score"]
    
    log(f"MCI Score: {mci_score}. Expected ~3.85")
    log(f"Standard Score: {standard_score}")

    if mci_score and 3.80 <= mci_score <= 3.90:
        log("Profile Simulation Verified!", "SUCCESS")
        return True
    else:
        log("Verification Failed!", "ERROR")
        return False

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)
