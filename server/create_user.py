#!/usr/bin/env python3
"""
Manage operator credentials in the SQLite credential store.
Usage:
    python3 -m server.create_user                        # create/update 'admin'
    python3 -m server.create_user --username <name>
    python3 -m server.create_user --delete <name>
    python3 -m server.create_user --list
    python3 -m server.create_user --gen-agent-key
"""
import argparse
import getpass
import os
import secrets
import sys

AGENT_KEY_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "agent_key")


def cmd_create(username: str):
    from server.db import init_db, create_user
    init_db()

    password = getpass.getpass(f"Password for '{username}': ")
    confirm  = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("[!] Passwords do not match.")
        sys.exit(1)
    if len(password) < 12:
        print("[!] Password must be at least 12 characters.")
        sys.exit(1)

    create_user(username, password)
    print(f"[+] User '{username}' saved to credential store.")


def cmd_delete(username: str):
    from server.db import init_db, delete_user
    init_db()
    delete_user(username)
    print(f"[+] User '{username}' deleted.")


def cmd_list():
    from server.db import init_db, list_users
    import datetime
    init_db()
    users = list_users()
    if not users:
        print("No users in credential store.")
        return
    print(f"{'Username':<20} {'Created':<22} {'Last Login'}")
    print("-" * 60)
    for u in users:
        created    = datetime.datetime.fromtimestamp(u["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
        last_login = datetime.datetime.fromtimestamp(u["last_login"]).strftime("%Y-%m-%d %H:%M:%S") if u["last_login"] else "never"
        print(f"{u['username']:<20} {created:<22} {last_login}")


def cmd_gen_agent_key():
    os.makedirs(os.path.dirname(AGENT_KEY_FILE), exist_ok=True)
    key = secrets.token_hex(32)
    with open(AGENT_KEY_FILE, "w") as f:
        f.write(key)
    os.chmod(AGENT_KEY_FILE, 0o600)
    print(f"[+] Agent key written to {AGENT_KEY_FILE}  (mode 600)")
    print(f"    {key}")
    print("    Copy config/agent_key to the agent host, or export C2_AGENT_KEY=<key>")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username",      default="admin", help="Username to create/update")
    parser.add_argument("--delete",        metavar="USERNAME", help="Delete a user")
    parser.add_argument("--list",          action="store_true", help="List all users")
    parser.add_argument("--gen-agent-key", action="store_true", help="Generate a new agent key")
    args = parser.parse_args()

    if args.gen_agent_key:
        cmd_gen_agent_key()
    elif args.delete:
        cmd_delete(args.delete)
    elif args.list:
        cmd_list()
    else:
        cmd_create(args.username)
