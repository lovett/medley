import cherrypy

class Tool(cherrypy.Tool):
    """Save the headers and body of an incoming request for later review"""

    def __init__(self):
        cherrypy.Tool.__init__(self, 'on_end_request',
                               self._capture)
    def _capture(self):
        cherrypy.engine.publish("capture:add", cherrypy.response)

cherrypy.tools.capture = Tool()
