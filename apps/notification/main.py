"""Notifier webhook for text-to-speech."""

import re
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = False
    exposed = True

    # Taken from https://stackoverflow.com/questions/33404752
    emoji_regex = re.compile("["
                             u"\U0001F600-\U0001F64F"
                             u"\U0001F300-\U0001F5FF"
                             u"\U0001F680-\U0001F6FF"
                             u"\U0001F1E0-\U0001F1FF"
                             u"\U00002500-\U00002BEF"
                             u"\U00002702-\U000027B0"
                             u"\U00002702-\U000027B0"
                             u"\U000024C2-\U0001F251"
                             u"\U0001f926-\U0001f937"
                             u"\U00010000-\U0010ffff"
                             u"\u2640-\u2642"
                             u"\u2600-\u2B55"
                             u"\u200d"
                             u"\u23cf"
                             u"\u23e9"
                             u"\u231a"
                             u"\ufe0f"
                             u"\u3030"
                             "]+",
                             flags=re.UNICODE)

    @cherrypy.tools.capture()
    @cherrypy.tools.json_in()
    def POST(self, *_args: str, **_kwargs: str) -> None:
        """Decide whether a notification is speakable."""

        notification = cherrypy.request.json

        # Retractions are ignored because they are not actionable.
        if "retracted" in notification:
            cherrypy.response.status = 202
            return

        skippable_groups = cherrypy.engine.publish(
            "registry:search:valuelist",
            "notification:skip:group"
        ).pop()

        if notification.get("group") in skippable_groups:
            cherrypy.response.status = 202
            return

        title = notification.get("title", "")

        if title:
            title = self.emoji_regex.sub(
                "", title
            ).strip()

        if not title:
            cherrypy.response.status = 400
            return

        muted = cherrypy.engine.publish("speak:muted").pop()

        if muted:
            cherrypy.response.status = 202
            return

        cherrypy.engine.publish("speak", title)
        cherrypy.response.status = 204
