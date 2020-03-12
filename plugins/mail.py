"""Send email."""

import smtplib
import typing
from email.mime.text import MIMEText
import cherrypy
import jinja2


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for sending email."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the mail prefix.
        """

        self.bus.subscribe("mail:send", self.send_message)

    @staticmethod
    def send_message(message_data: typing.Dict[str, str],
                     template_data: typing.Dict[str, str]) -> None:
        """Render an email template and send via SMTP"""

        loader = jinja2.FileSystemLoader(message_data["template_dir"])

        env = jinja2.Environment(
            loader=loader,
            autoescape=True
        )

        template = env.get_template(message_data["template"])

        rendered_template = template.render(template_data)

        message = MIMEText(rendered_template)
        message["To"] = message_data["recipient"]
        message["Subject"] = message_data["subject"]
        message["From"] = message_data["sender"]

        mailserver = smtplib.SMTP(
            message_data["smtp_host"],
            int(message_data["smtp_port"])
        )

        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login(
            message_data["smtp_username"],
            message_data["smtp_password"]
        )

        mailserver.sendmail(
            message_data["smtp_sender"],
            message_data["smtp_recipient"],
            message.as_string()
        )
