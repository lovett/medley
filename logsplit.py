import os.path
import sys
import util.parse
import util.fs

def segregate(parent_dir, field, segregated_line):
    path = util.fs.hashPath(parent_dir, field)

    parent = os.path.dirname(path)

    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                if line == segregated_line:
                    return False

    if not os.path.isdir(parent):
        os.makedirs(parent)

    with open(path, "a") as f:
        f.write(segregated_line)

def main():
    try:
        logfile = sys.argv[1]
    except IndexError:
        sys.exit("No input file specified")

    if not os.path.isfile(logfile):
        sys.exit("{} is not a file".format(logfile))


    log_parent = os.path.dirname(logfile)
    log_root = os.path.dirname(log_parent)
    split_root = log_root + "_split"



    with open(logfile) as f:
        for line in f:
            fields = util.parse.appengine(line)
            segregate(split_root, fields.ip, line)

if __name__ == "__main__":
    main()
