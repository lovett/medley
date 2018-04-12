"""Parse text in INI format."""

import configparser


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

        if any([d for d in self.local_domains if url in d]):
            return url
        return self.anonymizer + url

    def parse(self, text):
        """Pass some text to the parser."""

        config = configparser.ConfigParser(
            delimiters=('=',),
            interpolation=False,
            strict=False
        )

        if self.anonymizer:
            config.optionxform = self.anonymize

        config.read_string(text)
        return config
