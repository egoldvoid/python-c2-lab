
from multiprocessing import Queue
import multiprocessing
import io
import sys
import time

def _python_worker(code, queue):
    
    local_scope = {}
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # Restricted builtins prevent naive escapes (open, exec, __import__, etc.)
    # but do NOT stop introspection-based escapes such as:
    #   ().__class__.__bases__[0].__subclasses__()
    # The multiprocessing.Process boundary is the real isolation layer —
    # treat any submitted code as having full access to the agent's environment.
    safe_builtins = {
        "print": print,
        "len": len,
        "range": range,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
    }
    
    try: 
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        start_time = time.time()
        exec(code, {"__builtins__" : safe_builtins}, local_scope)
        execution_time = time.time() - start_time
        
        result = local_scope.get("result")
        
        queue.put({
            "status": "success",
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "result": result,
            "execution_time": execution_time
        })

    except Exception as e:
        queue.put({
            "status": "error",
            "message": str(e),
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue()
        })

    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
        
    
def execute_python(args):
    code = args.get("code")

    if not code:
        return {"status": "error", "message": "code is required"}

    timeout = args.get("timeout", 5)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        timeout = 5

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_python_worker,
        args=(code, queue)
    )

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        return {"status": "error", "message": "Execution timed out"}

    try:
        return queue.get_nowait()
    
    except:
        return {"status": "error", "message": "No result returned"}
        
    