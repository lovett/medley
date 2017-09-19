import cherrypy

class Controller:
    """Add entries to an Asterisk callerid database"""

    url = "/callerid"

    name = "Caller ID"

    exposed = True

    user_facing = False

    def PUT(self, cid_number, cid_value):
        """Set the caller id for a number"""

        number = cid_number.strip()
        value = cid_value.strip()

        cherrypy.engine.publish("asterisk:set_caller_id", number, value)

        cherrypy.response.status = 204
        return
