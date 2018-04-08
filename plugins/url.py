import cherrypy
from cherrypy.process import plugins
from urllib.parse import urlencode


class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("url:for_controller", self.url_for_controller)

    def stop(self):
        pass

    def url_for_controller(self, cls, path=None, query={}):
        host = cherrypy.request.headers.get("Host", "")

        if cherrypy.request.headers.get("X-Https", "") == "On":
            proto = "https"
        else:
            proto = "http"

        url = next(
            ("{}://{}{}".format(proto, host, key)
             for key in cherrypy.tree.apps.keys()
             if isinstance(cherrypy.tree.apps[key].root, type(cls))),
            None
        )

        if path:
            url = "{}/{}".format(url, path)

        if query:
            url = "{}?{}".format(url, urlencode(query))

        return url
