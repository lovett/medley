import os
import os.path
import time
import re
import fnmatch
import os.path
import util.net
import util.parse
import util.decorator
import hashlib
import apps.logindex.models
from collections import namedtuple

GrepResult = namedtuple("GrepResult", "matches count limit")

@util.decorator.timed
def appengine_log_grep(logdir, filters, offsets=None, limit=50):
    logman = apps.logindex.models.LogManager(logdir)
    matches = []

    files = logman.getList(True)
    files = [f for f in files if any(d in f for d in filters["date"])]
    additional_matches = 0

    def filter(line, patterns):
        matches = (re.search(pattern, line) for pattern in patterns)
        for match in matches:
            if match:
                return True
        return False

    skips = set()

    # put the file list in reverse chronological order
    # (lexicographically) to get newest results first
    files.sort(reverse=True)

    def processLine(line):
        ip = line[0:line.find(" ")]

        if ip in skips:
            return 0

        if filter(line, filters["shun"]):
            skips.add(ip)
            return 0

        if not filters["include"] and not filters["exclude"]:
            include = True
        elif not filters["include"] and not filter(line, filters["exclude"]):
            include = True
        elif not filters["exclude"] and filter(line, filters["include"]):
            include = True
        else:
            include = False

        if not include:
            return 0

        if include and len(matches) + len(matches_in_file) > limit:
            return 1

        fields = util.parse.appengine(line)
        matches_in_file.append(fields)
        return 0

    def offsetsByPath(path):
        if not offsets:
            return None

        for key, value in offsets.items():
            if key in path:
                return value

    for path in files:
        matches_in_file = []

        with open(path) as f:
            path_offsets = offsetsByPath(path)
            if not path_offsets:
                for line in f:
                    additional_matches += processLine(line)
            else:
                for offset in path_offsets:
                    f.seek(offset)
                    line = f.readline()
                    additional_matches += processLine(line)

        matches_in_file.reverse()
        matches.extend(matches_in_file)

    return GrepResult(matches, len(matches) + additional_matches, limit)
