from typing import Dict
from typing import Union
from typing import Optional
from typing import Callable


def encode(
        payload: Dict[str, Union[str, int]],
        key: str,
        algorithm: Optional[str] = "HS256",
        headers: Optional[Dict[str, Union[str, int]]] = None,
        json_encoder: Optional[Callable] = None,
) -> str: ...
