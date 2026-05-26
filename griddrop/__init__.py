__all__ = ["setup"]

def __getattr__(name):
    if name == "setup":
        from .core import setup
        return setup
    raise AttributeError(...)