Overview

This project implements a basic Command and Control (C2) system consisting of:
	•	A server that queues tasks and receives results
	•	One or more agents that beacon, execute tasks, and return output
	•	A plaintext protocol augmented with payload-level encryption for confidentiality over the network

Encryption is intentionally limited in scope to preserve debuggability and protocol clarity.

⸻

Design Goals
	•	Prevent plaintext commands and output from appearing in network traffic
	•	Preserve existing C2 behavior and control flow
	•	Keep encryption failures non-fatal
	•	Enable future key-exchange and per-agent keys without refactoring core logic

This design prioritizes correctness, clarity, and extensibility over stealth or complexity.

⸻

Trust Model (Current Phase)

Assumptions:
	•	Agent and server are mutually trusted
	•	Operator is trusted
	•	Network is hostile (passive observation)
	•	Endpoints are not hardened against memory inspection

As a result:
	•	A pre-shared symmetric key is acceptable
	•	No handshake or key exchange is implemented yet

⸻

What Is Encrypted

Only payload contents are encrypted.

Encrypted
	•	Task command strings (server → agent)
	•	Command output strings (agent → server)

Not Encrypted
	•	HTTP endpoints
	•	HTTP methods
	•	JSON field names
	•	Agent ID
	•	Beacon timing and cadence

Encryption applies only to data crossing the network, not internal logic.

⸻

Message Flow

Operator → Server
	•	Operator submits a task via /api/push
	•	Task is stored in plaintext in server memory

Agent → Server (Beacon)
	•	Agent POSTs to /api/status
	•	Sends agent ID in plaintext
	•	Server checks task queue

Server → Agent (Tasking)
	•	If a task exists:
	•	Task string is encrypted
	•	Encrypted blob is returned in response
	•	Tasks are never stored encrypted

Agent Execution
	•	Agent decrypts task
	•	If decryption succeeds, task is executed
	•	If decryption fails, task is discarded

Agent → Server (Result)
	•	Agent encrypts command output
	•	Sends encrypted result to /api/upload

Server Processing
	•	Server decrypts result
	•	Output is printed or stored
	•	Decryption failure results in discard, not crash

⸻

Failure Behavior

Agent-Side

If task decryption fails:
	•	Task is dropped
	•	Agent continues beaconing
	•	No retries or execution attempts

Server-Side

If result decryption fails:
	•	Output is discarded
	•	Error is logged
	•	Agent state is preserved

Encryption failures affect messages, not processes.

⸻

Key Management (Current)
	•	One static symmetric key
	•	Hardcoded on both agent and server
	•	Loaded at startup
	•	No rotation

This is intentionally simple and will be replaced in later phases.

⸻

Debugging Strategy
	•	Encryption can be toggled on/off
	•	Encrypted blobs may be logged by length (not content)
	•	Beaconing remains plaintext to aid debugging

⸻

Known Limitations
	•	No replay protection
	•	No MITM resistance against active attackers
	•	Single shared key (full compromise if leaked)
	•	No forward secrecy

These are accepted tradeoffs for the current development phase.

⸻

Future Extensions

This design supports future improvements including:
	•	Handshake-based session keys
	•	Per-agent encryption keys
	•	Key rotation
	•	Encrypted beacon metadata
	•	Operator authentication

Because encryption is isolated at transport boundaries, these features can be added without redesigning core logic.

⸻

Acceptance Criteria

This design is considered successful when:
	•	Encrypted commands execute correctly
	•	Encrypted output returns correctly
	•	Incorrect keys cause task failure without crashing
	•	Agents continue beaconing under all conditions
	•	Network captures show no plaintext task or output data