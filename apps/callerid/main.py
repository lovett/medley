"""Add entries to an Asterisk callerid database."""

import cherrypy

class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    @cherrypy.tools.json_out()
    def PUT(self, cid_number, cid_value):
        """Set the caller id for a number"""

        number = cid_number.strip()
        value = cid_value.strip()

        cherrypy.engine.publish("asterisk:set_caller_id", number, value)

        return {
            "cid_number": number,
            "cid_value": value
        }
