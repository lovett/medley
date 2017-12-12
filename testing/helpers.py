import cherrypy
import plugins.jinja
import random
import os.path
import tempfile
import apps.shared.main

def getFixture(path):
    with open("test/fixtures/" + path) as handle:
        return handle.read()

def start_server(app):
    """Create a cherrypy server for testing with an app mounted at root
    using method dispatch"""

    server_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cherrypy.config.update({
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

    cherrypy.tree.mount(app(), "/", app_config)

    # Always load the shared app
    cherrypy.tree.mount(
        apps.shared.main.Controller,
        apps.shared.main.Controller.url,
        {}
    )

    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    cherrypy.engine.start()

def stop_server():
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
        return false
