"""Current and upcoming forecasts"""

import typing
from collections import defaultdict
import cherrypy

Forecast = typing.Dict[str, typing.Any]


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args: str, **_kwargs: str) -> bytes:
        """Display selected parts of the most recent OpenWeather API query"""

        config = cherrypy.engine.publish(
            "registry:search:dict",
            "weather:*",
            key_slice=1
        ).pop()

        if "openweather_api_key" not in config:
            raise cherrypy.HTTPError(500, "No api key")

        locations = tuple(
            tuple(value.split(",", 2))
            for key, value in config.items()
            if key.startswith("latlong")
        )

        latitude = ""
        longitude = ""
        location_name = ""

        if "latlong:default" in config:
            defaults = config["latlong:default"].split(",", 2)
            latitude = defaults[0]
            longitude = defaults[1]
            location_name = defaults[2]

        if len(args) == 1:
            params = args[0].split(",", 1)
            latitude = params[0]
            longitude = params[1]
            location_name = next((
                location[2]
                for location in locations
                if location[0] == latitude
                and location[1] == longitude
            ), "")

        cache_key = f"openweather_{latitude},{longitude}"

        cached_api_response = cherrypy.engine.publish(
            "cache:get",
            cache_key
        ).pop()

        if cached_api_response:
            forecast = self.shape_forecast(cached_api_response)

        if not cached_api_response:
            endpoint = "https://api.openweathermap.org/data/2.5/onecall"
            endpoint += f"?lat={latitude}&lon={longitude}"
            endpoint += "&exclude=minutely"
            endpoint += "&units=imperial"
            endpoint += f"&appid={config['openweather_api_key']}"

            api_response = cherrypy.engine.publish(
                "urlfetch:get",
                endpoint,
                as_json=True,
            ).pop()

            if api_response:
                # Cache for 1 hour.
                cherrypy.engine.publish(
                    "cache:set",
                    cache_key,
                    api_response,
                    3600
                )

                forecast = self.shape_forecast(api_response)

        edit_url = cherrypy.engine.publish(
            "url:internal",
            "/registry",
            {"q": "weather:latlong"}
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/weather/weather.jinja.html",
                forecast=forecast,
                other_locations=locations,
                location_name=location_name,
                edit_url=edit_url,
                subview_title=location_name,
            ).pop()
        )

    @staticmethod
    def shape_forecast(forecast: Forecast) -> Forecast:
        """Reduce an API response object to wanted values"""

        result: Forecast = defaultdict()

        daily = forecast.get("daily", [])
        hourly = forecast.get("hourly", [])
        currently = forecast.get("current", {})

        now = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        result["currently"] = currently
        result["hourly"] = hourly[0:(24 - now.hour + 1)]
        result["today"] = daily[0]
        result["upcoming"] = daily[1:]

        print(currently["weather"])

        result["currently"]["weather_groups"] = [
            item.get("main").lower()
            for item
            in currently["weather"]
        ]

        result["currently"]["weather_description"] = ". ".join([
            item.get("description").capitalize()
            for item
            in currently["weather"]
        ])

        return result
