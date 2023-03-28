import json
from httpx import Client, Response
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

BASE = "http://localhost:8085"

basic_client = Client(
    base_url=BASE
)

json_client = Client(
    base_url=BASE,
    headers={
        "Accept": "application/json"
    }
)


def print_response(response: Response) -> None:
    """Display the headers and body of a response."""

    print(response.request.method, response.url)
    print(f"{response.status_code} {response.reason_phrase}")

    print("")

    for key, value in response.headers.items():
        print(f"{key}: {value}")

    print("")

    if response.content and response.headers:
        print(highlight(
            json.dumps(response.json(), indent=4),
            JsonLexer(),
            Terminal256Formatter()
        ))
