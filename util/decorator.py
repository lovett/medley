import time
import functools

def timed(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.time()
        result = f(*args, **kwargs)
        t1 = time.time()
        return (result, t1-t0)

    return wrapper

def hideFromHomepage(f):
    f.hide_from_homepage = True
    return f
