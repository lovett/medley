import re
import fnmatch
import os.path
import util.net
import util.parse

def appengine_log_grep(logdir, filters):
    matches = []

    files = [os.path.join(dirpath, f)
             for dirpath, dirnames, files in os.walk(logdir)
             for f in fnmatch.filter(files, "*.log")]

    if len(filters["date"]) > 0:
        files = [f for f in files if any(d in f for d in filters["date"])]

    def filter(line, patterns):
        matches = (re.search(pattern, line) for pattern in patterns)
        for match in matches:
            if match:
                return True
        return False

    skips = set()

    for path in files:
        with open(path) as f:
            for line in f:
                ip = line[0:line.find(" ")]

                if ip in skips:
                    continue

                if filter(line, filters["shun"]):
                    skips.add(ip)
                    continue

                if filter(line, filters["include"]) and not filter(line, filters["exclude"]):
                    fields = util.parse.appengine(line)
                    matches.append(fields)

    return matches
