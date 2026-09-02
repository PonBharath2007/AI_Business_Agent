import sys
import os
from pathlib import Path

# Add project root to sys.path so backend imports work seamlessly on Vercel
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
