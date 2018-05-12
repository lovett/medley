import re
from cherrypy.process import plugins


class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("formatting:dbpedia_abstract", self.dbpediaAbstract)
        self.bus.subscribe("formatting:http_timestamp", self.http_timestamp)

    def stop(self):
        pass

    def dbpediaAbstract(self, text):
        """Extract the first two meaningful sentences from a dbpedia
        abstract.

        """

        # Separate collided sentences:
        #
        # Before:
        # This is the first.This is the second.
        #
        # After:
        # This is the first. This is the second.
        abbreviated_text = re.sub(r'([^A-Z])\.([^ ])', '\\1. \\2', text)

        # Remove sentences referring to maps
        abbreviated_text = [
            sentence for sentence in abbreviated_text.split(". ")
            if re.search(" in (red|blue) (is|are)", sentence, re.IGNORECASE) is None
            and not re.match("The map to the right", sentence, re.IGNORECASE)
            and not re.match("Error: ", sentence, re.IGNORECASE)
        ][:2]

        abbreviated_text = ". ".join(abbreviated_text)

        if len(abbreviated_text) > 0 and not abbreviated_text.endswith("."):
            abbreviated_text += "."

        return abbreviated_text

    def http_timestamp(self, instance):
        """Custom Pendulum formatter for an HTTP-date timestamp, as defined in
        Section 7.1.1.1 of [RFC7231].

        Example output: Thu, 01 Dec 1994 16:00:00 GMT

        """
        return instance.format('ddd, DD MMM YYYY HH:mm:ss zz')
