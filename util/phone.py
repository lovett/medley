import re

def sanitize(number=""):
    """Strip non-numeric characters from a numeric string"""
    number = re.sub(r"\D", "", number)
    number = re.sub(r"^1(\d{10})", r"\1", number)
    return number

def format(number=""):
    """Format a 10 or 7-digit numeric string as an American phone number.
    Strings of other lengths are returned unmodified."""

    if len(number) == 10:
        return re.sub(r"(\d{3})(\d{3})(\d{4})", r"(\1) \2-\3", number)
    if len(number) == 7:
        return re.sub(r"(\d\d\d)(\d\d\d\d)", r"\1-\2", number)
    else:
        return number
