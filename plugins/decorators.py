"""Decorators for use by plugins."""

from time import perf_counter
import functools
import cherrypy


def log_runtime(func):
    """Measure and store the runtime of a method call."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Calculate elapsed time and write to the applog."""

        source = '{}.{}.runtime'.format(
            func.__module__,
            func.__name__
        )
        start = perf_counter()
        result = func(*args, **kwargs)
        duration = perf_counter() - start

        cherrypy.engine.publish(
            'applog:add',
            source,
            'runtime',
            duration
        )

        return result

    return wrapper
