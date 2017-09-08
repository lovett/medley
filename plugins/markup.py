import cherrypy

class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("markup:reduce_title", self.reduceTitle)

    def stop(self):
        pass

    def reduceTitle(self, title):
        """Remove site identifiers and noise from the title of an HTML document"""
        title = title or ""
        reduced_title = title
        for char in "»|·—:-":
            separator = " {} ".format(char)
            if separator in title:
                segments = title.split(separator)
                reduced_title = max(segments, key=len)
                break

        if reduced_title == title:
            return title
        else:
            return self.reduceTitle(reduced_title)
