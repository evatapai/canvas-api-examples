"""Recipe registry. Every module named like 01_auth.py is a recipe."""

import importlib
import pkgutil
from pathlib import Path


def discover():
    """Return every recipe as a dict, sorted by module name."""
    names = sorted(m.name for m in pkgutil.iter_modules(__path__) if m.name[0].isdigit())
    recipes = []
    for name in names:
        module = importlib.import_module(f"{__name__}.{name}")
        recipes.append(
            {
                "id": name,
                "title": module.TITLE,
                "description": module.DESCRIPTION,
                "writes": getattr(module, "WRITES", False),
                "source": Path(module.__file__).read_text(),
                "run": module.run,
            }
        )
    return recipes
