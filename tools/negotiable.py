import cherrypy

class Tool(cherrypy.Tool):
    def __init__(self):
        cherrypy.Tool.__init__(self, 'on_start_resource',
                               self._negotiate,
                               priority=10)

    def _negotiate(self, media=["text/html", "application/json", "text/plain"], charset="utf-8"):
        """Pick a representation for the requested resource

        This is a CherryPy custom tool. It combines cherrypy.tools.accept
        and cherrypy.tools.json_out, so that json is emitted only if the
        client accepts it.

        The selected media type is added to the request object as
        cherrypy.request.negotiated."""

        if isinstance(media, str):
            media = [media]

        req = cherrypy.request

        negotiated = cherrypy.tools.accept.callable(media)

        req.as_json = False
        req.as_text = False
        req.as_html = True

        if negotiated == "application/json":
            req.as_json = True
            cherrypy.tools.json_out.callable()
        elif negotiated == "text/plain":
            req.as_text = True
            cherrypy.response.headers["Content-Type"] = "text/plain"
            cherrypy.tools.encode.callable()
        else:
            req.as_html = True
            cherrypy.response.headers["Content-Type"] = "text/html;charset={}".format(charset)

cherrypy.tools.negotiable = Tool()
