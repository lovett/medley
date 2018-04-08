"""Parse text in INI format."""

import configparser


class Parser():
    """A small wrapper for Python's standard ConfigParser class."""

    @staticmethod
    def parse(text):
        """Pass some text to the parser."""

        config = configparser.ConfigParser(
            delimiters=('=',),
            strict=False
        )

        config.optionxform = lambda option: option.upper()

        config.read_string(text)
        return config
