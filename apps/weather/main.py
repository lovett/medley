"""Current and upcoming forecasts"""

import typing
from collections import defaultdict
import cherrypy

Forecast = typing.Dict[str, typing.Any]
Config = typing.Dict[str, typing.Any]


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args: str, **_kwargs: str) -> bytes:
        """Display current and upcoming weather conditions."""

        latitude = ""
        longitude = ""

        if len(args) == 1:
            latitude, longitude = args[0].split(",", 1)

        config = self.get_config(latitude, longitude)

        forecast = self.request_forecast(config)

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
                other_locations=config["locations"],
                location_name=config["location_name"],
                edit_url=edit_url,
                subview_title=config["location_name"],
            ).pop()
        )

    def POST(self, *args: str, **kwargs: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        latitude = ""
        longitude = ""
        components = tuple(kwargs.get("components", ''))

        if args[0] == "speak":
            try:
                latitude, longitude = args[1].split(",", 1)
            except IndexError:
                pass
            return self.speak(components, latitude, longitude)

        raise cherrypy.HTTPError(404)

    def request_forecast(self, config: Config) -> Forecast:
        """Request current weather data from OpenWeatherMap."""

        latitude = config.get("latitude")
        longitude = config.get("longitude")
        api_key = config.get("openweather_api_key")

        api_response = cherrypy.engine.publish(
            "urlfetch:get",
            "https://api.openweathermap.org/data/2.5/onecall",
            params={
                "lat": latitude,
                "lon": longitude,
                "exclude": "minutely",
                "units": "imperial",
                "appid": api_key,
            },
            as_json=True,
            cache_lifespan=600
        ).pop()

        return self.shape_forecast(api_response)

    @staticmethod
    def get_config(latitude: str, longitude: str) -> Config:
        """Load the application configuration."""

        config: Config = cherrypy.engine.publish(
            "registry:search:dict",
            "weather:*",
            key_slice=1
        ).pop()

        if "openweather_api_key" not in config:
            raise cherrypy.HTTPError(500, "No api key")

        config["locations"] = tuple(
            tuple(value.split(",", 2))
            for key, value in config.items()
            if key.startswith("latlong")
        )

        location_name = ""
        if not latitude and not longitude:
            latitude, longitude, location_name = config.get(
                "latlong:default", ""
            ).split(",", 2)

        if not location_name:
            location_name = next((
                location[2]
                for location in config["locations"]
                if location[0] == latitude
                and location[1] == longitude
            ), "")

        config["latitude"] = latitude
        config["longitude"] = longitude
        config["location_name"] = location_name

        return config

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

        end_hour_index = 24 - now.hour
        result["currently"] = currently
        result["hourly"] = hourly[0:end_hour_index]

        hourly_tomorrow = hourly[end_hour_index:end_hour_index+24]
        result["hourly_tomorrow"] = hourly_tomorrow[6:13]
        result["today"] = daily[0]
        result["upcoming"] = daily[1:]

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

        result["alerts"] = []

        if forecast.get("alerts"):
            blacklist = cherrypy.engine.publish(
                "registry:search:valuelist",
                "weather:alerts:blacklist"
            ).pop()

            for alert in forecast.get("alerts", []):
                if alert["event"] in blacklist:
                    continue

                for key in ["start", "end"]:
                    alert[key] = cherrypy.engine.publish(
                        "clock:from_timestamp",
                        alert[key],
                        True
                    ).pop()

                alert["description"] = alert["description"].lstrip("...")
                alert["description"] = alert["description"].split("*")

                result["alerts"].append(alert)

        return result

    def speak(
            self,
            components: typing.Tuple[str, ...],
            latitude: str,
            longitude: str
    ) -> None:
        """Present the current forecast in a format suitable for
        text-to-speech."""

        config = self.get_config(latitude, longitude)

        forecast = self.request_forecast(config)

        statements = []

        for component in components:
            statement = ""

            if component == "summary":
                statement = forecast["currently"]["weather_description"]

            if component == "clouds":
                clouds = forecast["currently"]["clouds"]

                statement = f"{clouds} percent cloudy."

            if component == "precipitation":
                if "rain" in forecast["currently"]["weather_groups"]:
                    statement = "It's raining."
                if "snow" in forecast["currently"]["weather_groups"]:
                    statement = "It's snowing."

            if component == "temperature":
                temp = round(forecast["currently"]["temp"])
                feel = round(forecast["currently"]["feels_like"])

                statement = "It's {} degrees".format(temp)

                if abs(temp - feel) > 5:
                    statement += " but feels like {}".format(feel)

            if component == "humidity":
                statement = "{} percent humidity".format(
                    forecast["currently"]["humidity"]
                )

            if statement:
                statements.append(statement)

        for statement in statements:
            cherrypy.engine.publish(
                "speak",
                statement
            )

        cherrypy.response.status = 204
