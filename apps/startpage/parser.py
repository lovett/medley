"""Parse URL/name pairs in INI format.

"""

import configparser
import re


class Parser():
    """A small wrapper for Python's standard ConfigParser class."""

    anonymizer = None
    local_domains = ()

    def __init__(self, anonymizer=None, local_domains=()):
        self.anonymizer = anonymizer
        self.local_domains = local_domains

    def anonymize(self, url):
        """Prepend a URL with the anonymizer URL.

        Return the URL as-is if the URL matches a value in the local
        domain list.

        """

        if any([d for d in self.local_domains if d in url]):
            return self.postprocess(url)

        return self.anonymizer + self.postprocess(url)

    @staticmethod
    def preprocess(text):
        """Temporarily convert delimiters in option names.

        URLs are used as option names. URLs can contain "=", but this
        is also serves as the delimiter between an option's name and
        its value. Temporarily converting "=" to a placeholder allows
        parsing to work as intended.

        Placeholders are only necessary when there is more than one
        equals sign on a line, and are not needed for the actual
        delimiter.

        """

        processed_text = [
            re.sub("=", "@@EQUAL@@", line, line.count("=") - 1)
            if line.count("=") > 1
            else line
            for line in text.split("\n")
        ]

        print(processed_text)
        return "\n".join(processed_text)

    @staticmethod
    def postprocess(text):
        """ Remove the placeholders added during preprocessing."""

        return re.sub("@@EQUAL@@", "=", text)

    def parse(self, text):
        """Pass some text to the parser."""

        config = configparser.ConfigParser(
            delimiters=('=',),
            interpolation=None,
            strict=False
        )

        if self.anonymizer:
            config.optionxform = self.anonymize

        processed_text = self.preprocess(text)

        config.read_string(processed_text)
        return config
