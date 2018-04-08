from time import perf_counter
import functools
import cherrypy


def log_runtime(f):
    """Calculate elapsed time and write to the cherrypy log."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        source = '{}.{}'.format(f.__module__, f.__name__)
        start = perf_counter()
        result = f(*args, **kwargs)
        duration = perf_counter() - start
        cherrypy.log(" {} ran in {}".format(
            source, duration
        ))

        return result

    return wrapper


def log_runtime_in_applog(f):
    """Calculate elapsed time and write to the applog."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        source = '{}.{}'.format(f.__module__, f.__name__)
        start = perf_counter()
        result = f(*args, **kwargs)
        duration = perf_counter() - start

        cherrypy.engine.publish(
            'applog:add',
            source,
            'runtime',
            duration
        )

        return result

    return wrapper
