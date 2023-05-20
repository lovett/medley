import json
from httpx import Client, Response, Timeout, HTTPTransport
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

transport = HTTPTransport(retries=5)
timeout = Timeout(5.0, connect=10.0)

BASE = "http://localhost:8085"

basic_client = Client(
    base_url=BASE,
    timeout=timeout,
    transport=transport,
)

json_client = Client(
    base_url=BASE,
    timeout=timeout,
    transport=transport,
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
        try:
            print(highlight(
                json.dumps(response.json(), indent=4),
                JsonLexer(),
                Terminal256Formatter()
            ))
        except json.decoder.JSONDecodeError:
            print(response.content.decode())
