import importlib
import os.path

module_dir = os.path.dirname(__file__)
module_name = os.path.basename(module_dir)

for item in os.listdir(module_dir):
    if item.startswith("__"):
        continue

    if item.startswith("test_"):
        continue

    if not item.endswith(".py"):
        continue

    importlib.import_module(".{}".format(item[:-3]), module_name)

del(module_dir)
del(module_name)
