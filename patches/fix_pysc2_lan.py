
"""Fix PySC2 LAN interface keyword compatibility."""

from pathlib import Path
import pysc2

path = Path(pysc2.__file__).parent / "env" / "lan_sc2_env.py"

old = "agent_interface_format=agent_interface_format, require_raw=visualize)"
new = "interface_format=agent_interface_format, require_raw=visualize)"

source = path.read_text()

if old in source:
    path.write_text(source.replace(old, new, 1))
    print(f"Patched: {path}")
elif new in source:
    print("Patch already applied")
else:
    raise RuntimeError("Unexpected PySC2 version")

