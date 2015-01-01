from time import time

Cache = {}

def get(key):
    value = Cache.get(key, (None, None))
    print("cache value: ", value)

    if type(value[1]) is float and value[1] < time():
        return None
    return value[0]

def set(key, value, expire=None):
    Cache[key] = (value, expire)

def clear():
    Cache.clear()
