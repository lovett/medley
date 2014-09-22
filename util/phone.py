import re
import urllib
import urllib.request
import urllib.parse
import json
import collections

def sanitize(number=""):
    """Strip non-numeric characters from a numeric string"""
    number = re.sub(r"\D", "", number)
    number = re.sub(r"^1(\d{10})", r"\1", number)
    return number

def format(number=""):
    """Format a 10 or 7-digit numeric string as an American telephone number.
    Strings of other lengths are returned unmodified."""

    if len(number) == 10:
        return re.sub(r"(\d{3})(\d{3})(\d{4})", r"(\1) \2-\3", number)
    if len(number) == 7:
        return re.sub(r"(\d\d\d)(\d\d\d\d)", r"\1-\2", number)
    else:
        return number

def findAreaCode(area_code):
    """Query dbpedia for the geographic location of an American telephone area code"""

    # area code should be a 3 digit string
    assert len(area_code) == 3, "Wrong length area code"
    assert re.match("\d+$", area_code) is not None, "Non-numeric area code"

    query = """
    PREFIX dbp: <http://dbpedia.org/property/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?state_abbrev, ?comment WHERE {{
        ?s dbp:this ?o .
        ?s dbp:state ?state_abbrev .
        ?s rdfs:comment ?comment
        FILTER (regex(?o, "{0}", "i"))
        FILTER (langMatches(lang(?state_abbrev), "en"))
    }} LIMIT 1
    """.format(area_code)

    params = urllib.parse.urlencode({
        "query": query,
        "format": "json",
        "timeout": "1000"
    })

    query = "http://dbpedia.org/sparql?{0}".format(params)

    Location = collections.namedtuple('Location', ['state_abbreviation', 'state_name', 'comment'])

    try:
        with urllib.request.urlopen(query, timeout=7) as request:
            result = json.loads(request.read().decode("utf-8"))

        first_result = result["results"]["bindings"][0]
        abbrev = first_result["state_abbrev"]["value"]
        comment = first_result["comment"]["value"]

        return Location(state_abbreviation=abbrev,
                        state_name=stateName(abbrev),
                        comment=abbreviateComment(comment))

    except (IndexError, urllib.error.HTTPError):
        return Location(state_abbreviation=None,
                        state_name="Unknown",
                        comment="The location of this number could not be found.")

def stateName(abbreviation=None):
    """Query dbpedia for the name of US state by its abbreviation"""

    query = """
    PREFIX dbp: <http://dbpedia.org/property/>
    SELECT ?name WHERE {{
        ?s dbp:isocode "US-{0}"@en .
        ?s dbp:name ?name .
    }} LIMIT 1
    """.format(abbreviation)

    query = "http://dbpedia.org/sparql?"
    query += urllib.parse.urlencode({
        "query": query,
        "format": "json",
        "timeout": "1000"
    })

    try:
        with urllib.request.urlopen(query, timeout=7) as request:
            result = json.loads(request.read().decode("utf-8"))
        return result["results"]["bindings"][0]["name"]["value"]
    except (IndexError, urllib.error.HTTPError):
        return "Unknown"

def abbreviateComment(comment):
    """Extract the first two meaningful sentences from a dbpedia comment field"""

    abbreviated_comment = [sentence for sentence in comment.split(". ")
                           if re.search(" in (red|blue) (is|are)", sentence, re.IGNORECASE) is None
                           and not re.match("The map to the right", sentence, re.IGNORECASE)
                           and not re.match("Error: ", sentence, re.IGNORECASE)][:2]

    abbreviated_comment = ". ".join(abbreviated_comment)

    if len(abbreviated_comment) > 0 and not abbreviated_comment.endswith("."):
        abbreviated_comment += "."

    return abbreviated_comment
