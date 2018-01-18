import time
import functools
import cherrypy

def log_runtime_in_applog(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = f(*args, **kwargs)
        t1 = time.perf_counter()
        cherrypy.engine.publish(
            "applog:add",
            "{}.{}".format(f.__module__, f.__name__),
            "runtime",
            t1 - t0
        )
        return result
    return wrapper
