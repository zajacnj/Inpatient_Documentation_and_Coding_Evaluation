"""Uvicorn entrypoint exposing app for reload/workers."""

from importlib import util
from pathlib import Path


def _load_app():
    app_path = Path(__file__).parent / "app.py"
    spec = util.spec_from_file_location("app_main", app_path)
    module = util.module_from_spec(spec)
    if spec and spec.loader:
        spec.loader.exec_module(module)
    return module.app


app = _load_app()
