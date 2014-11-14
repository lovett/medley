import cherrypy

class Tool(cherrypy.Tool):
    """Prompt for basic authentication unless the request originates from a
    whitelisted IP"""

    def __init__(self):
        cherrypy.Tool.__init__(self, 'on_start_resource',
                               self._noauth, priority=1)

    def _checkpassword(self, realm, user, password):
        users = cherrypy.config.get("users")
        p = users.get(user)
        return p and p == password or False

    def _noauth(self, whitelist=()):
        if cherrypy.request.remote.ip not in whitelist:
            cherrypy.tools.auth_basic.callable(realm="medley", checkpassword=self._checkpassword)
