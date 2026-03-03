
from multiprocessing import Queue
import multiprocessing
import io
import sys
import time

def _python_worker(code, queue):
    
    local_scope = {}
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # prevent things such as open, exec, eval, __import__, input, globals, locals
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

    try:
        timeout = args.get("timeout", 5)
    except:
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
        
    