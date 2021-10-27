"""Parse URL/name pairs in a quasi-INI format.

The format used by the startpage is based on the standard INI format,
but with some added relaxation of normal INI rules to allow URLs to be
used as keys.

"""

import typing
import configparser
import re
from resources.url import Url


class Parser():
    """A small wrapper for Python's standard ConfigParser class."""

    anonymizer: str = ""
    local_domains: typing.List[str]

    def __init__(
            self,
            anonymizer: str,
            local_domains: typing.List[str],
    ) -> None:
        self.anonymizer = anonymizer
        self.local_domains = local_domains

    def anonymize(self, option: str) -> str:
        """Prepend a URL with the anonymizer URL.

        Return the URL as-is if the URL matches a value in the local
        domain list.

        """

        url = Url(self.postprocess(option))

        # Skip non-http URLs.
        if not url.is_http():
            return url.address

        # Skip URLs in local domains.
        if ([d for d in self.local_domains if d in option]):
            return url.address

        return self.anonymizer + url.escaped_address

    @staticmethod
    def preprocess(text: str) -> str:
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

        return "\n".join(processed_text)

    @staticmethod
    def postprocess(text: str) -> str:
        """Remove the placeholders added during preprocessing."""

        return re.sub("@@EQUAL@@", "=", text)

    def parse(self, text: str) -> configparser.ConfigParser:
        """Pass some text to the parser."""

        config = configparser.ConfigParser(
            delimiters=('=',),
            interpolation=None,
            strict=False
        )

        if self.anonymizer:
            setattr(config, "optionxform", self.anonymize)

        processed_text = self.preprocess(text)

        config.read_string(processed_text)
        return config
