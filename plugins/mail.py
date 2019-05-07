"""Send email."""

import smtplib
from email.mime.text import MIMEText
import jinja2
from cherrypy.process import plugins


class Plugin(plugins.SimplePlugin):
    """A CherryPy plugin for sending email."""

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the mail prefix.
        """

        self.bus.subscribe("mail:send", self.send_message)

    @staticmethod
    def send_message(message_data, template_data):
        """Render an email template and send via SMTP"""

        loader = jinja2.FileSystemLoader(message_data["template_dir"])

        env = jinja2.Environment(
            loader=loader,
            autoescape=True
        )

        template = env.get_template(message_data["template"])

        rendered_template = template.render(template_data)

        message = MIMEText(rendered_template)
        message["To"] = ", ".join(message_data["smtp"]["recipients"])
        message["Subject"] = message_data["subject"]
        message["From"] = message_data["smtp"]["sender"]

        mailserver = smtplib.SMTP(
            message_data["smtp"]["host"],
            message_data["smtp"]["port"]
        )

        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login(
            message_data["smtp"]["username"],
            message_data["smtp"]["password"]
        )

        mailserver.sendmail(
            message_data["smtp"]["sender"],
            ", ".join(message_data["smtp"]["recipients"]),
            message.as_string()
        )
