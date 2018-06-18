"""Import all plugin submodules."""

import importlib
import os.path

MODULE_DIR = os.path.dirname(__file__)
MODULE_NAME = os.path.basename(MODULE_DIR)

for item in os.listdir(MODULE_DIR):
    if item.startswith("__"):
        continue

    if item.startswith("."):
        continue

    if item.startswith("mixins"):
        continue

    if item.startswith("decorators"):
        continue

    if item.startswith("test_"):
        continue

    if not item.endswith(".py"):
        continue

    importlib.import_module(".{}".format(item[:-3]), MODULE_NAME)

del MODULE_DIR
del MODULE_NAME
