"""Root conftest — ensures src/ is on PYTHONPATH for test discovery."""
import os
import sys
from pathlib import Path

# --- OpenMP multi-library guard (v3.4.58) ----------------------------------
# Must be set BEFORE any test module imports torch / sklearn / lightgbm.
# Without this, test collection itself can trigger the libomp SIGSEGV on
# macOS ARM when pytest imports test files that have top-level lgb imports.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
if "OMP_NUM_THREADS" not in os.environ:
    os.environ["OMP_NUM_THREADS"] = "2"
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).parent / "src"))
