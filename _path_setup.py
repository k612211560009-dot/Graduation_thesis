import sys
from pathlib import Path

# Walk up until we find config.py (= project root)
_here = Path(__file__).resolve().parent
_root = _here
for _ in range(5):          # max 5 levels up
    if (_root / "config.py").exists():
        break
    _root = _root.parent

if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
