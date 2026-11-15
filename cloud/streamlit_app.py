"""Streamlit Community Cloud entrypoint: public data only, no credentials required."""
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['TRENDLENS_PUBLIC'] = '1'
runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')
