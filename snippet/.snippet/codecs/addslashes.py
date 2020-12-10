from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Add slashes before quotes. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value):
        return value.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
