import subprocess
import re
def query(address):
    """Run a whois query by shelling out. The output is filtered to
    improve readability. Returns a list of key value pairs.

    Although there are some whois Python modules, none proved viable
    for Python 3.2"""

    assert len(address) > 0, "Invalid address"

    process = subprocess.Popen(["whois", address],
                               stdout=subprocess.PIPE)
    out, err = process.communicate()

    try:
        out_raw = out.decode("utf-8")
    except UnicodeDecodeError:
        out_raw = out.decode("iso-8859-1")

    out_raw = out_raw.split("\n")

    out_filtered = []
    for line in out_raw:
        line = line.strip()

        # remove comments
        if line.startswith(("#", "%")):
            continue

        # separate label and value for non-comment lines
        line = re.sub(r"\s+", " ", line).strip()
        fields = line.split(": ", 1)

        # Discard blank lines
        if fields[0] == "":
            continue

        # Discard labelled lines with no value
        if len(fields) == 1 and ":" in fields[0]:
            continue

        # Preserve unlabelled lines
        if len(fields) == 1:
            fields.append(None)
        else:
            fields[0] = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", fields[0]).title()

        out_filtered.append(fields)

    # collapse repeated headers and comment lines
    previous = None
    out_collapsed = []
    for line in out_filtered:
        if line[1] is not None and line[0] == previous:
            out_collapsed[-1][-1] += "\n" + line[1]
        else:
            out_collapsed.append(line)
            previous = line[0]

    return out_collapsed
