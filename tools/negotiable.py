import cherrypy

class Tool(cherrypy.Tool):
    def __init__(self):
        cherrypy.Tool.__init__(self, 'on_start_resource',
                               self._negotiate,
                               priority=10)

    def _negotiate(self, media=["text/html", "application/json", "text/plain"], charset="utf=8"):
        """Pick a representation for the requested resource

        This is a CherryPy custom tool. It combines cherrypy.tools.accept
        and cherrypy.tools.json_out, so that json is emitted only if the
        client accepts it.

        The selected media type is added to the request object as
        cherrypy.request.negotiated."""

        if isinstance(media, str):
            media = [media]

        req = cherrypy.request
        tools = cherrypy.tools
        req.negotiated = tools.accept.callable(media)

        if req.negotiated == "application/json":
            tools.json_out.callable()
        elif req.negotiated == "text/plain":
            cherrypy.response.headers["Content-Type"] = "text/plain; charset={}".format(charset)
            tools.encode.callable()
