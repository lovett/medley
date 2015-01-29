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

def userFacing(f):
    f.userFacing = True
    return f
