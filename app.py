"""Entrada compatible con despliegues Streamlit anteriores."""
from pathlib import Path
exec(compile((Path(__file__).parent/"streamlit_app.py").read_text(encoding="utf-8"),"streamlit_app.py","exec"))
