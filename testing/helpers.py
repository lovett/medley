"""Utility functions to make unit tests easier."""

import pathlib
import tempfile
import typing
from unittest import mock
import cherrypy
import plugins.jinja
import tools.etag


def get_fixture(path: str) -> str:
    """Return the contents of a file in the fixtures directory."""
    with open("testing/fixtures/" + path, "r", encoding="utf-8") as handle:
        return handle.read()


def start_server(app: typing.Callable) -> None:
    """Create a cherrypy server for testing an app.

    The app is always mounted at the URL root so that URL references
    aren't dependent on the app's name.

    """

    server_root = pathlib.Path(__file__).parents[1]

    cherrypy.config.update({
        "server_root": server_root,
        "database_dir": tempfile.gettempdir(),
    })

    cherrypy.tools.etag = tools.etag.Tool()

    cherrypy.tree.mount(app(), "/", {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
        }
    })

    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    cherrypy.engine.start()


def stop_server() -> None:
    """Shut down the cherrypy server used by the current test suite."""
    cherrypy.engine.exit()


def response_is_html(res: cherrypy.response) -> bool:
    """Test a response object for an HTML content type header"""
    return header_is(res.headers, "Content-Type", "text/html;charset=utf-8")


def response_is_json(res: cherrypy.response) -> bool:
    """Test a response object for an JSON content type header"""
    return header_is(res.headers, "Content-Type", "application/json")


def response_is_text(res: cherrypy.response) -> bool:
    """Test a response object for a plain text content type header"""
    return header_is(res.headers, "Content-Type", "text/plain;charset=utf-8")


def header_is(
        headers: typing.Dict[str, str],
        name: str,
        expected_value: str
) -> bool:
    """Test a dict of headers for an expected name/value pair"""
    header_value = headers.get(name)
    return expected_value == header_value


def template_var(publish_mock: mock.Mock, key: str) -> typing.Any:
    """Retrieve a template variable passed to jinja:render."""

    for call in publish_mock.call_args_list:
        if call[0][0] != "jinja:render":
            continue
        return call[1].get(key)


def find_publish_call(
        publish_mock: mock.Mock,
        subscription_topic: str
) -> typing.Any:
    """Find a topic in the call list of a mock of cherrypy.engine.publish."""
    for call in publish_mock.call_args_list:
        if call[0][0] == subscription_topic:
            return call
    return None
