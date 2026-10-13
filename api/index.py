import sys
import os
from pathlib import Path

# Add project root to sys.path so imports work smoothly in serverless runtime
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app import app
