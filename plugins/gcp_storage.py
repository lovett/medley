"""
Interact with Google Cloud Storage.

See https://googleapis.dev/python/storage/latest/client.html
"""

import json
import pathlib
import cherrypy
from google.cloud import storage
from google.oauth2.service_account import Credentials
import google.api_core.exceptions
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for interacting with Google Cloud Platform."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the gcp prefix.
        """

        self.bus.subscribe("gcp:storage:pull", self.pull_bucket)

    @staticmethod
    @decorators.log_runtime
    def pull_bucket() -> None:
        """
        Download files from a Google Cloud Storage bucket.
        """

        config = cherrypy.engine.publish(
            "registry:search",
            "gcp",
            as_dict=True,
            key_slice=1
        ).pop()

        storage_root = cherrypy.engine.publish(
            "registry:first_value",
            "config:storage_root"
        ).pop()

        if "service_account" not in config:
            raise cherrypy.HTTPError(
                500,
                "Missing gcp:service_account in registry"
            )

        service_account_json = json.loads(config["service_account"])

        scopes = config.get("scope", "").split("\n")

        credentials = Credentials.from_service_account_info(
            service_account_json,
            scopes=scopes
        )

        storage_client = storage.Client(
            credentials=credentials,
            project=config.get("project")
        )

        blobs = storage_client.list_blobs(config.get("bucket"))

        files_pulled = 0

        for blob in blobs:
            blob_path = pathlib.Path(blob.name)

            download_root = pathlib.Path(storage_root)

            destination_path = download_root / blob_path

            should_delete = False

            if destination_path.exists():
                should_delete = True

                if blob.size != destination_path.stat().st_size:
                    should_delete = False

                if should_delete:
                    lines_in_blob = 0
                    with open(destination_path) as handle:
                        for lines_in_blob, _ in enumerate(handle):
                            pass

                    # Add one to account for the last line.
                    lines_in_blob += 1

                    lines_in_database = cherrypy.engine.publish(
                        "logindex:count_lines",
                        blob_path
                    ).pop()

                    if lines_in_database != lines_in_blob:
                        should_delete = False

            if should_delete:
                try:
                    blob.delete()
                except google.api_core.exceptions.GoogleAPIError:
                    bucket_name = config.get("bucket")
                    cherrypy.log(
                        f"Cannot delete GCP blob in {bucket_name}"
                    )
                continue

            if not destination_path.parent.is_dir():
                destination_path.parent.mkdir(parents=True)

            blob.download_to_filename(destination_path)

            if blob_path.parts[0] == "appengine.googleapis.com":
                if blob_path.parts[1] == config.get("log_sink"):
                    cherrypy.engine.publish(
                        "scheduler:add",
                        1,
                        "gcp:appengine:ingest_file",
                        destination_path
                    )

            files_pulled += 1

        cherrypy.engine.publish(
            "applog:add",
            "gcp",
            "bucket_files_pulled",
            files_pulled
        )
