"""
Dispatches tasks through the tasks directory so they are not executed via shell 
"""
from tasks import filesystem
from tasks.sysinfo import get_sysinfo
from tasks.python_exec import execute_python

TASK_REGISTRY = {
    "list_directory": filesystem.list_directory,
    "read_file": filesystem.read_file,
    "write_file": filesystem.write_file,
    "delete_file": filesystem.delete_file,
    "sample_file": filesystem.sample_file,
    "get_sysinfo": get_sysinfo,
    "python_exec": execute_python
}

def execute_task(task):
    """ 
    Routes a task to the appropriate handler
    tasks = {
        "type" : str,
        "args" : dict
        }
    """
    task_type = task.get("type")
    
    if not task_type:
        return {
            "status": "error",
            "message": "Task type missing"
        }

    handler = TASK_REGISTRY.get(task_type) # find function to be executed
    if not handler:
        return {"status" : "error", "message": "Unknown task type"}
    
    args = task.get("args", {})
    
    try:
        return handler(args)
    
    except Exception as e:
        return {"status" : "error", "message" : f"Unhandled exception: {str(e)}"}


