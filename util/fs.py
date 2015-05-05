import os
import os.path
import time
import re
import fnmatch
import os.path
import util.net
import util.parse
import util.db
import util.decorator
import hashlib
from collections import namedtuple

GrepResult = namedtuple("GrepResult", "matches count limit")

def file_hash(path):
    m = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            m.update(data)
    return m.hexdigest()

def getSplitLogRoot(log_root, by, match=None):
    split_name = by
    if match:
        split_name += "_" + match
    return os.path.join(log_root, split_name)


def hashPath(root, key, depth=4, extension=".log"):
    """Convert key to a hash-based file path under root"""
    m = hashlib.sha1()
    m.update(key.encode("utf-8"))
    digest = m.hexdigest()
    path = "".join((digest[i] + os.sep for i in range(depth)))
    return os.path.join(root, path, digest + extension)

def sortLog(path, key):
    index = []

    infile = open(path)
    while True:
        offset = infile.tell()
        line = infile.readline()
        if not line:
            break

        length = len(line)
        fields = util.parse.appengine(line)
        index.append((fields[key], offset, length))

    sorted_index = index.sort()

    if sorted_index != index:
        outpath = path + "_sorted"
        outfile = open(outpath, "w")


        for field, offset, length in index:
            infile.seek(offset)
            outfile.write(infile.read(length))

        outfile.close()
        os.rename(outpath, path)
    infile.close()


def file_list(root, extension=None):
    if not extension:
        extension = ".*"

    return [os.path.join(dirpath, f)
            for dirpath, dirnames, files in os.walk(root)
            for f in fnmatch.filter(files, extension)]

@util.decorator.timed
def appengine_log_grep(logdir, split_dir, filters, limit=50):
    matches = []

    if len(filters["ip"]) > 0:
        root = getSplitLogRoot(split_dir, "ip")
        files = [hashPath(root, f, extension=".sqlite") for f in filters["ip"]]
        files = [f for f in files if os.path.isfile(f)]
    else:
        files = file_list(logdir, "*.log")
        files = [f for f in files if any(d in f for d in filters["date"])]

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


    def processLine(line):
        ip = line[0:line.find(" ")]

        if ip in skips:
            return False

        if filter(line, filters["shun"]):
            skips.add(ip)
            return False

        if not filters["include"] or (filter(line, filters["include"]) and not filter(line, filters["exclude"])):
            if limit == 0 or len(matches) + len(matches_in_file) < limit:
                fields = util.parse.appengine(line)
                matches_in_file.append(fields)
            else:
                additional_matches += 1

    for path in files:
        matches_in_file = []

        print(path)
        if path.endswith(".sqlite"):
            for line in util.db.getLogLines(path):
                processLine(line["value"])
        else:
            with open(path) as f:
                for line in f:
                    processLine(line)

        matches_in_file.reverse()
        matches.extend(matches_in_file)

    return GrepResult(matches, len(matches) + additional_matches, limit)
