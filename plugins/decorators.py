"""Decorators for use by plugins."""

from time import perf_counter
import functools
from typing import Any
from typing import Callable
from typing import TypeVar
from typing import cast
import cherrypy

FuncType = Callable[..., Any]
Func = TypeVar("Func", bound=FuncType)


def log_runtime(func: Func) -> Func:
    """Measure and store the runtime of a method call."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
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

    return cast(Func, wrapper)
