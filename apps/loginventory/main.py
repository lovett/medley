import sys
import os.path
import fnmatch
import tools.negotiable

sys.path.append("../../")

import cherrypy

class Controller:
    """List all the log files in the log directory"""

    exposed = True

    user_facing = False

    @cherrypy.tools.encode()
    def GET(self):
        root = cherrypy.config.get("log_dir")

        files = [os.path.join(dirpath, f)
                 for dirpath, dirnames, files in os.walk(root)
                 for f in fnmatch.filter(files, "*.log")]

        files = [os.path.basename(f) for f in files]

        cherrypy.response.headers["Content-Type"] = "text/plain"
        return "\n".join(files)
