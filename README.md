# Python C2 Architecture Lab

An educational command-and-control (C2) system built in Python, intended strictly for learning about cybersecurity concepts — C2 architecture, encrypted transport, authentication, and distributed task execution.

Credit: [Building a Custom C2 Server in Python](https://medium.com/maxwell-cross-python-for-red-teaming/building-a-custom-c2-server-in-python-a-fresh-take-on-offensive-security-e3d8c09bc2ab) for the original idea and architecture.

> **Warning**: This project is for authorized educational and research use only.

---

## Architecture

```
Operator CLI ──► Server (Flask) ◄── Web Dashboard
                     │
                  (HTTP + Fernet encryption)
                     │
                  Agent(s)
```

- **Server** (`server/`) — Flask app that queues tasks, tracks agents, and serves a web dashboard
- **Agent** (`agent/`) — Beacons periodically, pulls tasks, executes them, and posts results back
- **Operator CLI** (`controller/`) — Authenticated CLI for dispatching tasks and listing agents
- **Common** (`common/`) — Shared Fernet encryption helpers

---

## Features

- Encrypted payload transport (Fernet — AES-128-CBC + HMAC-SHA256)
- Persistent agent identity (UUID stored across restarts)
- Agent heartbeat and online/offline status tracking
- Token-based operator authentication (8-hour sessions)
- Rate-limited login endpoint (10 attempts / 60s per IP)
- Web dashboard with auto-refresh (every 5 seconds)
- Modular task system: filesystem, sysinfo, Python execution
- Exfiltration staging with size limits
- Encrypted-at-rest credential store (pbkdf2:sha256:600000 + Fernet)

---

## Project Structure

```
c2/
├── server/
│   ├── app.py              # Flask server — API endpoints, task queue, agent registry
│   ├── auth.py             # Token generation and validation
│   ├── db.py               # SQLite credential store (encrypted at rest)
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
│   └── credentials.db      # SQLite operator store
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

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" \
    > config/shared_key
chmod 600 config/shared_key
```

Copy `config/shared_key` to any agent host, or export it as `C2_SHARED_KEY` on both sides.

### 2 — Generate the agent authentication key

```bash
python3 -m server.create_user --gen-agent-key
```

Copy `config/agent_key` to the agent host, or export as `C2_AGENT_KEY`.

### 3 — Create an operator account

```bash
python3 -m server.create_user                   # creates 'admin'
python3 -m server.create_user --username alice  # creates 'alice'
```

Password must be at least 12 characters.

### 4 — Start the server

```bash
python3 -m server.app
```

Listens on `0.0.0.0:5000`. Web dashboard at `http://localhost:5000`.

### 5 — Start an agent

```bash
python3 -m agent.agent
```

Beacons every 10–30 seconds (jittered). Prints its UUID on startup.

---

## Operator CLI

```bash
# Authenticate
python3 -m controller.operator login
python3 -m controller.operator logout

# List active agents
python3 -m controller.operator agents

# Push a task
python3 -m controller.operator exec <AGENT_ID> <TASK_TYPE> [--args '<JSON>']
```

See `SAMPLE_COMMANDS.md` for a full task reference with examples.

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
| `exfil_file` | `path` | 5 MB max; saved to `exfil/` on server |

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
| POST | `/api/login` | Exchange credentials for session token |
| GET | `/api/agents` | List all agents |
| GET | `/api/tasks?agent_id=<ID>` | Get task queue for an agent |
| POST | `/api/push` | Queue a task for an agent |
| DELETE | `/api/tasks?agent_id=<ID>` | Clear all tasks for an agent |

### Agent (`X-Agent-Key` header required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/status` | Beacon; returns next pending task |
| POST | `/api/upload` | Post encrypted task result |

---

## Configuration

### Environment Variables

| Variable | Purpose | Fallback |
|----------|---------|----------|
| `C2_SHARED_KEY` | Fernet key (base64) | Reads `config/shared_key` |
| `C2_AGENT_KEY` | Agent auth key (hex) | Reads `config/agent_key` |
| `C2_SECRET_KEY` | Token signing key (hex) | Ephemeral (tokens lost on restart) |

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
python3 -m server.create_user --gen-agent-key   # rotate agent key
```

---

## Security Notes

- **No TLS**: The server runs plain HTTP; use a trusted network or add a reverse proxy for TLS.
- **In-memory state**: Task queues and agent registry are lost on server restart.
- **No replay protection**: Encrypted payloads can be replayed by a network observer.
- **Single shared key**: Full compromise if the Fernet key is leaked.
- **Python sandbox**: `python_exec` restricts obvious escapes but is not a hardened sandbox.

These are accepted tradeoffs for a learning project. See `DESIGN.md` for details on the encryption model and its known limitations.
