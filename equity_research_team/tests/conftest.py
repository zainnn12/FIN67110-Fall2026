import os
from pathlib import Path


os.environ["CREWAI_STORAGE_DIR"] = str(
    Path(__file__).resolve().parent / ".crewai-test-storage"
)
