
"""Patch PySC2 random.shuffle compatibility for Python 3.11+."""

from pathlib import Path
import pysc2

path = Path(pysc2.__file__).parent / "lib" / "colors.py"

old = "random.shuffle(palette, lambda: 0.5)"

new = """for i in range(len(palette) - 1, 0, -1):
        j = int(0.5 * (i + 1))
        palette[i], palette[j] = palette[j], palette[i]"""

source = path.read_text()

if old in source:
    path.write_text(source.replace(old, new, 1))
    print(f"Patched: {path}")
elif new in source:
    print("Patch already applied")
else:
    raise RuntimeError(
        "Unknown PySC2 source version; patch not applied."
    )

