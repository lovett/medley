"""Decorators for use by plugins."""

from time import perf_counter
import functools
import typing
import cherrypy

FuncType = typing.Callable[..., typing.Any]
Func = typing.TypeVar('Func', bound=FuncType)


def log_runtime(func: Func) -> Func:
    """Measure and store the runtime of a method call."""

    @functools.wraps(func)
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """Calculate and store elapsed time."""

        start = perf_counter()
        result = func(*args, **kwargs)

        cherrypy.engine.publish(
            "metrics:add",
            f"runtime:{func.__module__}:{func.__name__}",
            round((perf_counter() - start) * 1000),
            "ms"
        )

        return result

    return typing.cast(Func, wrapper)
