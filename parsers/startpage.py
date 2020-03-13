"""Parse URL/name pairs in a quasi-INI format.

The format used by the startpage is based on the standard INI format,
but with some added relaxation of normal INI rules to allow URLs to be
used as keys.

"""

import typing
from urllib.parse import quote, urlparse
import configparser
import re


class Parser():
    """A small wrapper for Python's standard ConfigParser class."""

    anonymizer: str = ""
    local_domains: typing.Tuple[str, ...] = ()

    def __init__(
            self,
            anonymizer: str = "",
            local_domains: typing.Tuple[str, ...] = ()
    ) -> None:
        self.anonymizer = anonymizer
        self.local_domains = local_domains

    def anonymize(self, option: str) -> str:
        """Prepend a URL with the anonymizer URL.

        Return the URL as-is if the URL matches a value in the local
        domain list.

        """

        parsed_url = urlparse(option)

        # Skip non-http URLs.
        if parsed_url.scheme not in ('http', 'https'):
            return self.postprocess(option)

        # Skip URLs in local domains.
        if ([d for d in self.local_domains if d in option]):
            return self.postprocess(option)

        return self.anonymizer + quote(self.postprocess(option))

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
        """ Remove the placeholders added during preprocessing."""

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
