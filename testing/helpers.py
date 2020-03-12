"""Utility functions to make unit tests easier."""

import pathlib
import tempfile
import typing
import unittest
import unittest.mock
import cherrypy
import plugins.jinja
import apps.shared.main
import tools.etag


def get_fixture(path: str) -> str:
    """Return the contents of a file in the fixtures directory."""
    with open("testing/fixtures/" + path) as handle:
        return handle.read()


def start_server(app: typing.Callable) -> None:
    """Create a cherrypy server for testing an app.

    The app is always mounted at the URL root so that URL references
    aren't dependent on the app's name.

    """

    server_root = pathlib.Path(__file__).parents[1]

    cherrypy.config.update({
        "app_root": server_root / "apps",
        "server_root": server_root,
        "database_dir": tempfile.gettempdir(),
    })

    cherrypy.tree.mount(app(), "/", {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
        }
    })

    # Always load the shared app
    cherrypy.tree.mount(
        apps.shared.main.Controller,
        "/shared",
        {}
    )

    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    cherrypy.tools.etag = tools.etag.Tool()
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


def html_var(mock: unittest.mock.Mock, key: str) -> typing.Any:
    """Retrieve a template variable from the HTML portion of a response."""
    return mock.call_args[0][0]["html"][1].get(key)


def text_var(mock: unittest.mock.Mock) -> typing.Any:
    """Retrieve a template variable from the text portion of a response."""
    return mock.call_args[0][0]["text"]


def find_publish_call(
        mock: unittest.mock.Mock,
        subscription_topic: str
) -> typing.Any:
    """Find a topic in the call list of a mock of cherrypy.engine.publish."""
    for call in mock.call_args_list:
        if call[0][0] == subscription_topic:
            return call
    return None
