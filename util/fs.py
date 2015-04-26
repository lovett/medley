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

def hashPath(root, key, depth=4, extension=".log"):
    """Convert key to a hash-based file path under root"""
    m = hashlib.sha1()
    m.update(key.encode("utf-8"))
    digest = m.hexdigest()
    path = "".join((digest[i] + os.sep for i in range(depth)))
    print(root)
    print(key)
    print(os.path.join(root, path, digest + extension))
    return os.path.join(root, path, digest + extension)

def segregateLogLine(root, line, field):
    """Append line to a file under root based on the hashed value of field"""
    fields = util.parse.appengine(line)
    key = fields[field]
    output_path = util.fs.hashPath(root, key)

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
