import time
import cherrypy

class Tool(cherrypy.Tool):
    """Populate the X-Response-Time header, which measures how many
    seconds it took to process the request. Based on sample code in
    the CherryPy documentation."""

    def __init__(self):
        cherrypy.Tool.__init__(self, "before_handler",
                               self.start_timer,
                               priority=95)

    def _setup(self):
        cherrypy.Tool._setup(self)
        cherrypy.request.hooks.attach("before_finalize",
                                      self.end_timer,
                                      priority=5)

    def start_timer(self):
        cherrypy.request._time = time.time()

    def end_timer(self):
        try:
            duration = time.time() - cherrypy.request._time
            cherrypy.response.headers["X-Response-Time"] = round(duration, 4)
        except AttributeError:
            # The timer isn't always active. It won't be started when
            # serving static assets, for example.
            pass

cherrypy.tools.response_time = Tool()
