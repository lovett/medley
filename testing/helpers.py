"""Utility functions to make unit tests easier."""

import os.path
import tempfile
import cherrypy
import plugins.jinja
import apps.shared.main
from tools import negotiable


def get_fixture(path):
    """Return the contents of a file in the fixtures directory."""
    with open("testing/fixtures/" + path) as handle:
        return handle.read()


def start_server(app):
    """Create a cherrypy server for testing with an app mounted at root
    using method dispatch"""

    server_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_root = os.path.join(server_root, "apps")

    cherrypy.config.update({
        "app_root": app_root,
        "server_root": server_root,
        "database_dir": tempfile.gettempdir(),
        "tools.encode.on": False
    })

    app_config = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.encode.on": False
        }
    }

    # Treat the app as exposed by default. Apps that are not exposed
    # return 404s, which interferes with testing.
    app.exposed = True

    cherrypy.tree.mount(app(), "/", app_config)

    # Always load the shared app
    cherrypy.tree.mount(
        apps.shared.main.Controller,
        "/shared",
        {}
    )

    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    cherrypy.tools.negotiable = negotiable.Tool()
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
