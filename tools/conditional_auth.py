import cherrypy


class Tool(cherrypy.Tool):
    """Prompt for basic authentication unless the request originates from
    a whitelisted IP

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
        if not p:
            return False

        return p == password

    def _auth(self, whitelist=None):
        """Decide whether to prompt for HTTP basic authentication."""

        # The maintenance app should only be accessed from localhost,
        # unless the global application config says otherwise.
        only_local = False
        if cherrypy.request.script_name == "/maintenance":
            only_local = cherrypy.config.get("local_maintenance", True)

        ips = ["127.0.0"]
        if not only_local:
            ips.extend(whitelist.split())

        address = cherrypy.request.headers.get("X-Real-IP")

        if not address:
            address = cherrypy.request.headers.get("Remote-Addr")

        if not any(address.startswith(ip) for ip in ips):
            cherrypy.tools.auth_basic.callable(
                realm="medley",
                checkpassword=self._checkpassword
            )


cherrypy.tools.conditional_auth = Tool()
