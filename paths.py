"""
Central path definitions for all scripts.

These paths point to the shared data directories used throughout the pipeline.
"""
from pathlib import Path

# Root path for the project
ROOT = Path("/data/openreal2sim")

# Base path for reconstruction outputs organized by week/author
# Structure: RECONSTRUCTIONS/<week>/<author>/<key>/
RECONSTRUCTIONS = ROOT / "reconstructions"
HUNYUAN = RECONSTRUCTIONS / "hunyuan"
SAM = RECONSTRUCTIONS / "sam"
# Base path for intermediate outputs before moving to reconstructions
# Structure: ESTEBAN_OUTPUTS/<key>/
ESTEBAN_OUTPUTS = ROOT / "esteban" / "outputs"

TOOLS_PATH = ROOT / "tools"

FIREBASE_PATH = TOOLS_PATH / "config" / "firebase.json"
