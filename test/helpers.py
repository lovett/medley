def getFixture(path):
    with open("test/fixtures/" + path) as handle:
        return handle.read()
