"""Run one recipe from the command line or from the local web server."""

import json
import sys

from canvaslib.client import CanvasClient, CanvasError


def run_recipe(run):
    """Run a recipe and return (result, error_message). One of them is None."""
    try:
        return run(CanvasClient.from_env()), None
    except CanvasError as err:
        return None, str(err)


def main(run):
    """Entry point used by each recipe's `python -m recipes.<name>` command."""
    result, error = run_recipe(run)
    if error:
        sys.exit(f"ERROR: {error}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
