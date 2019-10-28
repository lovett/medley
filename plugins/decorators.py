"""Decorators for use by plugins."""

from time import perf_counter
import functools
import cherrypy


def log_runtime(func):
    """Measure and store the runtime of a method call."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Calculate elapsed time and write to the applog."""

        start = perf_counter()
        result = func(*args, **kwargs)

        cherrypy.engine.publish(
            "applog:add",
            "runtime",
            f"{func.__module__}.{func.__name__}",
            perf_counter() - start
        )

        return result

    return wrapper
