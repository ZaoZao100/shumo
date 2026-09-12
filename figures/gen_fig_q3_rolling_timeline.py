"""v3 canonical generator; old source archived under sources/v2_*.py."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("gen_v3_figures.py")),run_name="__main__")
