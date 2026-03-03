import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT_FILE = os.path.join(PROJECT_ROOT, "agent.py")

def list_directory(args):
    path = args.get("path", ".")
    if not path:
        return {"status": "error", "message": "path is required"}
    
    try:
        files = os.listdir(path)
        return {"status": "success", "files" : files}
    
    except FileNotFoundError:
        return {"status": "error", "message": "Directory not found"}

    except NotADirectoryError:
        return {"status": "error", "message": "Path is not a directory"}

    except PermissionError:
        return {"status": "error", "message": "Permission denied"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def sample_file(args):
    """
     sample functionality, to read the first 5 lines of a function
    """
    path = args.get("path", ".")
    if not path:
        return {"status": "error", "message": "path is required"}
    try:
        with open(path, "r") as f:
            lines = []
            for _ in range(5):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip())
            f.read(5)
            return {
                "status": "success",
                "lines": lines
            }
            
    except FileNotFoundError:
        return {"status": "error", "message": "File not found"}

    except IsADirectoryError:
        return {"status": "error", "message": "Path is a directory"}

    except PermissionError:
        return {"status": "error", "message": "Permission denied"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
           
def read_file(args):
    path = args.get("path", ".")
    if not path:
        return {"status": "error", "message": "path is required"}
    
    try:
        with open(path, "r") as f:
            content = f.read(path, 1024*1024) # files can be 1 MB max at this point
            return {
                "status": "success",
                "content": content
            }

    except FileNotFoundError:
        return {"status": "error", "message": "File not found"}

    except IsADirectoryError:
        return {"status": "error", "message": "Path is a directory"}

    except PermissionError:
        return {"status": "error", "message": "Permission denied"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def write_file(args):
    path = args.get("path")
    content = args.get("content")
    if not path:
        return {"status": "error", "message": "path is required"}
    
    if content is None:
        return {"status": "error", "message": "content is required"}
    
    try:
        with open(path, "w") as f:
            f.write(content)
        return {
            "status": "success",
            "message": "File written successfully"
        }
        
    except PermissionError:
        return {"status": "error", "message": "Permission denied"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def delete_file(args):
    """
    Delete file, with guardrails to prevent deletion of agent itself, 
                    as that would defeat the purpose
    """
    path = args.get("path")
    if not path: 
        return {"status": "error", "message": "path is required"}
    
    target = os.path.abspath(path)
    if target == os.path.abspath(AGENT_FILE):
        return {"status": "error", "message": "Cannot delete agent file"}

    if os.path.commonpath([target, PROJECT_ROOT]) == PROJECT_ROOT:
         return {"status": "error", "message": "Cannot delete files inside agent directory"}
     
    try: 
        os.remove(target)
        return {
            "status": "success",
            "message": "File deleted successfully"
        }
        
    except FileNotFoundError:
        return {"status": "error", "message": "File not found"}

    except IsADirectoryError:
        return {"status": "error", "message": "Path is a directory"}

    except PermissionError:
        return {"status": "error", "message": "Permission denied"}

    except Exception as e:
        return {"status": "error", "message": str(e)}