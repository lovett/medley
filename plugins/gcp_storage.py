"""Interact with Google Cloud Storage."""

from datetime import datetime
import json
import pathlib
import typing
import cherrypy
import jwt
from plugins import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for interacting with Google Cloud Platform."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the gcp prefix.

        """

        self.bus.subscribe("gcp:storage:pull", self.pull_bucket)

    @decorators.log_runtime
    def pull_bucket(self) -> None:
        """Download files from a Google Cloud Storage bucket."""

        config = cherrypy.engine.publish(
            "registry:search:dict",
            "gcp",
            key_slice=1
        ).pop()

        storage_root = cherrypy.engine.publish(
            "registry:first:value",
            "config:storage_root"
        ).pop()

        if "service_account" not in config:
            raise cherrypy.HTTPError(
                500,
                "Missing gcp:service_account in registry"
            )

        service_account = json.loads(config["service_account"])

        now = typing.cast(
            datetime,
            cherrypy.engine.publish(
                "clock:now"
            ).pop()
        )

        expire = typing.cast(
            datetime,
            cherrypy.engine.publish(
                "clock:shift",
                now,
                hours=1
            ).pop()
        )

        token = jwt.encode({
            "iss": service_account.get("client_email"),
            "scope": config.get("scope"),
            "aud": service_account.get("token_uri"),
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        }, service_account.get("private_key"), algorithm="RS256")

        grant_response = cherrypy.engine.publish(
            "urlfetch:post",
            service_account.get("token_uri"),
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": token
            },
            as_object=True
        ).pop()

        if not grant_response:
            return

        access_token = grant_response.json().get("access_token")

        bucket = cherrypy.engine.publish(
            "urlfetch:get",
            (
                "https://storage.googleapis.com/storage/v1/b/"
                f"{config.get('bucket')}/o"
            ),
            headers=self.standard_headers(access_token),
            as_json=True
        ).pop()

        if not bucket:
            return

        files_pulled = 0

        for item in bucket.get("items"):
            item_path = pathlib.Path(item.get("name"))
            destination_path = pathlib.Path(storage_root) / item_path
            should_delete = False

            if destination_path.exists():
                should_delete = True

                if int(item.get("size", 0)) != destination_path.stat().st_size:
                    should_delete = False

            if should_delete and "request_log" in destination_path.parts:
                lines_in_blob = 0
                with open(destination_path) as handle:
                    for lines_in_blob, _ in enumerate(handle):
                        pass

                # Add one to account for the last line.
                lines_in_blob += 1

                lines_in_database = cherrypy.engine.publish(
                    "logindex:count_lines",
                    item_path
                ).pop()

                if lines_in_database != lines_in_blob:
                    should_delete = False

            if should_delete:
                self.delete_item(
                    item.get("selfLink"),
                    access_token
                )
                continue

            if not destination_path.parent.is_dir():
                destination_path.parent.mkdir(parents=True)

            cherrypy.engine.publish(
                "urlfetch:get:file",
                item.get("mediaLink"),
                destination_path,
                headers=self.standard_headers(access_token)
            )

            request_top_path = ("appengine.googleapis.com", "request_log")

            if item_path.parts[0:2] == request_top_path:
                cherrypy.engine.publish(
                    "scheduler:add",
                    1,
                    "gcp:appengine:ingest_file",
                    item_path
                )

            files_pulled += 1

        cherrypy.engine.publish(
            "applog:add",
            "gcp_storage",
            f"{files_pulled} {'file' if files_pulled == 1 else 'files'} pulled"
        )

    def delete_item(self, url: str, access_token: str) -> None:
        """Delete a file from a bucket."""

        cherrypy.engine.publish(
            "urlfetch:delete",
            url,
            headers=self.standard_headers(access_token)
        ).pop()

    @staticmethod
    def standard_headers(access_token: str) -> typing.Dict[str, str]:
        """Wrap an access token in a headers dict."""

        return {
            "Authorization": f"Bearer {access_token}"
        }
