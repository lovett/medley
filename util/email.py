import jinja2
from email.mime.text import MIMEText
import smtplib

def sendMessage(message_data, template_data, debug=False):
    """Compose an email message from a Jinja template and send via
    localhost SMTP"""

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(message_data["template_dir"]))
    template = env.get_template(message_data["template"])

    rendered_template = template.render(template_data)

    message = MIMEText(rendered_template)
    message["To"] = ", ".join(message_data["smtp"]["recipients"])
    message["Subject"] = message_data["subject"]
    message["From"] = message_data["smtp"]["sender"]

    if debug:
        return message.as_string()

    mailserver = smtplib.SMTP(message_data["smtp"]["host"],
                              message_data["smtp"]["port"])
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login(message_data["smtp"]["username"],
                   message_data["smtp"]["password"])

    mailserver.sendmail(message_data["smtp"]["sender"],
                        ", ".join(message_data["smtp"]["recipients"]),
                        message.as_string())
