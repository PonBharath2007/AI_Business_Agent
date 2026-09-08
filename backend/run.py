import os
import sys
import subprocess
from pathlib import Path

# Ensure project root is in sys.path and PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if "PYTHONPATH" in os.environ:
    if str(ROOT_DIR) not in os.environ["PYTHONPATH"].split(os.pathsep):
        os.environ["PYTHONPATH"] = f"{ROOT_DIR}{os.pathsep}{os.environ['PYTHONPATH']}"
else:
    os.environ["PYTHONPATH"] = str(ROOT_DIR)

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    print(f"Starting AI Business Agent API from root: {ROOT_DIR} on {host}:{port}")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=True)
