import cherrypy
import util.db

class Tool(cherrypy.Tool):
    """Save the headers and body of an incoming request for later review"""

    def __init__(self):
        cherrypy.Tool.__init__(self, 'on_end_request',
                               self._capture)
    def _capture(self):
        util.db.saveCapture(cherrypy.request, cherrypy.response)

cherrypy.tools.capture = Tool()
