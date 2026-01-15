import requests
import sys

BASE_URL = "http://localhost:8000"
# Reusing users from previous flows if possible, or new ones.
# Assuming verify_evaluator_flow created 'App Flow Test'.
# We need to find an application ID.

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def verify():
    s = requests.Session()
    
    # Login Admin to list apps
    log("Logging in Admin...")
    s.post(f"{BASE_URL}/auth/login", json={"username": "admin_verify_flow", "password": "admin123"})
    
    # Get Apps
    r = s.get(f"{BASE_URL}/applications")
    if r.status_code != 200:
        log("Failed to list apps", "ERROR")
        return False
    
    apps = r.json()
    if not apps:
        log("No apps found. Run previous verifications first.", "ERROR")
        return False
    
    target_app = apps[0]
    app_id = target_app["id"]
    log(f"Target App: {target_app['name']} (ID: {app_id})")

    # Request PDF
    log("Requesting PDF...")
    r = s.get(f"{BASE_URL}/reports/export-pdf?applicationId={app_id}")
    
    if r.status_code != 200:
        log(f"PDF Request Failed: {r.text}", "ERROR")
        return False
    
    if "application/pdf" not in r.headers.get("Content-Type", ""):
        log(f"Invalid Content-Type: {r.headers.get('Content-Type')}", "ERROR")
        return False
    
    content = r.content
    if not content.startswith(b"%PDF"):
        log("Content does not look like PDF", "ERROR")
        return False
        
    log(f"PDF Generated Successfully. Size: {len(content)} bytes", "SUCCESS")
    
    # Save for manual inspection if needed
    with open("test_report.pdf", "wb") as f:
        f.write(content)
        
    return True

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)
