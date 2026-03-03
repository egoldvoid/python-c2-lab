import platform
import os
import psutil
import time 
import datetime

def get_sysinfo(args):
    try:
        return {
            "status": "success",
            "os": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_env(args):
    try: 
        return {
            {"status": "success",
             "env" : dict(os.environ)}
        }
    except Exception as e:
         return {"status": "error", "message": str(e)}
     
def get_uptime(args):
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time

        return {
            "status": "success",
            "boot_time": boot_time,
            "uptime_seconds": uptime_seconds,
            "uptime_timedelta": str(datetime.timedelta(seconds=int(uptime_seconds)))
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def get_proccesses(args):
    
    try: 
        limit = args.get("limit", 50) 
        
        if not isinstance(limit, int):
            return {"status": "error", "message": "limit must be an integer"}
        if limit <= 0:
            return {"status": "error", "message": "limit must be an integer"}
        
        if limit > 500:
            limit = 500 # set a hard limit for concurrent processes
        
        processes = []
        for i, proc in enumerate(psutil.process_iter(['pid'], ['name'])):
            if i >= limit:
                break
            processes.append(proc.info)
            
        return {
            "status": "success",
            "count" : len(processes),
            "processes": processes
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    