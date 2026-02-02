from typing import Any, Callable

class MarkDecorator:
    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]: ...

class Mark:
    asyncio: MarkDecorator

mark: Mark

def approx(value: Any, rel: float | None = ..., abs: float | None = ...) -> Any: ...
