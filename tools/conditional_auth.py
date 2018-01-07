import cherrypy

class Tool(cherrypy.Tool):
    """Prompt for basic authentication unless the request originates from a
    whitelisted IP

    Whitelisted IPs should be specified in the global application
    config under the key tools.conditional_auth.whitelist
    """

    def __init__(self):
        cherrypy.Tool.__init__(
            self,
            "on_start_resource",
            self._auth,
            priority=1
        )

    def _checkpassword(self, realm, user, password):
        users = cherrypy.config.get("users")
        p = users.get(user)
        return p and p == password or False

    def _auth(self, whitelist=None):

        ips = whitelist.split()
        ips.append("127.0.0")

        address = None
        for header in ("X-Real-Ip", "Remote-Addr"):
            try:
                address = cherrypy.request.headers[header]
                break
            except KeyError:
                pass

        if any(address.startswith(ip) for ip in ips):
            return

        cherrypy.tools.auth_basic.callable(realm="medley", checkpassword=self._checkpassword)

cherrypy.tools.conditional_auth = Tool()
