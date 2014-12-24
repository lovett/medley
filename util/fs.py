import re
import time

def webgrep(path, include, exclude=[], shun=[]):
    matches = []

    def filter(line, patterns):
        matches = (re.search(pattern, line) for pattern in patterns)
        for match in matches:
            if match:
                return True
        return False

    with open(path) as f:
        for line in f:
            if filter(line, shun):
                ip = line[0:line.find(" ")]
                exclude.append(ip)

            if filter(line, include) and not filter(line, exclude):
                fields = parse_appengine(line)
                matches.append(fields)

    return matches

def parse_appengine(line):
    fields = line.split(" ")
    ip = fields[0]
    return {
        "ip": fields[0],
        "date": time.strptime(" ".join(fields[3:5]), "[%d/%b/%Y:%H:%M:%S %z]"),
        "method": fields[5],
        "uri": fields[6],
        "status": fields[8],
        "referrer": fields[10],
        "line": line
    }
