import cherrypy
import plugins.jinja

def getFixture(path):
    with open("test/fixtures/" + path) as handle:
        return handle.read()

def start_server(app):
    cherrypy.config.update({
        "app_roots": [],
    })


    app_config = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.encode.on": False
        }
    }

    cherrypy.tree.mount(app(), "/", app_config)

    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    cherrypy.engine.start()

def stop_server():
    cherrypy.engine.exit()
