"""Look up geographic information by various identifiers."""

import re
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Tuple
from typing import cast
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for retrieving geographic information by
    abbreviation or other identifier.

    """

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the geography prefix.
        """

        self.bus.subscribe(
            "geography:unabbreviate_state",
            self.unabbreviate_us_state
        )

        self.bus.subscribe(
            "geography:state_by_area_code",
            self.state_by_area_code
        )

        self.bus.subscribe(
            "geography:country_by_abbreviation",
            self.country_by_abbreviation
        )

    def state_by_area_code(
            self,
            area_code: str
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Query dbpedia for the geographic location of a North American
        telephone area code. Returns a dictionary with keys for state
        abbreviation, full name, and comment.

        """

        sparql = f"""
        PREFIX dbp: <http://dbpedia.org/property/>
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?state_abbrev, ?abstract WHERE {{
        ?s dbp:this ?o .
        ?s dbo:abstract ?abstract .
        ?s dbp:state ?_state_abbrev
        FILTER (regex(str(?o), "{area_code}", "i"))
        FILTER (langMatches(lang(?abstract), "en"))
        BIND( str(?_state_abbrev) as ?state_abbrev )
        }} LIMIT 1
        """

        response, _ = cherrypy.engine.publish(
            "urlfetch:get:json",
            "http://dbpedia.org/sparql",
            headers={
                "Accept": "application/sparql-results+json"
            },
            params={
                "query": sparql,
                "format": "json",
                "timeout": "5000"
            },
            cache_lifespan=86400
        ).pop()

        try:
            abstract = self.dbpedia_abstract(
                response["results"]["bindings"][0]["abstract"]["value"]
            )

            return (
                sparql,
                response["results"]["bindings"][0]["state_abbrev"]["value"],
                abstract
            )
        except (IndexError, KeyError, TypeError):
            return (sparql, None, None)

    @staticmethod
    def unabbreviate_us_state(
            abbreviation: str
    ) -> Tuple[str, Optional[str]]:
        """Query dbpedia for the full name of a U.S. state by its 2-letter
        abbreviation.

        """

        sparql = f"""
        PREFIX dbp:  <http://dbpedia.org/property/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?state_name WHERE {{
            ?x rdfs:label ?state_name .
            ?x dbp:isocode "US-{abbreviation}"^^rdf:langString .
            FILTER (langMatches(lang(?state_name), "en"))
        }}
        LIMIT 1
        """

        response, _ = cherrypy.engine.publish(
            "urlfetch:get:json",
            "http://dbpedia.org/sparql",
            headers={
                "Accept": "application/sparql-results+json"
            },
            params={
                "query": sparql,
                "format": "json",
                "timeout": "5000"
            },
            cache_lifespan=86400
        ).pop()

        try:
            return (
                sparql,
                response["results"]["bindings"][0]["state_name"]["value"]
            )
        except (IndexError, KeyError, TypeError):
            return (sparql, None)

    @staticmethod
    def country_by_abbreviation(
            abbreviations: Iterable[str] = ()
    ) -> Dict[str, str]:
        """Query the registry for the name of a country from its 2-letter
        abbreviation.

        """

        keys = (
            f"country_code:alpha2:{abbreviation}"
            for abbreviation in abbreviations
        )

        rows = cherrypy.engine.publish(
            "registry:search:dict",
            keys=tuple(keys),
            key_slice=2
        ).pop()

        return cast(
            Dict[str, str],
            rows
        )

    @staticmethod
    def dbpedia_abstract(text: str) -> str:
        """Extract the first two meaningful sentences from a dbpedia
        abstract."""

        # Separate collided sentences:
        #
        # Before:
        # This is the first.This is the second.
        #
        # After:
        # This is the first. This is the second.
        abbreviated_text = re.sub(r'([^A-Z])\.([^ ])', '\\1. \\2', text)

        # Remove sentences referring to maps
        sentences = [
            sentence for sentence in abbreviated_text.split(". ")
            if not re.search(
                    " in (red|blue) (is|are)", sentence,
                    re.IGNORECASE
            )
            and not re.match(
                "The map to the right", sentence,
                re.IGNORECASE
            )
            and not re.match(
                "Error: ", sentence,
                re.IGNORECASE
            )
        ][:2]

        abbreviated_text = ". ".join(sentences)

        if abbreviated_text and not abbreviated_text.endswith("."):
            abbreviated_text += "."

        return abbreviated_text
