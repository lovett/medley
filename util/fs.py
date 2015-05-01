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

def file_hash(path):
    m = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            m.update(data)
    return m.hexdigest()


def getSplitLogRoot(log_root, split_by):
    return log_root + "_split_by_{}".format(split_by)


def hashPath(root, key, depth=4, extension=".log"):
    """Convert key to a hash-based file path under root"""
    m = hashlib.sha1()
    m.update(key.encode("utf-8"))
    digest = m.hexdigest()
    path = "".join((digest[i] + os.sep for i in range(depth)))
    return os.path.join(root, path, digest + extension)


def segregateLogLine(root, line, field, match=None):
    """Append line to a file under root

    The file path is determined from the hashed value of field.

    Lines can be appended selectively by specifying match. Matching is
    string-based and case-insensitive.
    """

    fields = util.parse.appengine(line)

    # the field isn't present
    if not field in fields:
        return None

    # the field doesn't match
    if match and (match.lower() not in fields[field].lower()):
        return None

    output_path = util.fs.hashPath(root, fields[field])

    # don't allow dupliate writes
    if os.path.isfile(output_path):
        with open(output_path) as f:
            for existing_line in f:
                if existing_line == line:
                    return None


    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "a") as f:
        f.write(line)

    return output_path


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
def appengine_log_grep(logdir, filters, limit=50):
    matches = []

    t0 = time.time()
    if len(filters["ip"]) > 0:
        root = getSplitLogRoot(logdir, "ip")
        files = [hashPath(root, f) for f in filters["ip"]]
        files = [f for f in files if os.path.isfile(f)]
    else:
        files = file_list(logdir, "*.log")
        files = [f for f in files if any(d in f for d in filters["date"])]
    t1 = time.time()

    print(files)

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

                if not filters["include"] or (filter(line, filters["include"]) and not filter(line, filters["exclude"])):
                    if limit == 0 or len(matches) + len(matches_in_file) < limit:
                        fields = util.parse.appengine(line)
                        matches_in_file.append(fields)
                    else:
                        additional_matches += 1

        matches_in_file.reverse()
        matches.extend(matches_in_file)

    t3 = time.time()

    return GrepResult(matches, len(matches) + additional_matches, limit, t1 - t0, t3 - t2)
