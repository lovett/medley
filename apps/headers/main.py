import cherrypy
import tools.negotiable
import tools.jinja

class Controller:
    """Display request headers"""

    name = "Headers"

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="headers.html")
    @cherrypy.tools.negotiable()
    def GET(self):
        headers = [(key.decode('utf-8'), value.decode('utf-8'))
                   for key, value in cherrypy.request.headers.output()]

        headers.sort(key=lambda tup: tup[0])

        if cherrypy.request.as_json:
            return headers
        elif cherrypy.request.as_text:
            headers = ["{}: {}".format(key, value) for key, value in headers]
            return "\n".join(headers)
        else:
            return {
                "headers": headers,
                "app_name": self.name
            }
