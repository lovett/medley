"""Current and upcoming forecasts"""

import copy
import math
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
        """Display selected parts of the most recent Darksky API query"""

        config = cherrypy.engine.publish(
            "registry:search:dict",
            "weather:*",
            key_slice=1
        ).pop()

        if "darksky_key" not in config:
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

        cache_key = f"darksky_{latitude},{longitude}"

        cached_api_response = cherrypy.engine.publish(
            "cache:get",
            cache_key
        ).pop()

        if cached_api_response:
            forecast = self.shape_forecast(cached_api_response)

        if not cached_api_response:
            endpoint = "https://api.darksky.net/forecast/"
            endpoint += config['darksky_key']
            endpoint += f"/{latitude},{longitude}"
            endpoint += "?lang=en&units=us&exclude=minutely"

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
                subview_title=location_name
            ).pop()
        )

    @staticmethod
    def shape_forecast(forecast: Forecast) -> Forecast:
        """Reduce an API response object to wanted values"""

        result: Forecast = defaultdict()

        daily_block = forecast.get("daily", {})
        days = daily_block.get("data", [{}, {}])

        today = days[0]

        currently = forecast.get("currently", {})
        hourly = forecast.get("hourly", {})

        result["current_summary"] = currently.get("summary")

        result["upcoming"] = days[1:]

        for item in result["upcoming"]:
            item["time"] = cherrypy.engine.publish(
                "clock:from_timestamp",
                item.get("time"),
                local=True
            ).pop()

            if "temperatureHigh" in item:
                item["high"] = math.ceil(item.get("temperatureHigh"))

            if "temperatureHighTime" in item:
                item["high_at"] = cherrypy.engine.publish(
                    "clock:from_timestamp",
                    item.get("temperatureHighTime"),
                    local=True
                ).pop()

            if "temperatureLow" in item:
                item["low"] = math.ceil(item.get("temperatureLow"))

            if "temperatureLowTime" in item:
                item["low_at"] = cherrypy.engine.publish(
                    "clock:from_timestamp",
                    item.get("temperatureLowTime"),
                    local=True
                ).pop()

        result["current_temperature"] = math.ceil(
            currently.get("temperature")
        )

        result["current_time"] = cherrypy.engine.publish(
            "clock:from_timestamp",
            currently.get("time"),
            local=True
        ).pop()

        result["current_humidity"] = currently.get("humidity", 0)

        result["summary"] = today.get("summary")

        result["temperature"] = math.ceil(today.get("temperature", 0))

        result["sunrise"] = cherrypy.engine.publish(
            "clock:from_timestamp",
            today.get("sunriseTime"),
            local=True
        ).pop()

        result["sunset"] = cherrypy.engine.publish(
            "clock:from_timestamp",
            today.get("sunsetTime"),
            local=True
        ).pop()

        result["humidity"] = currently.get("humidity", 0)

        result["high"] = math.ceil(today.get("temperatureHigh"))

        result["high_at"] = cherrypy.engine.publish(
            "clock:from_timestamp",
            today.get("temperatureHighTime"),
            local=True
        ).pop()

        result["low"] = math.ceil(today.get("temperatureLow"))

        result["low_at"] = cherrypy.engine.publish(
            "clock:from_timestamp",
            today.get("temperatureLowTime"),
            local=True
        ).pop()

        if "alerts" in forecast:
            result["alerts"] = [
                alert.get("description")
                for alert in forecast["alerts"]
            ]

        now = cherrypy.engine.publish("clock:now", local=True).pop()
        hours_remaining_today = 24 - now.hour

        if "data" in hourly:
            result["hourly"] = []
            for hour in hourly["data"][0:hours_remaining_today]:
                hour_clone = copy.copy(hour)
                hour_clone["time"] = cherrypy.engine.publish(
                    "clock:from_timestamp",
                    hour_clone["time"],
                    local=True
                ).pop()

                result["hourly"].append(hour_clone)

        return result
