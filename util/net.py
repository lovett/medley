import subprocess
import socket
import re
import shutil
import requests
import jinja2
import smtplib
import cherrypy
from html.parser import HTMLParser
from email.mime.text import MIMEText

class NetException (Exception):
    pass

class HtmlTitleParser(HTMLParser):
    in_title_tag = False
    result = None

    def parse(self, markup):
        self.feed(markup)
        return self.result

    def handle_starttag(self, tag, attrs):
        if not self.result and tag == "title":
            self.in_title_tag = True

    def handle_endtag(self, tag):
        if not self.result and tag == "title":
            self.in_title_tag = False

    def handle_data(self, data):
        if not self.result and self.in_title_tag:
            self.result = data.strip()

class HtmlTextParser(HTMLParser):
    tag = None
    result = []
    blacklist = ["script", "style"]

    def parse(self, markup):
        self.result = []
        self.feed(markup)
        return " ".join(self.result)

    def handle_starttag(self, tag, attrs):
        self.tag = tag

    def handle_data(self, data):
        if self.tag not in self.blacklist:
            self.result.append(data.strip())

def sendMessage(message_data, template_data):
    """Render an email template and send via SMTP"""

    loader = jinja2.FileSystemLoader(message_data["template_dir"])
    env = jinja2.Environment(loader=loader)
    template = env.get_template(message_data["template"])

    rendered_template = template.render(template_data)

    message = MIMEText(rendered_template)
    message["To"] = ", ".join(message_data["smtp"]["recipients"])
    message["Subject"] = message_data["subject"]
    message["From"] = message_data["smtp"]["sender"]

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

def sendNotification(message, config):

    try:
        r = requests.post(config[0], auth=config[1:2], data=message)
        r.raise_for_status()
        return True
    except:
        return False

def getHtmlTitle(html):
    """Extract the contents of the title tag from an HTML string"""
    parser = HtmlTitleParser()
    return parser.parse(html)

def getUrl(url, json=False):
    """Make a GET request for the specified URL and return its HTML as a string"""

    cherrypy.log("APP", "Requesting {}".format(url))

    try:
        r = requests.get(
            url,
            timeout=5,
            allow_redirects=True,
            headers = {
                "User-Agent": "python"
            }
        )
        r.raise_for_status()
        if json:
            return r.json()
        else:
            return r.text

    except requests.exceptions.HTTPError as e:
        raise NetException(e)


def saveUrl(url, destination):
    """Download a URL, saving the response body to the filesystem"""

    cherrypy.log("APP", "Requesting {}".format(url))

    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        raise NetException("URL download failed")

    if r.status_code == 200:
        with open(destination, "wb") as f:
            shutil.copyfileobj(r.raw, f)

def htmlToText(html):
    """Reduce an HTML document to the text nodes of the body tag"""
    parser = HtmlTextParser()
    return parser.parse(html)
