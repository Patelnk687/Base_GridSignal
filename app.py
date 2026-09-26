"""Streamlit entry point. Run: streamlit run app.py"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit Cloud installs requirements.txt; ensure src/ is importable even if
# the editable install is skipped for any reason.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gridsignal.ui.dashboard import main

if __name__ == "__main__":
    main()
