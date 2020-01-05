"""Utility functions to make unit tests easier."""

import pathlib
import tempfile
import cherrypy
import plugins.jinja
import apps.shared.main
import tools.etag


def get_fixture(path):
    """Return the contents of a file in the fixtures directory."""
    with open("testing/fixtures/" + path) as handle:
        return handle.read()


def start_server(app):
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


def stop_server():
    """Shut down the cherrypy server used by the current test suite."""
    cherrypy.engine.exit()


def response_is_html(res):
    """Test a response object for an HTML content type header"""
    return header_is(res.headers, "Content-Type", "text/html;charset=utf-8")


def response_is_json(res):
    """Test a response object for an JSON content type header"""
    return header_is(res.headers, "Content-Type", "application/json")


def response_is_text(res):
    """Test a response object for a plain text content type header"""
    return header_is(res.headers, "Content-Type", "text/plain;charset=utf-8")


def header_is(headers, name, value):
    """Test a dict of headers for an expected name/value pair"""
    try:
        return headers[name] == value
    except KeyError:
        return False


def html_var(called_mock, key):
    """Retrieve a template variable from the HTML portion of a response."""
    return called_mock.call_args[0][0]["html"][1].get(key)


def text_var(called_mock):
    """Retrieve a template variable from the text portion of a response."""
    return called_mock.call_args[0][0]["text"]


def find_publish_call(called_mock, subscription_topic):
    """Find a topic in the call list of a mock of cherrypy.engine.publish."""
    for call in called_mock.call_args_list:
        if call[0][0] == subscription_topic:
            return call
    return None
