from fastapi import FastAPI, Request, Form  
from fastapi.responses import JSONResponse  
from datetime import datetime 
from pydantic import BaseModel
import os  
from pathlib import Path
import os
import json
import socket, getpass
class SomeInput(BaseModel):
    user_id: str
    # Add other fields as needed for your analysis (e.g., text: str, model:str, parameters, etc.)

USE_RENDER = True  # Try Render first
RENDER_URL = "https://harmony-gpt.onrender.com"  # Replace with actual URL
TUNNEL_URL = "https://harmonygpt.loca.lt"            # Secondary fallback

# Try connecting to both servers
def get_available_server():
    try:
        r = requests.get(f"{RENDER_URL}/health", timeout=2)
        if r.status_code == 200:
            return RENDER_URL
    except:
        pass
    try:
        r = requests.get(f"{TUNNEL_URL}/health", timeout=2)
        if r.status_code == 200:
            return TUNNEL_URL
    except:
        pass
    return None  # No server available

BASE_URL = get_available_server()
if BASE_URL is None:
    print("❌ No server reachable. Check internet or tunnel status.")
else:
    print(f"✅ Connected to server: {BASE_URL}")

# Use this to build file/api paths
def get_path(endpoint):
    return f"{BASE_URL}/{endpoint}"    

app = FastAPI()

# === Base Path Logic (Plan A / Plan B Fallback) ===
BASE_PATH = os.path.join(os.getcwd(), "harmony_server", "admin_data")  # Plan A
if not os.path.exists(BASE_PATH):
    BASE_PATH = os.path.join(os.getcwd(), "gomasterg_sync_server", "admin_data")  # Plan B

os.makedirs(BASE_PATH, exist_ok=True)

# === Global Path Constants (used across modules) ===
ADMIN_FILE = os.path.join(BASE_PATH, "admin.txt")
DEMO_LIMIT_FILE = os.path.join(BASE_PATH, "demo_limit.txt")
USER_FILE = os.path.join(BASE_PATH, "user.txt")
USER_CHAT_LOG = os.path.join(BASE_PATH, "user_chat_logs.txt")
USER_ISSUE_LOG = os.path.join(BASE_PATH, "user_issue_log.txt")
DEMO_ACCESS_FILE = os.path.join(BASE_PATH, "demo_access.txt")
DUPLICATE_LOG_FILE = os.path.join(BASE_PATH, "duplicate_activity_log.txt")

# Pathlib example (for special usage where needed)
ADMIN_DATA_PATH = Path(BASE_PATH)
CONSENT_LOG_PATH = ADMIN_DATA_PATH / "consent_log.txt"

# === Core Files to Sync: Name -> Default Content ===
FILES_TO_CREATE = {
    "admin.txt": "",
    "demo_limit.txt": "3\n",
    "user.txt": "",
    "user_chat_logs.txt": "",
    "user_issue_log.txt": "",
    "demo_access.txt": "",
    "duplicate_activity_log.txt": "",
    "consent_log.txt": ""
}

from fastapi.responses import FileResponse

@app.get("/download-exe")
def download_harmony_ai():
    return FileResponse("Harmony_AI.exe", media_type='application/octet-stream', filename="Harmony_AI.exe")

@app.post("/sync")
def sync_files():
    """
    Endpoint to sync system files from the server to the user's laptop/desktop.
    If a file doesn't exist, it will be created with default content.
    """
    result = {}
    for file_name, default_content in FILES_TO_CREATE.items():
        file_path = os.path.join(BASE_PATH, file_name)
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(default_content)
            result[file_name] = "created"
        else:
            result[file_name] = "already exists"

    return {
        "status": "success",
        "base_path_used": BASE_PATH,
        "synced_files": result
    }

# === DEVICE ID ===
def get_device_id():
    return f"{socket.gethostname()}-{getpass.getuser()}"
device_id = get_device_id()

# Ensure folders and files exist  
os.makedirs(ADMIN_DATA_FOLDER, exist_ok=True)  
for file in [USER_FILE, CHAT_LOG_FILE, ISSUE_LOG_FILE]:  
    if not os.path.exists(file):  
        open(file, "a", encoding="utf-8").close()  

@app.get("/")  
def root():  
    return {"message": "Harmony Sync Server is running."}  

# === Consent Model ===
class Consent(BaseModel):
    user_id: str
    full_name: str
    mobile: str
    agreed: bool
    device_id: str
    consent_text: str = "I agree to terms and conditions."

# === Consent Recording ===
@app.post("/consent")
async def record_consent(data: Consent):
    if not (data.user_id and data.full_name and data.mobile and data.agreed):
        return {"status": "error", "message": "Missing required consent fields."}

    # Log entry format
    log_entry = {
        "timestamp": str(datetime.now()),
        "user_id": data.user_id,
        "full_name": data.full_name,
        "mobile": data.mobile,
        "device_id": data.device_id,
        "agreed": data.agreed,
        "consent_text": data.consent_text
    }

    # Append to master log file (one line per user)
    with open(CONSENT_LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Save individual consent file
    user_consent_file = ADMIN_DATA_PATH / f"{data.user_id}.json"
    user_consent_file.write_text(json.dumps(log_entry, indent=2))

    return {"status": "success", "message": "Consent recorded."}

# === Consent Verification ===
def has_user_consented(user_id: str) -> bool:
    if not CONSENT_LOG_PATH.exists():
        return False
    try:
        with open(CONSENT_LOG_PATH, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("user_id") == user_id and entry.get("agreed"):
                        return True
                except json.JSONDecodeError:
                    continue
        return False
    except Exception:
        return False

# === Analyzer Example ===
class SomeInput(BaseModel):
    user_id: str
    text: str  # Your actual input model may vary

@app.post("/analyze")
async def analyze(data: SomeInput):
    if not has_user_consented(data.user_id):
        return {
            "status": "error",
            "message": "Consent not found. Please complete the consent form first."
        }

    # Proceed with analysis logic
    return {"status": "success", "message": "Consent verified. Proceeding with analysis."}
    
# === USER ACCESS STATUS ===  
@app.post("/access-status")  
def check_access(user_id: str = Form(...)):  
    if not os.path.exists(USER_FILE):  
        return JSONResponse(content={"access": "error", "reason": "user file not found"})  

    with open(USER_FILE, "r", encoding="utf-8") as f:  
        for line in f:  
            parts = line.strip().split("|")  
            if len(parts) == 4 and parts[0] == user_id:  
                return JSONResponse(content={"access": parts[2], "expiry": parts[3]})  

    return JSONResponse(content={"access": "error", "reason": "user not found"})  

# === USER ADD/UPDATE ===  
@app.post("/add-user")  
def add_user(username: str = Form(...), password: str = Form(...), status: str = Form(...), expiry: str = Form(...)):  
    new_line = f"{username}|{password}|{status}|{expiry}\n"  
    updated = False  

    if os.path.exists(USER_FILE):  
        with open(USER_FILE, "r", encoding="utf-8") as f:  
            lines = f.readlines()  

        with open(USER_FILE, "w", encoding="utf-8") as f:  
            for line in lines:  
                if line.startswith(username + "|"):  
                    f.write(new_line)  
                    updated = True  
                else:  
                    f.write(line)  

    if not updated:  
        with open(USER_FILE, "a", encoding="utf-8") as f:  
            f.write(new_line)  

    return JSONResponse(content={"status": "success", "message": "User added or updated."})  

# === CHAT LOGGING ===  
@app.post("/log-chat")  
def log_chat(user_id: str = Form(...), message: str = Form(...)):  
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    clean_message = message.strip().replace("\n", " ").replace("|", "/")  # remove newlines and pipe  
    log_entry = f"{user_id}|{now}|{clean_message}\n"  

    with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:  
        f.write(log_entry)  

    return JSONResponse(content={"status": "chat logged"})  

class FeedbackPayload(BaseModel):
    user_id: str
    engine: str
    model: str
    feedback: str

@app.post("/log-feedback/")
async def log_feedback(request: Request):
    data = await request.json()
    with open(ADMIN_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now()}] | User: {data['user_id']} | Model: {data['engine']} - {data['model']}\n")
        f.write(f"{data['message']}\n---\n")
    return {"status": "logged"}

# === ANALYSIS LOGGING ===  
@app.post("/log-analysis")  
def log_analysis(  
    user_id: str = Form(...),  
    engine: str = Form(...),        # gpt/gemini/offline/etc.  
    method: str = Form(...),        # pareto/fishbone/etc.  
    status: str = Form(...),        # success/failure  
    download: str = Form(...),      # Y/N  
    report: str = Form(...),        # Y/N  
):  
    now = datetime.now()  
    date_str = now.strftime("%Y-%m-%d")  
    time_str = now.strftime("%H:%M:%S")  

    log_line = f"{user_id}|{engine}|{method}|{date_str}|{time_str}|{status}|{download}|{report}\n"  

    with open(ISSUE_LOG_FILE, "a", encoding="utf-8") as f:  
        f.write(log_line)  

    return JSONResponse(content={"status": "analysis logged"})  

# === ADMIN DATA FILES ===
@app.get("/admin-data")
def read_admin_data():
    base_dir = "admin_data"
    if not os.path.exists(base_dir):
        return {"error": "admin_data folder not found"}

    data_files = [f for f in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, f))]
    return {"files": data_files}

from fastapi.responses import FileResponse

# === Serve All Core Files Individually (For Harmony_AI.py/.exe to pull remotely) ===

@app.get("/admin-log")
def serve_admin_log():
    return FileResponse(ADMIN_FILE)

@app.get("/demo-limit")
def serve_demo_limit():
    return FileResponse(DEMO_LIMIT_FILE)

@app.get("/user-list")
def serve_user_list():
    return FileResponse(USER_FILE)

@app.get("/chat-logs")
def serve_chat_logs():
    return FileResponse(USER_CHAT_LOG)

@app.get("/issue-log")
def serve_issue_logs():
    return FileResponse(USER_ISSUE_LOG)

@app.get("/access-list")
def serve_access_list():
    return FileResponse(DEMO_ACCESS_FILE)

@app.get("/consent-log")
def serve_consent_log():
    return FileResponse(CONSENT_LOG_PATH)

@app.get("/duplicate-logs")
def serve_duplicate_logs():
    return FileResponse(DUPLICATE_LOG_FILE)
