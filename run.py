import os
import sys
import subprocess
from pathlib import Path

# Ensure project root is in sys.path and PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if "PYTHONPATH" in os.environ:
    if str(ROOT_DIR) not in os.environ["PYTHONPATH"].split(os.pathsep):
        os.environ["PYTHONPATH"] = f"{ROOT_DIR}{os.pathsep}{os.environ['PYTHONPATH']}"
else:
    os.environ["PYTHONPATH"] = str(ROOT_DIR)

if __name__ == "__main__":
    import uvicorn
    print(f"Starting AI Business Agent API from root: {ROOT_DIR}")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
