from __future__ import annotations

import importlib
import inspect
import pkgutil
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).parent
    failures = []
    sys.path.insert(0, str(root.parent))
    for module_info in pkgutil.iter_modules([str(root)]):
        if not module_info.name.startswith("test_"):
            continue
        module = importlib.import_module(module_info.name)
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("test_"):
                try:
                    func()
                    print(f"ok {module_info.name}.{name}")
                except Exception as exc:
                    failures.append(f"{module_info.name}.{name}: {exc}")
                    print(f"FAIL {module_info.name}.{name}: {exc}")
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
