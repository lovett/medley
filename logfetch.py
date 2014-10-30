"""Download log files from a remote host for local archiving and
processing.

This script is currently biased toward getting logs out of Google
AppEngine via the appcfg.py tool.

It also is biased toward running under Python 3. For AppEngine, that
creates some complications since appcfg and the rest of the AppEngine
SDK require Python 2. To remedy, we call appcfg through a separate
Python 2 process, using a Python 3 subprocess.

Application configuration is taken from the file logfetch.ini in the
directory that this script resides. Unlike the CherryPy config, this
should be an INI file in the strict sense with no Python expressions
and without quoted values.

"""

import os
import sys
import argparse
import configparser
import subprocess
from datetime import date, datetime

def main():
    """Work out the job configuration, assemble a download command, and
    shell out via subprocess

    """

    # start out in the script directory
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    # configuration and validation
    today = date.today()
    parser = argparse.ArgumentParser()
    parser.add_argument("site")
    parser.add_argument("date", nargs="?",
                        default=today.strftime("%Y-%m-%d"))
    parser.add_argument('--dry-run', action="store_true")
    args = parser.parse_args()

    try:
        config = configparser.ConfigParser()
        config.read("logfetch.ini")
    except configparser.ParsingError:
        sys.exit("Parse error while reading config file")

    try:
        settings = config[args.site]
    except KeyError:
        sys.exit("No settings found in config for " + args.site)

    log_date = datetime.strptime(args.date, "%Y-%m-%d")

    settings["log_dir"] += log_date.strftime("/%Y-%m")
    settings["log_file"] = "%s.log" % log_date.strftime("%Y-%m-%d")

    # filesystem preparation
    try:
        os.makedirs(settings["log_dir"], exist_ok=True)
    except os.error:
        if not os.path.isdir(settings["log_dir"]):
            sys.exit("Unable to create {}".format(settings["log_dir"]))

    os.chdir(settings["log_dir"])

    # assemble the download command
    if settings["source"] == "appengine":
        command = [
            settings["python"],
            settings["appcfg"],
            "request_logs",
            "--application=%s" % args.site,
            "--version=%s" % settings["version"],
            "--num_days=1",
            "--include_all",
            "--end_date=%s" % log_date.strftime("%Y-%m-%d"),
            settings["log_file"]
        ]

        if os.path.isfile(settings["log_file"]):
            command.insert(-1, "--append")


    # perform the download
    if args.dry_run:
        print("Files saved to: %s" % settings["log_file"])
        print("Stdout and stderr log to: %s" % config["general"].get("log"))
        print("%s" % " ".join(command))
        sys.exit()

    log = open(config["general"].get("log"), "a")
    subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
    log.close()

if __name__ == "__main__":
    main()
