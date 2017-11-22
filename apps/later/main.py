import cherrypy
import re

class Controller:
    """Display a form for bookmarking a URL"""

    url = "/later"

    name = "Later"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, url=None, title=None, tags=None, comments=None):
        error = None
        bookmark = None

        if title:
            title = cherrypy.engine.publish("markup:plaintext", title).pop()
            answer = cherrypy.engine.publish("markup:reduce_title", title)
            title = answer.pop() if answer else title

        if tags:
            tags = cherrypy.engine.publish("markup:plaintext", tags).pop()

        if comments:
            comments = cherrypy.engine.publish("markup:plaintext", comments).pop()
            comments = re.sub("\s+", " ", comments).strip()
            comments = re.sub(",(\w)", ", \\1", comments)

        if comments and not comments.endswith("."):
            comments += "."

        if url:
            answer = cherrypy.engine.publish("archive:find", url=url)
            bookmark = answer.pop() if answer else None

        if bookmark:
            error = "This URL has already been bookmarked"
            title = bookmark["title"]
            tags = bookmark["tags"]
            comments = bookmark["comments"]

        base = cherrypy.request.headers.get("Host")

        if "X-HTTPS" in cherrypy.request.headers:
            base = "https://" + base
        else:
            base = "http://" + base

        return {
            "html": ("later.html", {
                "base": base,
                "error": error,
                "title": title,
                "url": url,
                "tags": tags,
                "comments": comments,
                "app_name": self.name
            })
        }
