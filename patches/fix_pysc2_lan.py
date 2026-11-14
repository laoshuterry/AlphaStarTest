cd /Volumes/MacExt/Developer/sc2-coach
mkdir -p patches

cat > patches/fix_pysc2_lan.py <<'PY'
"""PySC2 LAN compatibility fixes for the tested local environment.

PATCH-001: Fix _get_interface keyword argument.
PATCH-002: Initialize _requested_races for SC2Env.reset().

PATCH-002 is experimental. Human-vs-agent gameplay is not yet verified.
"""

from pathlib import Path
import pysc2

path = Path(pysc2.__file__).parent / "env" / "lan_sc2_env.py"
source = path.read_text(encoding="utf-8")
original = source

# PATCH-001: _get_interface() accepts interface_format, not
# agent_interface_format.
old_keyword = (
    "agent_interface_format=agent_interface_format, "
    "require_raw=visualize)"
)
new_keyword = (
    "interface_format=agent_interface_format, "
    "require_raw=visualize)"
)

if old_keyword in source:
    source = source.replace(old_keyword, new_keyword, 1)
    print("PATCH-001: applied")
elif new_keyword in source:
    print("PATCH-001: already applied")
else:
    raise RuntimeError("PATCH-001: unexpected source layout")

# PATCH-002: LAN environment does not initialize the attribute
# accessed by the inherited SC2Env.reset() method.
anchor = "    self._action_delay_fns = [None]"
addition = (
    anchor
    + "\n    # Experimental LAN compatibility fix.\n"
    + "    self._requested_races = {0: int(race)}"
)

if "self._requested_races = {0: int(race)}" in source:
    print("PATCH-002: already applied")
elif source.count(anchor) == 1:
    source = source.replace(anchor, addition, 1)
    print("PATCH-002: applied (experimental)")
else:
    raise RuntimeError("PATCH-002: unexpected source layout")

if source != original:
    path.write_text(source, encoding="utf-8")

print(f"Patch verification complete: {path}")
PY
