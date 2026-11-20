"""Import the bot without reading deployment credentials."""

import sys
from contextlib import contextmanager
from types import ModuleType

__all__ = ["app", "googleapi", "inert_credentials", "mechanics"]


@contextmanager
def inert_credentials():
    settings = ModuleType("privatevars")
    settings.TOKEN = settings.DBUSER = settings.DBPASS = "test"
    original = sys.modules.get("privatevars")
    sys.modules["privatevars"] = settings
    try:
        yield
    finally:
        if original is None:
            del sys.modules["privatevars"]
        else:
            sys.modules["privatevars"] = original


with inert_credentials():
    import bot as app
    from cogs import googleapi, mechanics
