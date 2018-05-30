"""Look up geographic information by various identifiers."""

import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for retrieving geographic information by
    abbreviation or other identifier.

    """

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
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
    def state_by_area_code(area_code):
        """Query dbpedia for the geographic location of a North American
        telephone area code. Returns a dictionary with keys for state
        abbreviation, full name, and comment.

        """

        sparql = """
        PREFIX dbp: <http://dbpedia.org/property/>
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?state_abbrev, ?abstract WHERE {{
        ?s dbp:this ?o .
        ?s dbo:abstract ?abstract .
        ?s dbp:state ?_state_abbrev
        FILTER (regex(str(?o), "{0}", "i"))
        BIND( str(?_state_abbrev) as ?state_abbrev )
        }} LIMIT 1
        """.format(area_code)

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
        except KeyError:
            return (None, None, None)

    @staticmethod
    def unabbreviate_us_state(abbreviation):
        """Query dbpedia for the full name of a U.S. state by its 2-letter
        abbreviation.

        """

        sparql = """
        PREFIX dbp:  <http://dbpedia.org/property/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?state_name WHERE {{
            ?x rdfs:label ?state_name .
            ?x dbp:isocode "US-{0}"^^rdf:langString .
            FILTER (langMatches(lang(?state_name), "en"))
        }}
        LIMIT 1
        """.format(abbreviation)

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
        except KeyError:
            return (None, None)

    @staticmethod
    def country_by_abbreviation(abbreviations=()):
        """Query the registry for the name of a country from its 2-letter
        abbreviation.

        """

        keys = (
            "country_code:alpha2:{}".format(abbreviation)
            for abbreviation in abbreviations
        )

        return cherrypy.engine.publish(
            "registry:search",
            keys=tuple(keys),
            as_dict=True,
            key_slice=2
        ).pop()
