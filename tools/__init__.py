import importlib
import os.path

module_dir = os.path.dirname(__file__)
module_name = os.path.basename(module_dir)

for item in os.listdir(module_dir):
    if item[0:2] == "__":
        continue

    if item[-3:] != ".py":
        continue

    importlib.import_module(".{}".format(item[:-3]), module_name)

del(module_dir)
del(module_name)
