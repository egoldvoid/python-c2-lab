""" 
Run 
"""
from multiprocessing import Queue
import multiprocessing 



def execute_python(args):
    code = args.get(code)
    if not code:
        return {"status": "error", "message" : "No code provided"}
    
    local_scope = {}
    try:
        exec(code, {}, local_scope)
        return {
            "status" : "success",
            "output" : local_scope
        }
    except Exception as e:
        return {
            "status" : "error",
            "message" : str(e)
        }
        
    