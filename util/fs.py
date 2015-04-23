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
from collections import namedtuple

GrepResult = namedtuple("GrepResult", "matches count limit walktime parsetime")


def hashPath(root, path):
    m = hashlib.md5()

    m.update(path.encode("utf-8"))

    hex = m.hexdigest()

    return root + "/" + hex[0] + "/" + hex[1] + "/" + hex[2] + "/" + hex + ".log"

@util.decorator.timed
def appengine_log_grep(logdir, filters, limit=50):
    matches = []

    t0 = time.time()
    files = [os.path.join(dirpath, f)
             for dirpath, dirnames, files in os.walk(logdir)
             for f in fnmatch.filter(files, "*.log")]
    t1 = time.time()

    if len(filters["date"]) > 0:
        files = [f for f in files if any(d in f for d in filters["date"])]
    elif len(filters["ip"]) > 0:
        files = [hashPath(logdir + "_split", f) for f in filters["ip"]]
        files = [f for f in files if os.path.isfile(f)]

    def filter(line, patterns):
        matches = (re.search(pattern, line) for pattern in patterns)
        for match in matches:
            if match:
                return True
        return False

    skips = set()
    additional_matches = 0

    # put the file list in reverse chronological order
    # (lexicographically) to get newest results first
    files.sort(reverse=True)

    t2 = time.time()
    for path in files:
        matches_in_file = []

        with open(path) as f:
            for line in f:
                ip = line[0:line.find(" ")]

                if ip in skips:
                    continue

                if filter(line, filters["shun"]):
                    skips.add(ip)
                    continue

                if filter(line, filters["include"]) and not filter(line, filters["exclude"]):
                    if limit == 0 or len(matches) + len(matches_in_file) < limit:
                        fields = util.parse.appengine(line)
                        matches_in_file.append(fields)
                    else:
                        additional_matches += 1

        matches_in_file.reverse()
        matches.extend(matches_in_file)

    t3 = time.time()

    return GrepResult(matches, len(matches) + additional_matches, limit, t1 - t0, t3 - t2)
