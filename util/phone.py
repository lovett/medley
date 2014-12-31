import re
import requests
import sqlite3
import socket
import util.sqlite_converters

class PhoneException(Exception):
    pass

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

def findAreaCode(area_code, timeout=4):
    """Query dbpedia for the geographic location of a North American
    telephone area code. Returns a dictionary with keys for state
    abbreviation, full name, and comment.
    """

    # area code should be a 3 digit string
    assert len(area_code) == 3, "Wrong length area code"
    assert re.match("\d+$", area_code) is not None, "Non-numeric area code"

    sparql = """
    PREFIX dbp: <http://dbpedia.org/property/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?state_abbrev, ?comment WHERE {{
        ?s dbp:this ?o .
        ?s dbp:state ?state_abbrev .
        ?s rdfs:comment ?comment
        FILTER (regex(str(?o), "{0}", "i"))
        FILTER (langMatches(lang(?state_abbrev), "en"))
        FILTER (langMatches(lang(?comment), "en"))
    }} LIMIT 1
    """.format(area_code)

    payload = {
        "query": sparql,
        "format": "json",
        "timeout": "1000"
    }

    result = {
        "sparql": [],
        "url": [],
        "state_abbreviation": None,
        "state_name": "Unknown",
        "comment": "The location of this number could not be found."
    }

    try:
        r = requests.get("http://dbpedia.org/sparql", params=payload, timeout=timeout)
        r.raise_for_status()
        response = r.json()
        first_result = response["results"]["bindings"][0]
        result["sparql"].append(sparql)
        result["url"].append(r.url)
        result["state_abbreviation"] = first_result["state_abbrev"]["value"]
        result["comment"] = abbreviateComment(first_result["comment"]["value"])
    except ValueError:
        raise PhoneException("Dbpedia area code query timed out")
    except requests.exceptions.HTTPError:
        raise PhoneException("Dbpedia area code query failed")
    except IndexError:
        return result

    try:
        state_result = stateName(result["state_abbreviation"], timeout)
        result["sparql"].append(state_result["sparql"])
        result["url"].append(state_result["url"])
        result["state_name"] = state_result["name"]
        return result
    except PhoneException:
        return result

def stateName(abbreviation=None, timeout=7):
    """Query dbpedia for the name of a US state from its abbreviation"""

    sparql = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbpo: <http://dbpedia.org/ontology/>
    SELECT ?name, ?actualResource WHERE {{
        ?s rdfs:label "US-{0}"@en .
        {{
            ?s dbpo:wikiPageRedirects ?actualResource .
            ?actualResource rdfs:label ?redirectsTo .
            ?actualResource rdfs:label ?name .
            FILTER (langMatches(lang(?name), "en"))
        }}
    }} LIMIT 1
    """.format(abbreviation)

    payload = {
        "query": sparql,
        "format": "json",
        "timeout": "1000"
    }

    result = {
        "sparql": sparql
    }

    try:
        r = requests.get("http://dbpedia.org/sparql", params=payload, timeout=timeout)
        r.raise_for_status()
        response = r.json()
        result["url"] = r.url
        result["name"] = response["results"]["bindings"][0]["name"]["value"]
        return result
    except ValueError:
        raise PhoneException("Dbpedia state name query timed out")
    except requests.exceptions.HTTPError:
        raise PhoneException("Dbpedia state name query failed")
    except IndexError:
        result["name"] = None
        return result

def abbreviateComment(comment):
    """Extract the first two meaningful sentences from a dbpedia comment field"""

    # Separate collided sentences:
    # This is the first.This is the second. => This is the first. This is the second.
    abbreviated_comment = re.sub(r'([^A-Z])\.([^ ])', '\\1. \\2', comment)

    # Remove sentences referring to maps
    abbreviated_comment = [sentence for sentence in abbreviated_comment.split(". ")
                           if re.search(" in (red|blue) (is|are)", sentence, re.IGNORECASE) is None
                           and not re.match("The map to the right", sentence, re.IGNORECASE)
                           and not re.match("Error: ", sentence, re.IGNORECASE)][:2]

    abbreviated_comment = ". ".join(abbreviated_comment)

    if len(abbreviated_comment) > 0 and not abbreviated_comment.endswith("."):
        abbreviated_comment += "."

    return abbreviated_comment

def callHistory(database, caller, limit=0, offset=0):
    """Get call history from an Asterisk sqlite3 CDR database."""

    sqlite3.register_converter("date", util.sqlite_converters.convert_date)
    sqlite3.register_converter("duration", util.sqlite_converters.convert_duration)
    sqlite3.register_converter("clid", util.sqlite_converters.convert_callerid)

    conn = sqlite3.connect(database, detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT count(*) as count FROM cdr WHERE src=?", (caller,))
    count = cur.fetchone()[0]

    if count == 0:
        conn.close()
        return ([], 0)

    params = []
    query = """SELECT calldate as "date [date]", duration as "duration [duration]", clid as "clid [clid]", * FROM cdr WHERE src=? ORDER BY calldate DESC"""
    params.append(caller)

    if limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    if limit > 0 and offset > 0:
        query += " OFFSET ?"
        params.append(offset)

    cur.execute(query, params)
    result = (cur.fetchall(), count)

    conn.close()
    return result
