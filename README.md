# Python C2 Architecture Lab

An educational command-and-control (C2) system built in Python, intended strictly for learning about cybersecurity concepts — C2 architecture, encrypted transport, authentication, and distributed task execution.

Credit: [Building a Custom C2 Server in Python](https://medium.com/maxwell-cross-python-for-red-teaming/building-a-custom-c2-server-in-python-a-fresh-take-on-offensive-security-e3d8c09bc2ab) for the original idea and architecture.

> **Warning**: This project is for authorized educational and research use only. Do not deploy against systems you do not own or have explicit written permission to test.

---

## What is a C2?

A **command-and-control (C2) framework** is the infrastructure used in adversarial security operations (red teaming, penetration testing) to manage remote access to target systems. Understanding how C2s work is foundational to both offensive security research and defensive detection engineering.

A C2 system has three main components:

| Component | Role |
|-----------|------|
| **Server** | Central hub. Receives beacons from agents, queues tasks, stores results. |
| **Agent** | Runs on the target host. Periodically checks in ("beacons"), executes tasks, and posts results back. |
| **Operator** | The human controller. Issues commands via a CLI or dashboard. |

The core operational loop:
1. The operator pushes a task to the server for a specific agent.
2. The agent beacons, receives the task (encrypted), and executes it.
3. The agent posts the encrypted result back to the server.
4. The operator retrieves and reads the result.

This project implements that loop with realistic security properties: encrypted transport, token-based authentication, rate limiting, and a persistent SQLite backend.

---

## Architecture

```
Operator CLI ──► Server (Flask + SQLite) ◄── Web Dashboard
                          │
               (HTTP + Fernet symmetric encryption)
                          │
                      Agent(s)
```

- **Server** (`server/`) — Flask app. Manages agent registry, task queue, and results. All state is persisted in SQLite and survives restarts.
- **Agent** (`agent/`) — Beacons on a jittered interval, receives and decrypts tasks, executes them, and posts encrypted results.
- **Operator CLI** (`controller/`) — Authenticated CLI for dispatching tasks and inspecting agents.
- **Common** (`common/`) — Shared Fernet encryption/decryption helpers used by both server and agent.

---

## Features

- Encrypted payload transport (Fernet — AES-128-CBC + HMAC-SHA256)
- Persistent agent identity (UUID written to disk, survives agent restarts)
- Agent heartbeat and online/offline status tracking
- Token-based operator authentication (8-hour sessions)
- Rate-limited login endpoint (10 attempts / 60s per IP)
- Web dashboard with auto-refresh (every 5 seconds)
- Modular task system: filesystem, sysinfo, Python execution
- Exfiltration staging with size limits
- Encrypted-at-rest credential store (pbkdf2:sha256:600000 + Fernet)
- **SQLite-backed task store** — task queue, lifecycle state, and results persist across server restarts

---

## Task Lifecycle

Every task moves through these stages:

```
queued ──► delivered ──► completed
```

| Stage | Meaning |
|-------|---------|
| `queued` | Task was pushed by the operator; waiting for the agent to beacon |
| `delivered` | Server handed the task to the agent on its last beacon |
| `completed` | Agent posted a result back; result is stored in the DB |

Tasks are stored with full timestamps (`created_at`, `delivered_at`, `completed_at`) so you can reason about latency and delivery at each stage.

---

## Project Structure

```
c2/
├── server/
│   ├── app.py              # Flask server — API endpoints, task queue, agent registry
│   ├── auth.py             # Token generation and validation
│   ├── db.py               # SQLite store: credentials, tasks, and agent registry
│   ├── create_user.py      # CLI tool: manage operators and agent key
│   └── templates/
│       ├── index.html      # Web dashboard
│       └── login.html      # Operator login page
├── agent/
│   ├── agent.py            # Beacon loop and task orchestration
│   ├── dispatcher.py       # Task type routing registry
│   └── tasks/
│       ├── filesystem.py   # list, read, write, delete, sample, exfil
│       ├── sysinfo.py      # OS info, env vars, uptime, processes
│       └── python_exec.py  # Sandboxed Python execution with timeout
├── controller/
│   └── operator.py         # CLI: login, logout, agents, exec
├── common/
│   └── cryptography_helpers.py  # Fernet encrypt/decrypt utilities
├── config/                 # Secrets directory (git-ignored)
│   ├── shared_key          # Fernet symmetric key (server + agent)
│   ├── agent_key           # Agent authentication pre-shared key
│   ├── db_key              # Database encryption key (auto-generated)
│   └── credentials.db      # SQLite store: users, tasks, agent registry
├── exfil/                  # Staging directory for exfiltrated files
├── DESIGN.md               # Encryption and protocol design notes
└── SAMPLE_COMMANDS.md      # Full operator command reference
```

---

## Setup

### Prerequisites

- Python 3.10+
- `pip install flask cryptography requests psutil`

### 1 — Generate the shared encryption key

The server and every agent must share the same Fernet key. This key encrypts all task payloads in transit.

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" \
    > config/shared_key
chmod 600 config/shared_key
```

Copy `config/shared_key` to any agent host (same relative path), or export it as an environment variable on both sides:

```bash
export C2_SHARED_KEY=$(cat config/shared_key)
```

### 2 — Generate the agent authentication key

Agents authenticate to the server using a pre-shared key sent in the `X-Agent-Key` header. Without this, the server rejects beacon and upload requests.

```bash
python3 -m server.create_user --gen-agent-key
```

Copy `config/agent_key` to the agent host, or export:

```bash
export C2_AGENT_KEY=$(cat config/agent_key)
```

### 3 — Create an operator account

```bash
python3 -m server.create_user                   # creates 'admin'
python3 -m server.create_user --username alice  # creates 'alice'
```

Password must be at least 12 characters. Passwords are hashed with pbkdf2:sha256:600000 and the hash is Fernet-encrypted before being written to the database.

### 4 — Start the server

```bash
python3 -m server.app
```

Listens on `0.0.0.0:5000`. Web dashboard at `http://localhost:5000`.

Set `C2_SECRET_KEY` to a stable hex value if you want operator tokens to survive server restarts:

```bash
export C2_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
python3 -m server.app
```

### 5 — Start an agent

```bash
python3 -m agent.agent
```

The agent writes its UUID to `agent/.agent_id` on first run and reuses it on subsequent runs, giving it a stable identity across restarts. It beacons every 10–30 seconds (jittered).

---

## Operator CLI

```bash
# Authenticate (saves token to controller/.operator_token)
python3 -m controller.operator login
python3 -m controller.operator logout

# List agents and their status
python3 -m controller.operator agents

# Push a task
python3 -m controller.operator exec <AGENT_ID> <TASK_TYPE> [--args '<JSON>']
```

See `SAMPLE_COMMANDS.md` for a complete task reference with examples.

---

## Available Tasks

### Filesystem

| Task | Required args | Notes |
|------|---------------|-------|
| `list_directory` | `path` | |
| `read_file` | `path` | 1 MB max |
| `sample_file` | `path` | First 5 lines |
| `write_file` | `path`, `content` | |
| `delete_file` | `path` | Agent files are protected |
| `exfil_file` | `path` | 5 MB max; saved to `exfil/<agent_id>_<filename>` on server |

### System Info

| Task | Args | Notes |
|------|------|-------|
| `get_sysinfo` | — | OS, kernel, arch, Python version |
| `get_env` | — | Full environment variable dump |
| `get_uptime` | — | Boot time and uptime in seconds |
| `get_processes` | `limit` (optional, max 500) | Default 50 |

### Execution

| Task | Required args | Notes |
|------|---------------|-------|
| `python_exec` | `code` | `timeout` optional (default 5s); restricted builtins |

---

## API Endpoints

### Operator (Bearer token required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/login` | Exchange credentials for a session token |
| GET | `/api/agents` | List all registered agents with status |
| GET | `/api/tasks?agent_id=<ID>` | Get all tasks for an agent |
| POST | `/api/push` | Queue a task for an agent |
| DELETE | `/api/tasks?agent_id=<ID>` | Clear all tasks for an agent |

### Agent (`X-Agent-Key` header required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/status` | Beacon; registers/updates agent, returns next queued task |
| POST | `/api/upload` | Post encrypted task result |

---

## Configuration

### Environment Variables

| Variable | Purpose | Fallback |
|----------|---------|----------|
| `C2_SHARED_KEY` | Fernet key (base64) | Reads `config/shared_key` |
| `C2_AGENT_KEY` | Agent auth key (hex) | Reads `config/agent_key` |
| `C2_SECRET_KEY` | Token signing key (hex) | Ephemeral — tokens are lost on server restart |

### Limits

| Limit | Value |
|-------|-------|
| Max queued tasks per agent | 100 |
| Exfil file size | 5 MB |
| `read_file` size | 1 MB |
| `python_exec` default timeout | 5 seconds |
| Login rate limit | 10 attempts / 60s per IP |
| Operator session TTL | 8 hours |
| Agent offline threshold | 60 seconds without beacon |

---

## Credential Management

```bash
python3 -m server.create_user                   # create/update 'admin'
python3 -m server.create_user --username alice  # create/update 'alice'
python3 -m server.create_user --delete alice    # delete user
python3 -m server.create_user --list            # list all users + last login
python3 -m server.create_user --gen-agent-key   # rotate the agent authentication key
```

---

## Security Notes

- **No TLS**: The server runs plain HTTP. Use a trusted local network, VPN, or add a TLS-terminating reverse proxy (nginx, caddy) for any real use.
- **No replay protection**: A network observer who captures an encrypted payload can replay it. Mitigation would require nonces or sequence numbers.
- **Single shared key**: If the Fernet key in `config/shared_key` is leaked, all past and future traffic can be decrypted.
- **Python sandbox**: `python_exec` restricts obvious escape paths but is not a hardened sandbox. Do not run untrusted code.
- **Ephemeral tokens**: Without `C2_SECRET_KEY` set, all operator sessions are invalidated when the server restarts.

These are accepted tradeoffs for a learning project. See `DESIGN.md` for a deeper discussion of the encryption model and its known limitations.
