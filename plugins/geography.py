"""Look up geographic information by various identifiers."""

import typing
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

    @staticmethod
    def state_by_area_code(
            area_code: str
    ) -> typing.Tuple[str, typing.Optional[str], typing.Optional[str]]:
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

        response = cherrypy.engine.publish(
            "urlfetch:get",
            "http://dbpedia.org/sparql",
            headers={
                "Accept": "application/sparql-results+json"
            },
            params={
                "query": sparql,
                "format": "json",
                "timeout": "5000"
            },
            as_json=True
        ).pop()

        try:
            abstract = cherrypy.engine.publish(
                "formatting:dbpedia_abstract",
                response["results"]["bindings"][0]["abstract"]["value"]
            ).pop()

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
    ) -> typing.Tuple[str, typing.Optional[str]]:
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

        response = cherrypy.engine.publish(
            "urlfetch:get",
            "http://dbpedia.org/sparql",
            headers={
                "Accept": "application/sparql-results+json"
            },
            params={
                "query": sparql,
                "format": "json",
                "timeout": "5000"
            },
            as_json=True
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
            abbreviations: typing.Iterable[str] = ()
    ) -> typing.Dict[str, str]:
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

        return typing.cast(
            typing.Dict[str, str],
            rows
        )
