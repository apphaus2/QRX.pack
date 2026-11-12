"""The archetypes: one module per kind of animal. A module dropped in this folder is found by name."""
import importlib, pkgutil


def load():
    """{name: module} for every archetype in this package."""
    return {info.name: importlib.import_module(__name__ + "." + info.name) for info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name)}
